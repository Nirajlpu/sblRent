# SBLRent

SBLRent is a Django-based rental platform for property owners (vendors) and tenants. It features secure registration, property listing, booking, payment integration (Razorpay), and robust user/vendor onboarding with document verification.

## Features
- User and Vendor registration with Aadhaar upload (required for all)
- Vendor KYC via email link (deferred KYC)
- Property listing and management
- Property booking and payment (Razorpay integration)
- Monthly payment logic for bookings
- Secure credential management using python-decouple and `.env`
- Email notifications for registration, KYC, and admin alerts
- Responsive Bootstrap UI

## Tech Stack
- Python 3.12
- Django 5.2.3
- SQLite (default, easy to switch to PostgreSQL/MySQL)
- Razorpay (payment gateway)
- Bootstrap 5 (frontend)
- python-decouple (for environment variables)

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/sblRent.git
cd sblRent
```

### 2. Create and activate a virtual environment
```bash
python3 -m venv myenv
source myenv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the root directory with the following keys:
```
SECRET_KEY=your-django-secret-key
RAZORPAY_KEY_ID=your-razorpay-key-id
RAZORPAY_KEY_SECRET=your-razorpay-key-secret
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-email-password
```

### 5. Apply migrations
```bash
python manage.py migrate
```

### 6. Create a superuser (admin)
```bash
python manage.py createsuperuser
```

### 7. Run the development server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser.

## Folder Structure
- `core/` - Django project settings
- `home/` - Main app (models, views, templates)
- `accounts/` - User account management
- `media/` - Uploaded files (profile pics, Aadhaar, etc.)
- `static/` - Static files (CSS, JS, images)

## Key Files
- `requirements.txt` - Python dependencies
- `manage.py` - Django management script
- `.env` - Environment variables (not committed)

## Security Notes
- Never commit your `.env` file or secret keys to version control.
- Use strong passwords and enable 2FA for your email and admin accounts.

## License


---

**Developed by Niraj Sahani**
