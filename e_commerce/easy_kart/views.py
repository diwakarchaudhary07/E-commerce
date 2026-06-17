import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags

from .forms import RegisterForm, OTPVerificationForm
from .models import CustomUser, OTP


def home(request):
    return render(request, 'index.html')


def product_page(request):
    return render(request, 'blank_page.html', {
        'page_title': 'Product',
        'heading': 'Product',
    })


def category_page(request):
    return render(request, 'blank_page.html', {
        'page_title': 'Category',
        'heading': 'Category',
    })


def gallery_page(request):
    return render(request, 'blank_page.html', {
        'page_title': 'Gallery',
        'heading': 'Gallery',
    })


def about_us(request):
    return render(request, 'blank_page.html', {
        'page_title': 'About Us',
        'heading': 'About Us',
    })


def wishlist_page(request):
    return render(request, 'blank_page.html', {
        'page_title': 'Wishlist',
        'heading': 'Wishlist',
    })


def cart_page(request):
    return render(request, 'blank_page.html', {
        'page_title': 'Cart',
        'heading': 'Cart',
    })


def profile_page(request):
    return render(request, 'blank_page.html', {
        'page_title': 'My Profile',
        'heading': 'My Profile',
    })


def orders_page(request):
    return render(request, 'blank_page.html', {
        'page_title': 'My Orders',
        'heading': 'My Orders',
    })


def send_otp_email(user, otp_code):
    """Send OTP email to user"""
    subject = 'Email Verification OTP - ShopSphere'
    html_message = render_to_string('otp_email.html', {
        'full_name': user.full_name,
        'otp_code': otp_code,
    })
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_welcome_email(user):
    """Send welcome email to user after verification"""
    subject = 'Welcome to ShopSphere!'
    html_message = render_to_string('welcome_email.html', {
        'full_name': user.full_name,
    })
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data['full_name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            base_username = email.split('@')[0]
            unique_username = f"{base_username}_{uuid.uuid4().hex[:6]}"
            user = CustomUser.objects.create(
                username=unique_username,
                full_name=full_name,
                email=email,
                password=make_password(password),
                is_active=False,
                is_email_verified=False,
                mobile_no='',
                address='',
            )
            otp = OTP.generate_otp(user)
            send_otp_email(user, otp.code)
            request.session['email_for_verification'] = email
            messages.success(request, 'Registration successful! Enter the OTP sent to your email.')
            return redirect('verify_otp')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def verify_otp(request):
    """Verify OTP and handle both registration verification and login-by-OTP flows."""
    # Support two flows via session keys:
    # - 'email_for_verification' : registration flow (mark email verified)
    # - 'email_for_login' : login via OTP (authenticate & login)
    email = request.session.get('email_for_verification') or request.session.get('email_for_login')
    is_login_flow = 'email_for_login' in request.session

    if not email:
        messages.error(request, 'Invalid verification request.')
        return redirect('register' if not is_login_flow else 'login')

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('register')

    # If registration verification and already verified, prompt to login
    if not is_login_flow and user.is_email_verified:
        messages.info(request, 'Email already verified. You can log in now.')
        return redirect('login')

    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()

        if not otp_code:
            messages.error(request, 'Please enter the OTP.')
            return render(request, 'verify_otp.html', {'email': email, 'form': OTPVerificationForm()})

        try:
            otp = OTP.objects.get(user=user)

            if otp.is_expired():
                messages.error(request, 'OTP has expired. Please request a new one.')
                return render(request, 'verify_otp.html', {'email': email, 'form': OTPVerificationForm()})

            if otp.verify(otp_code):
                # Registration verification flow
                if not is_login_flow:
                    user.is_email_verified = True
                    # Activate user upon successful email verification so they can authenticate
                    user.is_active = True
                    user.save()
                    send_welcome_email(user)
                    del request.session['email_for_verification']
                    messages.success(request, 'Email verified successfully! Welcome to ShopSphere. You can now log in.')
                    return redirect('login')

                # Login via OTP flow: log the user in without password
                try:
                    # Assign a backend so auth_login works
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    auth_login(request, user)
                    del request.session['email_for_login']
                    messages.success(request, f'Logged in successfully. Welcome back, {user.full_name}!')
                    return redirect('home')
                except Exception:
                    messages.error(request, 'Could not log you in. Please try the password login.')
                    return redirect('login')

            else:
                messages.error(request, 'Invalid OTP. Please try again.')
                return render(request, 'verify_otp.html', {'email': email, 'form': OTPVerificationForm()})

        except OTP.DoesNotExist:
            messages.error(request, 'OTP not found. Please request a new one.')
            return redirect('register')

    return render(request, 'verify_otp.html', {'email': email, 'form': OTPVerificationForm()})


def resend_otp(request):
    """Resend OTP to user email"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, 'Please enter your email.')
            return redirect('verify_otp')

        try:
            # If user exists but not verified, resend verification OTP
            user = CustomUser.objects.get(email=email, is_email_verified=False)
            otp = OTP.generate_otp(user)
            send_otp_email(user, otp.code)
            messages.success(request, 'OTP resent successfully. Check your email.')
            request.session['email_for_verification'] = email
            return redirect('verify_otp')
        except CustomUser.DoesNotExist:
            # Maybe it's a login OTP resend for already verified user
            user_verified = CustomUser.objects.filter(email=email, is_email_verified=True).first()
            if user_verified:
                otp = OTP.generate_otp(user_verified)
                send_otp_email(user_verified, otp.code)
                messages.success(request, 'OTP resent for login. Check your email.')
                request.session['email_for_login'] = email
                return redirect('verify_otp')
            messages.error(request, 'Email not found.')
            return redirect('register')

    return redirect('verify_otp')


def send_login_otp(request):
    """Send OTP specifically for login flow (separate endpoint used by URLs)."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'Please provide an email to send OTP.')
            return redirect('login')

        user = CustomUser.objects.filter(email=email).first()
        if not user:
            messages.error(request, 'Email not registered. Please register first.')
            return redirect('register')

        if not user.is_email_verified:
            messages.warning(request, 'Please verify your email via the registration flow first.')
            request.session['email_for_verification'] = email
            return redirect('verify_otp')

        otp = OTP.generate_otp(user)
        send_otp_email(user, otp.code)
        request.session['email_for_login'] = email
        messages.success(request, 'OTP sent for login. Check your email.')
        return redirect('verify_otp')

    return redirect('login')


def login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Support two actions from the login page: normal password login or send-login-otp
        action = request.POST.get('action', 'login')
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        if action == 'send_otp':
            if not email:
                messages.error(request, 'Please enter your email to receive an OTP.')
                return redirect('login')

            user = CustomUser.objects.filter(email=email).first()
            if not user:
                messages.error(request, 'Email not registered. Please register first.')
                return redirect('register')

            # Only allow login OTP for verified users
            if not user.is_email_verified:
                messages.warning(request, 'Please verify your email first via registration flow.')
                request.session['email_for_verification'] = email
                return redirect('verify_otp')

            otp = OTP.generate_otp(user)
            send_otp_email(user, otp.code)
            request.session['email_for_login'] = email
            messages.success(request, 'OTP sent for login. Check your email.')
            return redirect('verify_otp')

        # Default: password login
        if not email or not password:
            messages.error(request, 'Email and password are required!')
            return redirect('login')

        user = CustomUser.objects.filter(email=email).first()
        if not user:
            messages.error(request, 'Invalid email or password!')
            return redirect('login')

        if not user.is_email_verified:
            messages.warning(request, 'Please verify your email first before logging in.')
            request.session['email_for_verification'] = email
            return redirect('verify_otp')

        # Django's default authentication backend authenticates by username, not by email.
        authenticated_user = authenticate(request, username=user.username, password=password)
        if authenticated_user is not None:
            auth_login(request, authenticated_user)

            if remember_me:
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)

            messages.success(request, f'Welcome back, {authenticated_user.full_name}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid email or password!')
            return redirect('login')

    return render(request, 'login.html')


def logout(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('home')
