# Payment view for user after vendor approval
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse 
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime
from .models import Property, Profile, CustomUser, Booking, Review, PropertyImage
from .forms import PropertyForm, ProfileForm
import os
from .models import Wishlist
from dateutil.relativedelta import relativedelta

from django.core.paginator import Paginator
from django.template.loader import render_to_string

from django.utils import timezone
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.core.mail import send_mail
import threading

def send_email_async(subject, message, from_email, recipient_list):
    send_mail(subject=subject, message=message, from_email=from_email, recipient_list=recipient_list, fail_silently=False)

def home(request):
    # logout(request)
    user = request.user
    profile = user.profile if user.is_authenticated else None
    featured_list = Property.objects.filter(status='active', is_featured=True)
    recent_list = Property.objects.filter(status='active').order_by('-date_added')

    featured_paginator = Paginator(featured_list, 6)
    recent_paginator = Paginator(recent_list, 6)

    page_featured = request.GET.get('page_featured')
    page_recent = request.GET.get('page_recent')

    featured_properties = featured_paginator.get_page(page_featured)
    recent_properties = recent_paginator.get_page(page_recent)

    now = timezone.now()

    # AJAX response for featured
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'page_featured' in request.GET:
        html = render_to_string('partials/_featured_properties.html', {
            'featured_properties': featured_properties,
            'now': now
        })
        return JsonResponse({'html': html})

    # AJAX response for recent
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'page_recent' in request.GET:
        html = render_to_string('partials/_recent_properties.html', {
            'recent_properties': recent_properties,
            'now': now
        })
        return JsonResponse({'html': html})

    return render(request, 'index.html', {
        'featured_properties': featured_properties,
        'pic': profile if profile else None,
        'recent_properties': recent_properties,
        'now': now,
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





from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import Property, Booking



@login_required
def dashboard(request):
    user = request.user
    profile = user.profile
    page_number = request.GET.get('page')

    if profile.role == 'vendor':
        # Vendor-specific properties and stats
        properties = Property.objects.filter(owner=user).order_by('-date_added')
        paginator = Paginator(properties, 6)
        page_obj = paginator.get_page(page_number)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html = render_to_string('partials/_vendor_properties.html', {
                'properties': page_obj
            }, request=request)
            return JsonResponse({'html': html})

        stats = {
            'total_properties': properties.count(),
            'active_properties': properties.filter(status='active').count(),
            'pending_properties': properties.filter(status='pending').count(),
            'rented_properties': properties.filter(status='rented').count(),
            'total_bookings': Booking.objects.filter(property__owner=user).count(),
            'pending_bookings': Booking.objects.filter(property__owner=user, status='pending').count()
        }

        return render(request, 'vendor_dashboard.html', {
            'properties': page_obj,
            'stats': stats,
            'pic': profile,
            'recent_bookings': Booking.objects.filter(property__owner=user).order_by('-created_at')[:5]
        })

    else:
        # User-specific view
        all_properties = Property.objects.filter(status='active').order_by('-date_added')
        paginator = Paginator(all_properties, 6)
        page_obj = paginator.get_page(page_number)

        bookings = Booking.objects.filter(user=user).select_related('property')

        return render(request, 'user_dashboard.html', {
            'properties': page_obj,
            'pic': profile,
            'bookings': bookings,
            'wishlist': all_properties.filter(wishlist__user=user)[:4]
        })

def property_detail(request, property_id):
    user = request.user
    profile = user.profile if user.is_authenticated else None
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
       'pic': profile if profile else None,
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

    if profile.role == 'vendor':

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
            video_file = request.FILES.get('video')

            latitude = request.POST.get('latitude') or None
            longitude = request.POST.get('longitude') or None

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
            property.latitude = latitude
            property.longitude = longitude
            property.price = price
            property.deposit = deposit
            property.bedrooms = bedrooms
            property.bathrooms = bathrooms
            property.area = square_feet
            property.year_built = year_built
            property.amenities = amenities
            property.last_updated=datetime.now()
            property.image_url = image_url if image_upload is None else ''
        
            if image_upload:
                property.image = image_upload  # Store the uploaded image
            if video_file:
                property.video = video_file

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
    else:
        messages.success(request,"You are normal user.You can't add Property")
        return redirect('dashboard')


@login_required
def delete_property(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id, owner=request.user)
    property_obj.delete()
    messages.success(request, "Property deleted successfully!")
    return redirect('dashboard')

@login_required(login_url='/login/')
def book_property(request, property_id):
    user = request.user
    profile = user.profile if user.is_authenticated else None
    if profile and profile.role == 'vendor':
        messages.warning(request, "Vendors cannot book properties directly. Please create a tenant account to proceed.")
        return redirect('home')
    property_obj = get_object_or_404(Property, id=property_id, status='active')

    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        guest = request.POST.get('guests')
        notes = request.POST.get('notes', '')
        total_price_str = request.POST.get('calculated_total_price')
        payment_type = 'monthly'  # Always monthly

        if not start_date_str or not end_date_str:
            messages.error(request, "Both check-in and check-out dates are required.")
            return redirect('book_property', property_id=property_id)

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('book_property', property_id=property_id)

        if start_date >= end_date:
            messages.error(request, "Check-out date must be after check-in date.")
            return redirect('book_property', property_id=property_id)

        from decimal import Decimal
        try:
            total_price = Decimal(total_price_str)
        except (TypeError, ValueError):
            days = (end_date - start_date).days
            total_price = (Decimal(days) / Decimal(30)) * property_obj.price

        # Calculate monthly dues
        monthly_due_dates = []
        current = start_date
        while current < end_date:
            next_due = current + relativedelta(months=1)
            if next_due > end_date:
                next_due = end_date
            monthly_due_dates.append({
                'due_date': next_due.strftime('%Y-%m-%d'),
                'amount': float(property_obj.price),
                'paid': False
            })
            current = next_due

        # Only first month paid
        if monthly_due_dates:
            monthly_due_dates[0]['paid'] = True

        booking = Booking.objects.create(
            property=property_obj,
            user=request.user,
            start_date=start_date,
            end_date=end_date,
            total_price=total_price,
            guest=guest,
            notes=notes,
            payment_type=payment_type,
            monthly_due_dates=monthly_due_dates
        )
        
        messages.success(request, "Booking successful!")

        

        from django.urls import reverse

        first_month = booking.start_date.strftime('%B')
        first_year = booking.start_date.year
        pay_url = reverse('make_payment', kwargs={'booking_id': booking.id})
        return redirect(f'{pay_url}?month={first_month}&year={first_year}')

    return render(request, 'book_property.html', {
        'property': property_obj,
        'pic': profile if profile else None,
        'available_dates': get_available_dates(property_obj)
    })

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    # Mark property as rented if booking is paid
    booking.status = 'paid'
   

    vendor_email = booking.property.owner.email
    customer_email = request.user.email

    t1 = threading.Thread(
        target=send_email_async,
        kwargs={
            "subject": "A property has been booked",
            "message": (
                f"Dear {booking.property.owner.username},\n\n"
                f"We are pleased to inform you that {request.user.username} has successfully booked your property through SBLRent.\n\n"
                f"--- Property Details ---\n"
                f"Title: {booking.property.title}\n"
                f"Location: {booking.property.location}\n"
                f"Address: {booking.property.address}, {booking.property.city}, {booking.property.state} - {booking.property.zip_code}\n"
                f"Google Location: https://www.google.com/maps/search/?api=1&query={booking.property.latitude},{booking.property.longitude}\n"
                f"Monthly Rent: ₹{booking.property.price}\n\n"
                f"--- Booking Details ---\n"
                f"Start Date: {booking.start_date}\n"
                f"End Date: {booking.end_date}\n\n"
                f"Thank you for choosing SBLRent to connect with reliable tenants.\n"
                f"If you have any questions or need assistance, please reach out to our support team at support@sblrent.com.\n\n"
                f"Best regards,\n"
                f"SBLRent Team"
            ),
            "from_email": None,
            "recipient_list": [vendor_email],
        }
    )

    if booking.property.status != 'rented':
        t1.start()

    t2 = threading.Thread(
        target=send_email_async,
        kwargs={
            "subject": "Your property booking has been confirmed",
            "message": (
                f"Dear {request.user.username},\n\n"
                f"Congratulations! Your booking has been successfully confirmed through SBLRent.\n\n"
                f"--- Property Details ---\n"
                f"Title: {booking.property.title}\n"
                f"Location: {booking.property.location}\n"
                f"Address: {booking.property.address}, {booking.property.city}, {booking.property.state} - {booking.property.zip_code}\n"
                f"Google Location: https://www.google.com/maps/search/?api=1&query={booking.property.latitude},{booking.property.longitude}\n"
                f"Monthly Rent: ₹{booking.property.price}\n\n"
                f"--- Booking Details ---\n"
                f"Start Date: {booking.start_date}\n"
                f"End Date: {booking.end_date}\n\n"
                f"We look forward to making your stay comfortable and enjoyable.\n"
                f"For any queries or assistance, please contact us at support@sblrent.com.\n\n"
                f"Best regards,\n"
                f"SBLRent Team"
            ),
            "from_email": None,
            "recipient_list": [customer_email],
        }
    )
    if booking.property.status != 'rented':
        t2.start()
    booking.property.status = 'rented'
    booking.property.save()

    booking.save()
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

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Property, Wishlist

@login_required(login_url='/login/')
def toggle_wishlist(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)

    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, property=property_obj)

    if not created:
        wishlist_item.delete()
        status = "removed"
    else:
        status = "added"

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": status})
    else:
        return redirect(request.META.get("HTTP_REFERER", "home"))

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
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Property

from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from .models import Property, Wishlist
from django.shortcuts import render

from django.core.paginator import Paginator
from .models import Property, Wishlist

def property_list(request):
    user = request.user
    profile = user.profile if user.is_authenticated else None
    # Determine initial queryset
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'vendor':
        # Vendor: show only their properties
        queryset = Property.objects.filter(owner=request.user)
    elif request.GET.get('view') == 'wishlist' and request.user.is_authenticated:
        # Wishlist view
        queryset = Property.objects.filter(wishlist__user=request.user)
    else:
        # Default: active properties
        queryset = Property.objects.filter(status='active')

    # Apply filters for all cases
    location = request.GET.get('location')
    property_type = request.GET.get('property_type')
    price_range = request.GET.get('price_range')

    if location:
        queryset = queryset.filter(location__icontains=location)
    if property_type and property_type != "Any Type":
        queryset = queryset.filter(property_type=property_type)
    if price_range:
        if price_range == "Under ₹10,000":
            queryset = queryset.filter(price__lt=10000)
        elif price_range == "₹10,000-₹20,000":
            queryset = queryset.filter(price__gte=10000, price__lte=20000)
        elif price_range == "₹20,000-₹30,000":
            queryset = queryset.filter(price__gte=20000, price__lte=30000)
        elif price_range == "Over ₹30,000":
            queryset = queryset.filter(price__gt=30000)

    # Order newest first
    queryset = queryset.order_by('-date_added')

    # Add wishlist status for heart icon
    if request.user.is_authenticated:
        wishlist_ids = set(
            Wishlist.objects.filter(user=request.user).values_list('property_id', flat=True)
        )
        for prop in queryset:
            prop.in_wishlist = prop.id in wishlist_ids
    else:
        for prop in queryset:
            prop.in_wishlist = False

    # Pagination
    paginator = Paginator(queryset, 6)  # 6 per page
    page = request.GET.get('page')
    properties = paginator.get_page(page)

    return render(request, 'property_list.html', {
        'properties': properties,
        'pic': profile if profile else None,
        'showing_wishlist': request.GET.get('view') == 'wishlist',
        'is_vendor': request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'vendor'
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Booking  # Assuming you have a Booking model

@login_required
def my_bookings(request):
    user = request.user
    profile = user.profile if user.is_authenticated else None

   
    if profile.role == 'vendor':
        bookings = Booking.objects.filter(property__owner=user).select_related('user', 'property')
    else:
        bookings = Booking.objects.filter(user=user).select_related('property')

    return render(request, 'my_bookings.html', {
        'bookings': bookings,
        'pic': profile if profile else None,
        'is_vendor': profile.role == 'vendor'
    })


# Allow users to cancel/delete their own bookings
@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    # Allow cancel if payment is complete
    if True:  # booking.status in ['pending', 'approved', 'active', 'paid'] and booking.total_price == booking.total_amount
        booking.status = 'cancelled'
        booking.property.status = 'active'
        booking.property.save()

        # Send cancellation email notifications
        vendor_email = booking.property.owner.email
        customer_email = request.user.email

        vendor_message = (
            f"Dear {booking.property.owner.username},\n\n"
            f"We would like to inform you that the booking for your property '{booking.property.title}' "
            f"has been cancelled by {request.user.username}.\n\n"
            f"--- Property Details ---\n"
            f"Title: {booking.property.title}\n"
            f"Location: {booking.property.location}\n"
            f"Address: {booking.property.address}, {booking.property.city}, {booking.property.state} - {booking.property.zip_code}\n"
            f"Google Location: https://www.google.com/maps/search/?api=1&query={booking.property.latitude},{booking.property.longitude}\n"
            f"Monthly Rent: ₹{booking.property.price}\n\n"
            f"Best regards,\n"
            f"SBLRent Team"
        )

        customer_message = (
            f"Dear {request.user.username},\n\n"
            f"Your booking for the property '{booking.property.title}' has been successfully cancelled.\n\n"
            f"--- Property Details ---\n"
            f"Title: {booking.property.title}\n"
            f"Location: {booking.property.location}\n"
            f"Address: {booking.property.address}, {booking.property.city}, {booking.property.state} - {booking.property.zip_code}\n"
            f"Google Location: https://www.google.com/maps/search/?api=1&query={booking.property.latitude},{booking.property.longitude}\n"
            f"Monthly Rent: ₹{booking.property.price}\n\n"
            f"Best regards,\n"
            f"SBLRent Team"
        )

        t1 = threading.Thread(
            target=send_email_async,
            kwargs={
                "subject": "Booking Cancelled - SBLRent",
                "message": vendor_message,
                "from_email": None,
                "recipient_list": [vendor_email],
            }
        )
        t2 = threading.Thread(
            target=send_email_async,
            kwargs={
                "subject": "Your Booking Has Been Cancelled - SBLRent",
                "message": customer_message,
                "from_email": None,
                "recipient_list": [customer_email],
            }
        )
        t1.start()
        t2.start()

        booking.delete()
        messages.success(request, "Booking has been cancelled.")
    else:
        messages.error(request, "This booking cannot be cancelled.")
    return redirect('my_bookings')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Wishlist

@login_required
def my_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('property').order_by('-property__date_added')
    return render(request, 'my_wishlist.html', {'wishlist_items': wishlist_items})

# @login_required
# def vendor_booking_requests(request):
#     if request.user.profile.role != 'vendor':
#         return redirect('home')
#     bookings = Booking.objects.filter(property__owner=request.user)
#     return render(request, 'vendor_bookings.html', {'bookings': bookings})

# @login_required
# def approve_booking(request, booking_id):
#     booking = get_object_or_404(Booking, id=booking_id, property__owner=request.user)
#     booking.status = 'approved'
#     booking.save()
#     return redirect('vendor_booking_requests')

# @login_required
# def decline_booking(request, booking_id):
#     booking = get_object_or_404(Booking, id=booking_id, property__owner=request.user)
#     booking.status = 'declined'
#     booking.save()
#     return redirect('vendor_booking_requests')


# Reservation details view

# Reservation details view
from django.db import models
from .models import Review 
from django.utils.dateparse import parse_date
from django.contrib import messages
from django.utils.timezone import now  # Optional, for date comparison

from calendar import month_name
from django.utils import timezone
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta


@login_required
def reservation_details(request, booking_id):
    from calendar import month_name
    from dateutil.relativedelta import relativedelta
    from django.utils.dateparse import parse_date
    from datetime import datetime

    user = request.user
    profile = user.profile if user.is_authenticated else None

    booking = get_object_or_404(
        Booking.objects.select_related('property', 'user__profile'),
        id=booking_id
    )

    # Handle extension form submission
    if request.method == 'POST':
        new_end_date_str = request.POST.get('new_end_date')
        new_end_date = parse_date(new_end_date_str)
        if new_end_date and new_end_date > booking.end_date:
            booking.end_date = new_end_date
            booking.save()
            messages.success(request, 'Checkout date extended successfully.')
            return redirect('reservation_details', booking_id=booking.id)
        else:
            messages.error(request, 'Invalid date. Please select a future date.')

    booking_duration = (booking.end_date - booking.start_date).days
    previous_bookings = Booking.objects.filter(user=booking.user).exclude(id=booking.id).count()
    user_reviews = Review.objects.filter(user=booking.user)
    average_rating = round(user_reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0, 1)
    current_year = datetime.now().year

    # Generate monthly payments: each period is from start_date to same day next month
    monthly_payments = []
    payment_data = booking.payment_data or []
    payment_lookup = {}
    for year_entry in payment_data:
        year = year_entry.get('year')
        for month_name_str, payments in year_entry.get('months', {}).items():
            if payments:
                try:
                    month = datetime.strptime(month_name_str, "%B").month
                except Exception:
                    continue
                payment_lookup[(year, month)] = payments[0]

    current = booking.start_date
    end = booking.end_date
    while current < end:
        next_month = current + relativedelta(months=1)
        # If next_month's day is less than start_date's day, adjust to last day of month
        try:
            period_end = next_month.replace(day=current.day)
        except ValueError:
            # For months with fewer days, use last day of next month
            from calendar import monthrange
            last_day = monthrange(next_month.year, next_month.month)[1]
            period_end = next_month.replace(day=last_day)
        if period_end > end:
            period_end = end
        year, month = current.year, current.month
        payment = payment_lookup.get((year, month))
        payment_date = None
        amount = None
        if payment:
            try:
                payment_date = datetime.strptime(payment['payment_date'], "%Y-%m-%d").date()
            except Exception:
                payment_date = current
            try:
                amount = float(payment['payment_amount'])
            except Exception:
                amount = float(booking.property.price)
        else:
            payment_date = current
            amount = float(booking.property.price)
        monthly_payments.append({
            "month": month_name[month],
            "year": year,
            "date": payment_date,
            "amount": amount,
            "period_start": current,
            "period_end": period_end,
            "status": "paid" if payment else "pending"
        })
        current = period_end

    # Filter out past periods: only show from today onwards
    from django.utils.timezone import localdate
    # Use Django's timezone utilities to get IST (Asia/Kolkata) date
    # today = timezone.localtime(timezone.now(), timezone.get_fixed_timezone(330)).date()

    today = date(2028, 12, 1)  # Year, Month, Day
    print("Today Niraj:", today)

    monthly_payments = [p for p in monthly_payments if p["date"] <= today]
    # Filter by selected year if provided
    print("Monthly Payments Niraj:", monthly_payments)
 

    selected_year = int(request.GET.get('year', booking.start_date.year))
    filtered_payments = []
    for payment in monthly_payments:
        if payment['year'] == selected_year:
            # Start year: show from start month
            if selected_year == booking.start_date.year:
                if payment['period_start'].month >= booking.start_date.month:
                    filtered_payments.append(payment)
            # End year: show up to end month
            elif selected_year == booking.end_date.year:
                if payment['period_start'].month <= booking.end_date.month:
                    filtered_payments.append(payment)
            # Middle years: show all months
            else:
                filtered_payments.append(payment)

    return render(request, 'reservation_details.html', {
        'booking': booking,
        'current_year': current_year,
        'booking_duration': booking_duration,
        'previous_bookings': previous_bookings,
        'pic': profile if profile else None,
        'average_rating': average_rating,
        'monthly_payments': filtered_payments,
        'selected_year': selected_year,
    })

# User payment after vendor approval

@login_required
@csrf_exempt
def make_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    month = request.GET.get('month')
    year = request.GET.get('year')
    if not month or not year:
        messages.error(request, "Invalid payment period.")
        return redirect('book_property', booking_id=booking.id)

    if request.method == 'POST':
        from datetime import datetime
        now = datetime.now()
        payment_date = now.strftime('%Y-%m-%d')
        payment_time = now.strftime('%H:%M:%S')

        new_payment = {
            'payment_date': payment_date,
            'payment_time': payment_time,
            'payment_amount': float(booking.total_price)
        }

        data = booking.payment_data

        year = int(year)
        year_entry = next((entry for entry in data if entry['year'] == year), None)
        if year_entry:
            if month in year_entry['months']:
                year_entry['months'][month].append(new_payment)
            else:
                year_entry['months'][month] = [new_payment]
        else:
            data.append({
                'year': year,
                'months': {
                    month: [new_payment]
                }
            })

        booking.payment_data = data

        # Mark the first unpaid month as paid
        unpaid_found = False
        for due in booking.monthly_due_dates:
            if not due['paid'] and not unpaid_found:
                due['paid'] = True
                unpaid_found = True
                break

        booking.save()
        messages.success(request, f"Payment for {month} {year} successful!")
        return redirect('booking_confirmation', booking_id=booking.id)

    return render(request, 'make_payment.html', {
        'booking': booking,
        'month': month,
        'year': year
    })

# Example task (Celery)
from django.core.mail import send_mail
from django.utils import timezone
from .models import Booking

def send_payment_reminders():
    today = timezone.now().date()
    for booking in Booking.objects.filter(payment_type='monthly'):
        for due in booking.monthly_due_dates:
            due_date = datetime.strptime(due['due_date'], '%Y-%m-%d').date()
            if not due['paid'] and (due_date - today).days == 3:
                send_mail(
                    'Payment Reminder',
                    f'Your next payment of ₹{due["amount"]} is due on {due_date}.',
                    'noreply@sblrent.com',
                    [booking.user.email]
                )
