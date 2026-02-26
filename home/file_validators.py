from pathlib import Path
import io

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile


MAX_KYC_DOC_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_DANGEROUS_NAMES = {
    "/JavaScript",
    "/JS",
    "/AA",
    "/OpenAction",
    "/Launch",
    "/RichMedia",
    "/EmbeddedFile",
    "/EmbeddedFiles",
    "/XFA",
    "/SubmitForm",
    "/ImportData",
}
IMAGE_SIGNATURES = {
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
}


def _validate_file_signature(uploaded_file, file_extension, field_label):
    uploaded_file.seek(0)
    header = uploaded_file.read(16)
    uploaded_file.seek(0)

    if file_extension == ".pdf" and not header.startswith(b"%PDF-"):
        raise ValidationError(f"{field_label} must be a valid PDF file.")

    if file_extension in IMAGE_SIGNATURES:
        expected_signatures = IMAGE_SIGNATURES[file_extension]
        if not any(header.startswith(sig) for sig in expected_signatures):
            raise ValidationError(f"{field_label} content does not match its file type.")


def _validate_image(uploaded_file, field_label):
    from PIL import Image, UnidentifiedImageError

    uploaded_file.seek(0)
    try:
        image = Image.open(uploaded_file)
        image.verify()
    except (UnidentifiedImageError, OSError):
        raise ValidationError(f"{field_label} is not a valid image file.")
    finally:
        uploaded_file.seek(0)


def _scan_pdf_object(obj, visited):
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

    object_id = id(obj)
    if object_id in visited:
        return False
    visited.add(object_id)

    if isinstance(obj, IndirectObject):
        try:
            return _scan_pdf_object(obj.get_object(), visited)
        except Exception:
            return True

    if isinstance(obj, DictionaryObject):
        for key, value in obj.items():
            key_name = str(key)
            if key_name in PDF_DANGEROUS_NAMES:
                return True
            if _scan_pdf_object(value, visited):
                return True
        return False

    if isinstance(obj, ArrayObject):
        for item in obj:
            if _scan_pdf_object(item, visited):
                return True
        return False

    value_text = str(obj)
    return any(marker in value_text for marker in PDF_DANGEROUS_NAMES)


def _validate_pdf(uploaded_file, field_label):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValidationError("PDF validation service is unavailable. Please contact support.")

    _validate_file_signature(uploaded_file, ".pdf", field_label)

    uploaded_file.seek(0)
    try:
        reader = PdfReader(uploaded_file, strict=False)
    except Exception:
        uploaded_file.seek(0)
        raise ValidationError(f"{field_label} is corrupted or unreadable.")

    if getattr(reader, "is_encrypted", False):
        uploaded_file.seek(0)
        raise ValidationError(f"Encrypted PDFs are not allowed for {field_label}.")

    try:
        root = reader.trailer.get("/Root")
        if root and _scan_pdf_object(root, set()):
            raise ValidationError(
                f"{field_label} contains active content (JavaScript/actions) and was blocked."
            )

        # Also inspect page-level dictionaries for additional actions.
        for page in reader.pages:
            if _scan_pdf_object(page, set()):
                raise ValidationError(
                    f"{field_label} contains active content (JavaScript/actions) and was blocked."
                )
    finally:
        uploaded_file.seek(0)


def validate_uploaded_kyc_document(uploaded_file, field_label="Document"):
    if not uploaded_file:
        return

    file_extension = Path(uploaded_file.name or "").suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"{field_label} must be one of: PDF, JPG, JPEG, PNG."
        )

    if uploaded_file.size > MAX_KYC_DOC_SIZE_BYTES:
        raise ValidationError(f"{field_label} must be 5MB or smaller.")

    _validate_file_signature(uploaded_file, file_extension, field_label)

    if file_extension == ".pdf":
        _validate_pdf(uploaded_file, field_label)
        return

    if file_extension in IMAGE_EXTENSIONS:
        _validate_image(uploaded_file, field_label)


def sanitize_uploaded_pdf(uploaded_file, field_label="Document"):
    if not uploaded_file:
        return uploaded_file

    file_extension = Path(uploaded_file.name or "").suffix.lower()
    if file_extension != ".pdf":
        return uploaded_file

    try:
        import pikepdf
    except ImportError:
        return uploaded_file

    uploaded_file.seek(0)
    source_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    if not source_bytes:
        raise ValidationError(f"{field_label} is empty.")

    source_stream = io.BytesIO(source_bytes)
    sanitized_stream = io.BytesIO()

    try:
        with pikepdf.open(source_stream) as pdf:
            pdf.Root.pop("/OpenAction", None)
            pdf.Root.pop("/JavaScript", None)
            pdf.Root.pop("/AcroForm", None)

            for page in pdf.pages:
                page.obj.pop("/AA", None)
                annotations = page.obj.get("/Annots", [])
                for annotation in annotations:
                    annotation_obj = annotation.get_object()
                    if annotation_obj:
                        annotation_obj.pop("/AA", None)
                        action = annotation_obj.get("/A")
                        if action and str(action.get("/S", "")) in {"/JavaScript", "/Launch", "/SubmitForm", "/ImportData"}:
                            annotation_obj.pop("/A", None)

            pdf.save(sanitized_stream)
    except Exception:
        raise ValidationError(f"{field_label} could not be sanitized.")

    sanitized_content = ContentFile(sanitized_stream.getvalue())
    sanitized_content.name = uploaded_file.name
    return sanitized_content