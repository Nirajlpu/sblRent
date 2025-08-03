from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import os
from django.core.validators import FileExtensionValidator

def user_profile_pic_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/profile_pics/<filename>
    return f'user_{instance.user.id}/profile_pics/{filename}'

def vendor_document_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/documents/<filename>
    return f'user_{instance.user.id}/documents/{filename}'

def property_image_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/property_<id>/images/<filename>
    return f'property_{instance.id}/images/{filename}'

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
    
    # Vendor-specific fields
    company_name = models.CharField(max_length=100, blank=True, null=True)
    aadhaar_number = models.CharField(max_length=12, blank=True, null=True)
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    aadhaar_document = models.FileField(upload_to=vendor_document_path, blank=True, null=True)
    pan_document = models.FileField(upload_to=vendor_document_path, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    def delete(self, *args, **kwargs):
        # Delete associated files when profile is deleted
        if self.profile_picture:
            if os.path.isfile(self.profile_picture.path):
                os.remove(self.profile_picture.path)
        if self.aadhaar_document:
            if os.path.isfile(self.aadhaar_document.path):
                os.remove(self.aadhaar_document.path)
        if self.pan_document:
            if os.path.isfile(self.pan_document.path):
                os.remove(self.pan_document.path)
        super().delete(*args, **kwargs)

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
    deposit = models.DecimalField(max_digits=12, decimal_places=2,default=0)
    location = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude of the property"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude of the property"
    )
    image_url = models.URLField(default='https://via.placeholder.com/400x300?text=Property+Image')
    image = models.ImageField(
        upload_to='property_images/',
        default='property_images/default.jpg',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    video = models.FileField(
        upload_to='property_videos/',
        validators=[FileExtensionValidator(['mp4', 'mov', 'avi'])],
        blank=True,
        null=True
    )
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    area = models.DecimalField(max_digits=8, decimal_places=2, help_text="Area in square feet")
    year_built = models.PositiveIntegerField(null=True, blank=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='properties')
    views = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=4.5,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    date_added = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=True)
    
    # Amenities stored as a list of strings
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
    
    def delete(self, *args, **kwargs):
        # Delete the file from filesystem when the model is deleted
        if os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    )
    
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    

    def __str__(self):
        return f"Booking #{self.id} - {self.property.title}"

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
    

from django.db import models
from django.conf import settings
from .models import Property  # if not already present

class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'property')

    def __str__(self):
        return f"{self.user.username} - {self.property.title}"