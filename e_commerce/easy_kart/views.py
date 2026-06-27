import uuid

from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags

from .forms import RegisterForm, OTPVerificationForm, ProfileForm, TestEmailForm, ContactForm
from .models import CustomUser, OTP, Category, Profile, Product, Gallery, AboutUs, Contact, WishlistItem, Order, OrderItem , TeamMember
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST


def home(request):
    categories = Category.objects.filter(is_active=True).order_by('name')
    products = Product.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'index.html', {
        'categories': categories,
        'products': products,
        'page_title': 'Home',
    })


def product_page(request):
    products = Product.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'product_list.html', {
        'page_title': 'Products',
        'heading': 'Products',
        'products': products,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return render(request, 'product_detail.html', {
        'page_title': product.name,
        'heading': product.name,
        'product': product,
    })


def category_detail(request, slug):
    category = Category.objects.filter(slug=slug, is_active=True).first()
    if not category:
        return render(request, 'blank_page.html', {
            'page_title': 'Category not found',
            'heading': 'Category not found',
            'message': 'The requested category does not exist.',
        })

    products = category.products.filter(is_active=True).order_by('-created_at')
    return render(request, 'category_detail.html', {
        'category': category,
        'products': products,
    })


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = request.session.get('cart', {})
    cart[str(product.id)] = cart.get(str(product.id), 0) + 1
    request.session['cart'] = cart
    messages.success(request, f'Added {product.name} to cart.')
    return redirect('cart')


def cart_page(request):
    cart_data = request.session.get('cart', {})
    product_ids = [int(pid) for pid in cart_data.keys() if pid.isdigit()]
    products = Product.objects.filter(id__in=product_ids)
    cart_items = []
    total = Decimal('0.00')

    for product in products:
        quantity = cart_data.get(str(product.id), 0)
        price = product.get_discounted_price()
        item_total = price * quantity
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'price': price,
            'item_total': item_total,
        })
        total += item_total

    return render(request, 'cart.html', {
        'page_title': 'Cart',
        'heading': 'My Cart',
        'cart_items': cart_items,
        'cart_total': total,
    })


@login_required(login_url='login')
def checkout(request):
    cart_data = request.session.get('cart', {})
    if not cart_data:
        messages.info(request, 'Your cart is empty. Add some products to place an order.')
        return redirect('product')

    product_ids = [int(pid) for pid in cart_data.keys() if pid.isdigit()]
    products = Product.objects.filter(id__in=product_ids)
    order_items = []
    total = Decimal('0.00')

    for product in products:
        quantity = cart_data.get(str(product.id), 0)
        unit_price = product.get_discounted_price()
        item_total = unit_price * quantity
        order_items.append({
            'product': product,
            'quantity': quantity,
            'unit_price': unit_price,
            'item_total': item_total,
        })
        total += item_total

    if request.method == 'POST':
        shipping_address = request.POST.get('shipping_address', '').strip() or request.user.address
        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            shipping_address=shipping_address,
        )

        for item in order_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                total_price=item['item_total'],
            )

        order.calculate_total()
        request.session['cart'] = {}
        messages.success(request, f'Your order {order.order_number} has been placed successfully!')
        return redirect('my_orders')

    return render(request, 'checkout.html', {
        'page_title': 'Checkout',
        'heading': 'Checkout',
        'order_items': order_items,
        'order_total': total,
        'shipping_address': request.user.address,
    })


@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('order_items__product')
    return render(request, 'my_orders.html', {
        'page_title': 'My Orders',
        'heading': 'My Orders',
        'orders': orders,
    })


def category_page(request):
    categories = Category.objects.filter(is_active=True).order_by('name')
    return render(request, 'categories.html', {
        'categories': categories,
    })


def gallery_page(request):
    gallery_items = Gallery.objects.filter(is_active=True).order_by('order', '-created_at')
    return render(request, 'gallery.html', {
        'page_title': 'Gallery',
        'heading': 'Gallery',
        'gallery_items': gallery_items,
    })


def about_us(request):
    about = AboutUs.objects.filter(is_active=True).first()
    if not about:
        about = None
    return render(request, 'about_us.html', {
        'page_title': 'About Us',
        'heading': 'About Us',
        'about': about,
    })


def wishlist_page(request):
    return render(request, 'blank_page.html', {
        'page_title': 'Wishlist',
        'heading': 'Wishlist',
    })


@login_required
def profile_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'profile.html', {
        'page_title': 'My Profile',
        'heading': 'My Profile',
        'profile': profile,
    })


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()

            # sync overlapping fields back to the user model
            user = request.user
            sync_fields = ['full_name', 'email', 'mobile_no', 'alternate_mobile_no', 'dob', 'address', 'profile_image', 'gender']
            for f in sync_fields:
                if hasattr(profile, f) and hasattr(user, f):
                    try:
                        setattr(user, f, getattr(profile, f))
                    except Exception:
                        pass
            try:
                user.save()
            except Exception:
                # ignore save errors (e.g., email uniqueness) and continue
                pass

            messages.success(request, 'Profile updated successfully.')
            return redirect('my_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profile_edit.html', {
        'page_title': 'Edit Profile',
        'heading': 'Edit Profile',
        'form': form,
        'profile': profile,
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
    from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER

    send_mail(
        subject,
        plain_message,
        from_email,
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
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']

            base_username = email.split('@')[0]
            unique_username = f"{base_username}_{uuid.uuid4().hex[:6]}"

            try:
                registration = form.save(commit=False)
                registration.password = make_password(password)
                registration.is_active = False
                registration.save()
                # use create_user to ensure password is set properly
                user = CustomUser.objects.create_user(
                    username=unique_username,
                    email=email,
                    password=password,
                    full_name=full_name,
                    is_active=False,
                    is_email_verified=False,
                    mobile_no='',
                    address='',
                )
            except Exception as e:
                messages.error(request, f'Error creating account: {e}')
                return render(request, 'register.html', {'form': form})

            otp = OTP.generate_otp(user)
            try:
                send_otp_email(user, otp.code)
            except Exception as e:
                # Clean up partial registration if email cannot be sent
                otp.delete()
                user.delete()
                if hasattr(registration, 'pk'):
                    registration.delete()
                messages.error(request, f'Unable to send OTP email: {e}. Please try again.')
                return render(request, 'register.html', {'form': form})

            request.session['email_for_verification'] = email.lower()
            messages.success(request, 'Registration successful! Enter the OTP sent to your email.')
            return redirect('verify_otp')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def verify_otp(request):
    """Verify OTP for registration email verification only."""
    posted_email = request.POST.get('email', '').strip().lower() if request.method == 'POST' else ''
    email = posted_email or request.session.get('email_for_verification', '').strip().lower()

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

    form = OTPVerificationForm(request.POST or None, initial={'email': email})

    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()

        if not otp_code:
            messages.error(request, 'Please enter the OTP.')
            return render(request, 'verify_otp.html', {'email': email, 'form': form})

        try:
            otp = OTP.objects.get(user=user)

            if otp.is_expired():
                messages.error(request, 'OTP has expired. Please request a new one.')
                return render(request, 'verify_otp.html', {'email': email, 'form': form})

            if otp.verify(otp_code):
                user.is_email_verified = True
                user.is_active = True
                user.save()
                send_welcome_email(user)
                request.session.pop('email_for_verification', None)
                messages.success(request, 'Registration successful! Your email has been verified and you can now log in.')
                return redirect('login')
            else:
                messages.error(request, 'Invalid OTP. Please try again.')
                return render(request, 'verify_otp.html', {'email': email, 'form': form})

        except OTP.DoesNotExist:
            messages.error(request, 'OTP not found. Please request a new one.')
            return redirect('register')

    return render(request, 'verify_otp.html', {'email': email, 'form': form})


def resend_otp(request):
    """Resend OTP to user email"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower() or request.session.get('email_for_verification', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email.')
            return redirect('verify_otp')
        try:
            # Only allow resending OTP for registration verification
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


def send_login_otp(request):
    """Send OTP specifically for login flow (separate endpoint used by URLs)."""
    # Login-by-OTP flow is disabled. Users should log in with email/password.
    messages.error(request, 'Login via OTP is disabled. Please use your password to log in.')
    return redirect('login')


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_obj = form.save()
            messages.success(request, 'Your message has been sent successfully. We will get back to you soon!')
            return redirect('contact')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm()

    return render(request, 'contact.html', {
        'page_title': 'Contact Us',
        'heading': 'Contact Us',
        'form': form,
    })


def send_test_email(request):
    """Test SMTP email functionality"""
    if request.method == 'POST':
        form = TestEmailForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message_body = form.cleaned_data['message']
            recipient_email = form.cleaned_data['recipient_email']
            from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
            try:
                send_mail(
                    subject,
                    message_body,
                    from_email,
                    [recipient_email],
                    fail_silently=False,
                )
                return render(request, 'email_sent.html', {
                    'message': f'Test email sent successfully to {recipient_email}!',
                    'status': 'success',
                    'recipient': recipient_email,
                    'from_email': from_email,
                })
            except Exception as e:
                return render(request, 'email_sent.html', {
                    'message': f'Error sending email: {e}',
                    'status': 'error',
                    'from_email': from_email,
                })
    else:
        form = TestEmailForm()

    return render(request, 'send_test_email.html', {
        'form': form,
        'from_email': settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
    })


@login_required(login_url='login')
def wishlist_page(request):
    wishlist_items = WishlistItem.objects.filter(user=request.user).select_related('product', 'product__category')
    
    context = {
        'page_title': 'My Wishlist',
        'heading': 'My Wishlist',
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_items.count(),
    }
    return render(request, 'wishlist.html', context)


@login_required(login_url='login')
def add_to_wishlist(request, slug):
    try:
        product = Product.objects.get(slug=slug)
        wishlist_item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product=product
        )
        if created:
            messages.success(request, f'{product.name} added to wishlist!')
        else:
            messages.info(request, f'{product.name} is already in your wishlist.')
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
    
    # Redirect to referrer or wishlist page
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))


@login_required(login_url='login')
def buy_now(request, slug):
    """Add single product to session cart and redirect to checkout for quick purchase."""
    try:
        product = Product.objects.get(slug=slug, is_active=True)
    except Product.DoesNotExist:
        messages.error(request, 'Product not found or unavailable.')
        return redirect(request.META.get('HTTP_REFERER', 'product'))

    # Create a fresh cart with only this product (quantity = 1)
    request.session['cart'] = {str(product.id): 1}

    messages.info(request, f'{product.name} ready for purchase. Proceed to checkout.')

    # Redirect to checkout (login_required will ensure user signs in)
    return redirect('checkout')


@login_required(login_url='login')
def remove_from_wishlist(request, product_id):
    try:
        wishlist_item = WishlistItem.objects.get(user=request.user, product_id=product_id)
        product_name = wishlist_item.product.name
        wishlist_item.delete()
        messages.success(request, f'{product_name} removed from wishlist.')
    except WishlistItem.DoesNotExist:
        messages.error(request, 'Item not found in wishlist.')
    
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))


def quick_links(request):
    return render(request, 'quick_links.html', {
        'page_title': 'Quick Links',
        'heading': 'Quick Links',
    })


def privacy_policy(request):
    return render(request, 'privacy_policy.html', {
        'page_title': 'Privacy Policy',
        'heading': 'Privacy Policy',
    })


def refund_policy(request):
    return render(request, 'refund_policy.html', {
        'page_title': 'Refund Policy',
        'heading': 'Refund Policy',
    })


def shipping_policy(request):
    return render(request, 'shipping_policy.html', {
        'page_title': 'Shipping Policy',
        'heading': 'Shipping Policy',
    })


def terms_and_conditions(request):
    return render(request, 'terms_and_conditions.html', {
        'page_title': 'Terms & Conditions',
        'heading': 'Terms & Conditions',
    })


def our_mission(request):
    return render(request, 'mission.html', {
        'page_title': 'Our Mission',
        'heading': 'Our Mission',
    })


def our_vision(request):
    return render(request, 'vision.html', {
        'page_title': 'Our Vision',
        'heading': 'Our Vision',
    })


def logout(request):
    """Logout user"""
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

def login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Password login only
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

def team_members(request):
    members = TeamMember.objects.all()

    context = {
        'members': members
    }

    return render(request, 'team_members.html', context)
