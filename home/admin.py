from django.contrib import admin
from .models import (
    CustomUser,
    Profile,
    Property,
    PropertyImage,
    Booking,
    Review,
    Wishlist
)

# Register models
admin.site.register(CustomUser)
admin.site.register(Profile)
admin.site.register(Property)
admin.site.register(PropertyImage)
admin.site.register(Booking)
admin.site.register(Review)
admin.site.register(Wishlist)