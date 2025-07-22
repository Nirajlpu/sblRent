from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse 
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from .models import Property, Profile, CustomUser, Booking, Review, PropertyImage
from .forms import PropertyForm, ProfileForm
import os
from .models import Wishlist

def home(request):
    
    featured_properties = Property.objects.filter(
        status='active', 
        is_featured=True
    )[:6]
    recent_properties = Property.objects.filter(
        status='active'
    ).order_by('-date_added')[:6]
    
    return render(request, 'index.html', {
        'featured_properties': featured_properties,
        
        'recent_properties': recent_properties
    })

def register_user(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone = request.POST.get('phone')
        role = request.POST.get('role', 'user')
        profile_pic = request.FILES.get('profile_image')
        
        # Validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('register')
            
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken!")
            return redirect('register')
            
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered!")
            return redirect('register')

        # Create user
        user = CustomUser.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username,
            password=password
        )
        
        # Create profile
        profile = Profile.objects.create(
            user=user,
            role=role,
            phone_number=phone
        )
        
        # Handle profile picture upload
        if profile_pic:
            profile.profile_picture = profile_pic
            profile.save()
            
        # Handle vendor documents if role is vendor
        if role == 'vendor':
            aadhaar_doc = request.FILES.get('aadhaar_card')
            if aadhaar_doc:
                profile.aadhaar_document = aadhaar_doc
                profile.aadhaar_number = request.POST.get('aadhaar_number', '')
                profile.save()

        messages.success(request, "Account created successfully! Please login.")
        return redirect('login')

    return render(request, 'register.html')

def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('login')
            
    return render(request, 'login.html')

@login_required
def dashboard(request):
    user = request.user
    profile = user.profile
   
    
   

    
    if profile.role == 'vendor':
        properties = Property.objects.filter(owner=user)
        
        stats = {
            'total_properties': properties.count(),
            'active_properties': properties.filter(status='active').count(),
            'pending_properties': properties.filter(status='pending').count(),
            'rented_properties': properties.filter(status='rented').count(),
            'total_bookings': Booking.objects.filter(property__owner=user).count(),
            'pending_bookings': Booking.objects.filter(
                property__owner=user, 
                status='pending'
            ).count()
        }
        
        return render(request, 'vendor_dashboard.html', {

            'properties': properties[:5],  # Show recent 5 properties
            'stats': stats,
            'pic': profile,
            'recent_bookings': Booking.objects.filter(
                property__owner=user
            ).order_by('-created_at')[:5]
        })
    else:
        # User dashboard
        
        properties = Property.objects.filter(status='active')
        bookings = Booking.objects.filter(user=user).select_related('property')
        
        return render(request, 'user_dashboard.html', {
            'properties': properties[:6],
            'pic': profile,
            'bookings': bookings,
            'wishlist': properties.filter(wishlist__user=user)[:4]
        })

@login_required
def property_detail(request, property_id):
    property = get_object_or_404(Property, id=property_id)
    is_bookmarked = False
    similar_properties = Property.objects.filter(
        Q(location__icontains=property.location) | 
        Q(property_type=property.property_type),
        status='active'
    ).exclude(id=property.id)[:4]
    
    if request.user.is_authenticated:
        property.views += 1
        property.save()
        is_bookmarked = property.wishlist.filter(user=request.user).exists()
    
    return render(request, 'property_detail.html', {
        'property': property,
        'similar_properties': similar_properties,
        'is_bookmarked': is_bookmarked,
        'reviews': Review.objects.filter(property=property).select_related('user')
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Property, PropertyImage
import json

@login_required
def manage_property(request, property_id=None):
    user = request.user
    profile = user.profile

    property_obj = None
    if property_id:
        property_obj = get_object_or_404(Property, id=property_id, owner=user)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        property_type = request.POST.get('property_type')
        status = request.POST.get('status')
        location = request.POST.get('location')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')
        price = request.POST.get('price') or 0
        deposit = request.POST.get('deposit') or 0
        bedrooms = request.POST.get('bedrooms') or 0
        bathrooms = request.POST.get('bathrooms') or 0
        square_feet = request.POST.get('square_feet') or 0
        year_built = request.POST.get('year_built') or None
        amenities_json = request.POST.get('amenities', '[]')
        image_url = request.POST.get('image_url')
        image_upload = request.FILES.get('image_upload')

        try:
            amenities = json.loads(amenities_json)
        except json.JSONDecodeError:
            amenities = []

        if property_obj:
            property = property_obj
        else:
            property = Property(owner=user)

        # Set all fields
        property.title = title
        property.description = description
        property.property_type = property_type
        property.status = status
        property.location = location
        property.address = address
        property.city = city
        property.state = state
        property.zip_code = zip_code
        property.price = price
        property.deposit = deposit
        property.bedrooms = bedrooms
        property.bathrooms = bathrooms
        property.area = square_feet
        property.year_built = year_built
        property.amenities = amenities
        property.image_url = image_url if image_upload is None else ''
        
        if image_upload:
            property.image = image_upload  # Store the uploaded image

        property.save()

        # Handle multiple images (if you're using another input for multiple images)
        images = request.FILES.getlist('images')  # optional enhancement
        for img in images:
            PropertyImage.objects.create(property=property, image=img)

        messages.success(request,
                         "Property updated successfully!" if property_id else "Property added successfully!")
        return redirect('dashboard')

    return render(request, 'manage_property.html', {
        'property': property_obj,
        'pic': profile,
        'images': property_obj.images.all() if property_obj else []
    })

@login_required
def delete_property(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id, owner=request.user)
    property_obj.delete()
    messages.success(request, "Property deleted successfully!")
    return redirect('dashboard')

@login_required
def book_property(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id, status='active')
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        notes = request.POST.get('notes', '')
        
        # Calculate total price (simple daily rate calculation)
        days = (end_date - start_date).days
        total_price = days * property_obj.price
        
        booking = Booking.objects.create(
            property=property_obj,
            user=request.user,
            start_date=start_date,
            end_date=end_date,
            total_price=total_price,
            notes=notes
        )
        
        messages.success(request, "Booking request submitted successfully!")
        return redirect('booking_confirmation', booking_id=booking.id)
    
    return render(request, 'book_property.html', {
        'property': property_obj,
        'available_dates': get_available_dates(property_obj)  # You'll need to implement this
    })

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'booking_confirmation.html', {'booking': booking})

@login_required
def manage_profile(request):
    profile = request.user.profile
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('dashboard')
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'manage_profile.html', {'form': form})

@login_required
def toggle_wishlist(request, property_id):
    property = get_object_or_404(Property, id=property_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        property=property
    )
    
    if not created:
        wishlist_item.delete()
        return JsonResponse({'status': 'removed'})
    
    return JsonResponse({'status': 'added'})

def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

# Utility functions
def get_available_dates(property):
    # Implement your availability logic here
    # This could check against existing bookings
    return []

from django.contrib.auth.decorators import login_required

@login_required
def property_list(request):
    properties = Property.objects.filter(status='active')
    return render(request, 'property_list.html', {'properties': properties})

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Booking  # Assuming you have a Booking model

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user)
    return render(request, 'my_bookings.html', {'bookings': bookings})

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Wishlist

@login_required
def my_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'my_wishlist.html', {'wishlist_items': wishlist_items})