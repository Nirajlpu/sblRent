from django.shortcuts import render

# -----------(IMPORT)add manually-----------
from django.http import HttpResponse, JsonResponse 
# --- User Registration, Login, Dashboard, Vendor CRUD, Booking ---
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.shortcuts import redirect
from .models import Property
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.contrib.auth.models import User
from .models import Profile


# Create your views here.

from django.shortcuts import render
from .models import Property  # adjust import path if needed

def home(request):
    properties = Property.objects.all()  # fetch all records
    return render(request, 'index.html', {'properties': properties})

def register_user(request):
    if request.method == 'POST':
        first_name=request.POST.get('first_name')
        last_name=request.POST.get('last_name')
        email=request.POST.get('email')
        username=request.POST.get('username')
        password=request.POST.get('password')
        role = request.POST['role']
        user=User.objects.filter(username=username)
        if user.exists():
            messages.info(request, f"{username} Username is already taken!")
            return redirect('register')
        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username,
            password=password
        )
        Profile.objects.create(user=user, role=role)
        messages.info(request, "Your account is created successfully!")
        return redirect('register')

    return render(request, 'register.html')

def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

@login_required
def dashboard(request):
    if request.user.profile.role == 'vendor':
        properties = Property.objects.filter(owner=request.user)
        return render(request, 'vendor_dashboard.html', {'properties': properties})
    else:
        properties = Property.objects.all()
        return render(request, 'user_dashboard.html', {'properties': properties})

@login_required
def add_property(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        location = request.POST.get('location')
        image_url = request.POST.get('image_url')
        Property.objects.create(
            title=title,
            description=description,
            price=price,
            location=location,
            image_url=image_url,
            owner=request.user
        )
        return redirect('dashboard')
    return render(request, 'add_property.html')

@login_required
def delete_property(request,id):
    queryset=Property.objects.get(id=id)
    queryset.delete()

    return redirect('dashboard')
    
@login_required
def book_property(request, property_id):
    property = Property.objects.get(id=property_id)
    # Add logic to mark property as booked by the current user or show booking form
    return render(request, 'book_property.html', {'property': property})

#update
@login_required
def updateProperty(request, property_id):
    property = Property.objects.get(id=property_id)

    if request.method == 'POST':
        property.title = request.POST.get('title')
        property.description = request.POST.get('description')
        property.price = request.POST.get('price')
        property.location = request.POST.get('location')
        property.image_url = request.POST.get('image_url')

        property.save()
        messages.success(request, "Property updated successfully!")
        return redirect('dashboard')  # redirect to the property list, adjust if needed

    return render(request, 'add_property.html', {'property': property})

# Logout view
def logout_user(request):
    logout(request)
    return redirect('login')