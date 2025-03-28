from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import CustomUserCreationForm
from django.contrib.auth.forms import AuthenticationForm
import random,time
from django.contrib import messages
from django.core.mail import send_mail
from .models import CustomUser
from .forms import CustomUserCreationForm
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils.timezone import now
from datetime import timedelta


# Signup View
def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log in after signup
            return redirect('home')  # Redirect to home page after signup
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    """Handles login authentication."""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect('login')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, "User does not exist. Please sign up.")
            return redirect('login')

        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request, "Incorrect password. Please try again.")
            return redirect('login')

        if not user.is_active:  # Check if user is blocked
            messages.error(request, "Admin has blocked this user.")
            return render(request, 'login.html')

        login(request, user)
        return redirect('home')  # Redirect to home page if successful

    return render(request, 'login.html')

# Logout View
def logout_view(request):
    logout(request)
    return redirect('login')

# generate otp view
def generate_otp():
    """Generates a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    """Sends OTP to user's email"""
    subject = "Your OTP Code for Signup"
    message = f"Your OTP for signup is {otp}. Please enter this OTP to complete your registration."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
    print(f"OTP for {email}: {otp}")  # Debugging (Visible in terminal)

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        email = request.POST.get('email')
        password = request.POST.get('password')
        username = request.POST.get('username')
        confirm_password = request.POST.get('confirm_password')

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "User already exists. Please log in.")
            return redirect('login')  # Redirect to login page

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup.html', {'form': form})

        # Generate and send OTP
        otp = generate_otp()
        send_otp_email(email, otp)

        # Store email, password, and OTP in session
        request.session['signup_email'] = email
        request.session['signup_password'] = password
        request.session['signup_otp'] = otp
        request.session['signup_username'] = username  
        request.session['signup_otp_time'] = time.time()


        return redirect('otp_verification')  # Redirect to OTP verification page

    

    return render(request, 'signup.html', {'form': CustomUserCreationForm()})

# signup page otp verification view
def otp_verification_view(request):
    """Handles OTP verification."""
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        stored_otp = request.session.get('signup_otp')
        email = request.session.get('signup_email')
        password = request.session.get('signup_password')
        username = request.session.get('signup_username')
        otp_time = request.session.get('signup_otp_time')

        # OTP expiration check
        if not stored_otp or not otp_time or time.time() - otp_time > 60:
            messages.error(request, "OTP expired. Please request a new OTP.")
            return redirect('otp_verification')

        if entered_otp == stored_otp:
            if not CustomUser.objects.filter(email=email).exists():
                CustomUser.objects.create_user(username=username, email=email, password=password)
                messages.success(request, "OTP verified successfully! Please log in.")
                request.session.flush()
                return redirect('login')
            else:
                messages.error(request, "User already exists. Please log in.")
                return redirect('login')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'otp.html', {
        'otp_expiry_time': request.session.get('signup_otp_time', 0) + 60 - time.time()
    })

# signup page resent otp verification view
def resend_otp_view(request):
    """Handles OTP resending."""
    if request.method == 'POST':
        email = request.session.get('signup_email')
        username = request.session.get('signup_username')
        password = request.session.get('signup_password')

        if not email or not username or not password:
            messages.error(request, "Session expired. Please sign up again.")
            return redirect('signup')

        # Generate a new OTP
        new_otp = str(random.randint(100000, 999999))
        request.session['signup_otp'] = new_otp
        request.session['signup_otp_time'] = time.time()  # Reset timer

        # Simulate sending OTP (print to console)
        print(f"New OTP for {email}: {new_otp}")

        messages.success(request, "OTP has been resent successfully!")
        return redirect('otp_verification')

    return redirect('otp_verification')






def forgot_password_otp_verification_view(request):
    """Handles email submission and OTP verification"""
    if request.method == 'POST':
        # Check if the request contains an email (initial step)
        if 'email' in request.POST:
            email = request.POST.get('email')

            # Check if the email exists
            if not CustomUser.objects.filter(email=email).exists():
                messages.error(request, "Email does not exist. Please sign up.")
                return redirect('password_otp_verification')  # Stay on email input page

            # Generate OTP and store it in session
            otp = str(random.randint(100000, 999999))
            request.session['reset_otp'] = otp
            request.session['reset_email'] = email
            request.session['otp_expiry'] = (now() + timedelta(minutes=1)).timestamp()

            # Send OTP to email
            send_mail(
                subject="Your OTP",
                message=f"Your OTP is: {otp}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, "OTP sent to your email. It expires in 1 minute.")
            return redirect('forgot_password_otp')  # Redirect to OTP verification page

        # Check if the request contains an OTP (verification step)
        elif 'otp' in request.POST:
            entered_otp = request.POST.get('otp')
            stored_otp = request.session.get('reset_otp')
            expiry_time = request.session.get('otp_expiry')

            if not stored_otp or now().timestamp() > expiry_time:
                messages.error(request, "OTP expired. Please request a new one.")
                return redirect('forgot_password')  # Redirect to email input page

            if entered_otp == stored_otp:
                messages.success(request, "OTP verified. Please reset your password.")
                return redirect('reset_password')

            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('forgot_password_otp')

    # Render the appropriate template based on the URL
    if request.path == '/forgot-password_otp/':
        return render(request, 'forgot_password_otp.html')
    return render(request, 'password_otp_verification.html')


def forgot_password_view(request):
    """Handles Forgot Password - Sends OTP"""
    if request.method == 'POST':
        email = request.POST.get('email')

        if not CustomUser.objects.filter(email=email).exists():
            messages.error(request, "User does not exist.")
            return redirect('forgot_password')  # Stay on same page

        # Generate OTP and store it in session
        otp = str(random.randint(100000, 999999))
        request.session['reset_otp'] = otp
        request.session['reset_email'] = email
        request.session['otp_expiry'] = (now() + timedelta(minutes=1)).timestamp()

        # Send OTP to email
        send_mail(
            subject="Your OTP",
            message=f"Your OTP is: {otp}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        messages.success(request, "OTP sent to your email. It expires in 1 minute.")
        return redirect('password_otp_verification')

    return render(request, 'forgot_password.html')


def reset_otp_view(request):
    """Resends OTP and refreshes timer"""
    email = request.session.get('reset_email')

    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect('forgot_password')

    otp = str(random.randint(100000, 999999))
    request.session['reset_otp'] = otp
    request.session['otp_expiry'] = (now() + timedelta(minutes=1)).timestamp()

    send_mail(
        subject="Your OTP",
        message=f"Your new OTP is: {otp}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

    messages.success(request, "OTP resent. Please check your email.")
    return redirect('forgot_password_otp')

def reset_password_view(request):
    """Handles password reset after OTP verification"""
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password')

        email = request.session.get('reset_email')
        if not email:
            messages.error(request, "Session expired. Please request a new OTP.")
            return redirect('forgot_password')

        user = CustomUser.objects.get(email=email)
        user.set_password(new_password)  # Hash the password
        user.save()

        # Clear session data
        del request.session['reset_email']
        del request.session['reset_otp']
        del request.session['otp_expiry']

        messages.success(request, "Password reset successful. Please log in.")
        return redirect('login')  # Redirect to login page

    return render(request, 'reset_password.html')  # Ensure this template exists