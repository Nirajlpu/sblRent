from django.contrib import admin
# ----------------add manually------------------
from home.models import  Profile#add manually
from home.models import Property #add manually
from home.models import Booking #add manually

# Register your models here.
admin.site.register(Profile) #add manually
admin.site.register(Property) #add manually
admin.site.register(Booking) #add manually
