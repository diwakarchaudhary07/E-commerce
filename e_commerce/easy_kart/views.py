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
    """Verify OTP and mark email as verified"""
    email = request.session.get('email_for_verification')

    if not email:
        messages.error(request, 'Invalid verification request.')
        return redirect('register')

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('register')

    if user.is_email_verified:
        messages.info(request, 'Email already verified. You can log in now.')
        return redirect('login')

    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()

        if not otp_code:
            messages.error(request, 'Please enter the OTP.')
            return render(request, 'verify_otp.html', {'email': email})

        try:
            otp = OTP.objects.get(user=user)

            if otp.is_expired():
                messages.error(request, 'OTP has expired. Please request a new one.')
                return render(request, 'verify_otp.html', {'email': email})

            if otp.verify(otp_code):
                user.is_email_verified = True
                user.save()
                send_welcome_email(user)
                del request.session['email_for_verification']
                messages.success(request, 'Email verified successfully! Welcome to ShopSphere. You can now log in.')
                return redirect('login')
            else:
                messages.error(request, 'Invalid OTP. Please try again.')
                return render(request, 'verify_otp.html', {'email': email})

        except OTP.DoesNotExist:
            messages.error(request, 'OTP not found. Please register again.')
            return redirect('register')

    return render(request, 'verify_otp.html', {'email': email})


def resend_otp(request):
    """Resend OTP to user email"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, 'Please enter your email.')
            return redirect('verify_otp')

        try:
            user = CustomUser.objects.get(email=email, is_email_verified=False)
            otp = OTP.generate_otp(user)
            send_otp_email(user, otp.code)
            messages.success(request, 'OTP resent successfully. Check your email.')
            request.session['email_for_verification'] = email
            return redirect('verify_otp')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Email not found or already verified.')
            return redirect('register')

    return redirect('verify_otp')


def login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

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

        authenticated_user = authenticate(request, email=email, password=password)
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
