from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.conf import settings
import hashlib
import os


def hash_filename(filename):
    """Generate a SHA256 hash for the filename (preserve extension)."""
    name, ext = os.path.splitext(filename)
    hash_str = hashlib.sha256(filename.encode('utf-8')).hexdigest()
    return f"{hash_str}{ext}"

def user_profile_pic_path(instance, filename):
    """Path: user_<user_id>/profile_pics/<filename>"""
    return f'user_{instance.user.id}/profile_pics/{hash_filename(filename)}'

def vendor_document_path(instance, filename):
    """Path: user_<user_id>/documents/<filename>"""
    return f'user_{instance.user.id}/documents/{hash_filename(filename)}'

def property_image_path(instance, filename):
    """Path: user_<owner_id>/property_<property_id>/images/<filename>"""
    return f'user_{instance.property.owner.id}/property/property_{instance.property.id}/images/{hash_filename(filename)}'

def property_video_path(instance, filename):
    """Path: user_<owner_id>/property_<property_id>/videos/<filename>"""
    return f'user_{instance.owner.id}/property/property_{instance.id}/videos/{hash_filename(filename)}'

class CustomUser(AbstractUser):
    is_email_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    def __str__(self):
        return self.username

class Profile(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('vendor', 'Vendor'),
    )
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    registration_date = models.DateField(auto_now_add=True)
    profile_picture = models.ImageField(
        upload_to=user_profile_pic_path,
        null=True,
        blank=True,
        default='default_profile_pic.jpg'
    )
    is_email_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    # Vendor-specific
    company_name = models.CharField(max_length=100, blank=True, null=True)
    aadhaar_number = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    aadhaar_document = models.FileField(upload_to=vendor_document_path, blank=True, null=True)
    pan_document = models.FileField(upload_to=vendor_document_path, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    # New payout-related fields
    bank_account_number = models.CharField(max_length=30, blank=True, null=True)
    bank_ifsc = models.CharField(max_length=15, blank=True, null=True)
    razorpay_contact_id = models.CharField(max_length=50, blank=True, null=True)
    razorpay_fund_account_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    # Remove the old delete method, signals will handle file deletion

class Property(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('rented', 'Rented'),
        ('sold', 'Sold'),
        ('draft', 'Draft')
    )
    TYPE_CHOICES = (
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('villa', 'Villa'),
        ('condo', 'Condo'),
        ('land', 'Land'),
        ('commercial', 'Commercial')
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    property_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='apartment')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    location = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    # image_url = models.URLField(default='https://via.placeholder.com/400x300?text=Property+Image', blank=True, null=True)
    image = models.ImageField(
        upload_to='property_images/',
        default='property_images/default.jpg',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        blank=True,
        null=True
    )
    video = models.FileField(upload_to=property_video_path, validators=[FileExtensionValidator(['mp4', 'mov', 'avi'])],
                              blank=True, null=True)
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    area = models.DecimalField(max_digits=8, decimal_places=2, help_text="Area in square feet")
    year_built = models.PositiveIntegerField(null=True, blank=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='properties')
    views = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5,
                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
    date_added = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=True)
    amenities = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.title
    
    def delete(self, *args, **kwargs):
        # Delete associated images when property is deleted
        for image in self.images.all():
            image.delete()
        super().delete(*args, **kwargs)

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=property_image_path)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.property.title}"
    
    # Remove the old delete method, signals will handle file deletion

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('paid', 'Paid')
    )
    PAYMENT_TYPE_CHOICES = (
        ('monthly', 'Monthly'),
    )
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    start_date = models.DateField()
    end_date = models.DateField()
    guest = models.CharField(max_length=15, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='approved')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    payment_data = models.JSONField(default=list, blank=True)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default='monthly')
    monthly_due_dates = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Booking #{self.id} - {self.property.title}"

class PaymentLog(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=50)
    payment_id = models.CharField(max_length=50, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.CharField(max_length=20)
    year = models.CharField(max_length=10)
    status = models.CharField(max_length=20, default='created')  # created / paid / failed
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_By_User = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    signature = models.CharField(max_length=255, blank=True, null=True, help_text="Razorpay payment signature for verification.")
    payment_method = models.CharField(max_length=50, blank=True, null=True, help_text="Payment method/type (e.g., card, upi, netbanking)")
    error_message = models.TextField(blank=True, null=True, help_text="Error or failure reason, if any.")
    full_response = models.JSONField(blank=True, null=True, help_text="Full Razorpay response for audit/debugging.")

    def __str__(self):
        return f"PaymentLog #{self.id}-paid_By_User:{self.paid_By_User}->{self.status}"

class Review(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('property', 'user')

    def __str__(self):
        return f"Review by {self.user.username} for {self.property.title}"

class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'property')

    def __str__(self):
        return f"{self.user.username} - {self.property.title}"


from django.db import models
from django.conf import settings

class RecentView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recent_views')
    property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='recent_views')
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'property')
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user.username} viewed {self.property.title} at {self.viewed_at}"
# --- SIGNALS FOR FILE DELETION ON UPDATE OR DELETE ---
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver

@receiver(pre_save, sender=Profile)
def delete_old_profile_files_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Profile.objects.get(pk=instance.pk)
    except Profile.DoesNotExist:
        return
    if old.profile_picture and old.profile_picture != instance.profile_picture:
        old.profile_picture.delete(save=False)
    if old.aadhaar_document and old.aadhaar_document != instance.aadhaar_document:
        old.aadhaar_document.delete(save=False)
    if old.pan_document and old.pan_document != instance.pan_document:
        old.pan_document.delete(save=False)

@receiver(post_delete, sender=Profile)
def delete_profile_files_on_delete(sender, instance, **kwargs):
    if instance.profile_picture:
        instance.profile_picture.delete(save=False)
    if instance.aadhaar_document:
        instance.aadhaar_document.delete(save=False)
    if instance.pan_document:
        instance.pan_document.delete(save=False)

@receiver(pre_save, sender=Property)
def delete_old_property_files_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Property.objects.get(pk=instance.pk)
    except Property.DoesNotExist:
        return
    if old.image and old.image != instance.image:
        old.image.delete(save=False)
    if old.video and old.video != instance.video:
        old.video.delete(save=False)

@receiver(post_delete, sender=Property)
def delete_property_files_on_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
    if instance.video:
        instance.video.delete(save=False)

@receiver(pre_save, sender=PropertyImage)
def delete_old_propertyimage_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = PropertyImage.objects.get(pk=instance.pk)
    except PropertyImage.DoesNotExist:
        return
    if old.image and old.image != instance.image:
        old.image.delete(save=False)

@receiver(post_delete, sender=PropertyImage)
def delete_propertyimage_on_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)