import uuid
from datetime import timedelta
from decimal import Decimal

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags
from .email_utils import send_otp_email, send_welcome_email

from .forms import RegisterForm, LoginForm, OTPVerificationForm, ProfileForm, TestEmailForm, ContactForm, ProductFeedbackForm
from .models import CustomUser, Category, Profile, Product, Gallery, AboutUs, Contact, WishlistItem, Order, OrderItem, TeamMember, Cart, CartItem, ProductFeedback
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie


def _get_or_create_user_cart(request):
    if not request.user.is_authenticated:
        return None

    cart, _ = Cart.objects.get_or_create(user=request.user)
    session_cart = request.session.get('cart', {})
    if session_cart:
        for product_id, quantity in session_cart.items():
            if not str(product_id).isdigit():
                continue
            try:
                product = Product.objects.get(id=int(product_id), is_active=True)
            except Product.DoesNotExist:
                continue
            item, _ = CartItem.objects.get_or_create(cart=cart, product=product)
            item.quantity += int(quantity)
            item.save()
        request.session['cart'] = {}
    return cart


def _build_cart_context(request):
    if request.user.is_authenticated:
        cart = _get_or_create_user_cart(request)
        cart_items = []
        total = Decimal('0.00')
        if cart:
            for item in cart.items.select_related('product').filter(product__is_active=True):
                price = item.product.get_discounted_price()
                item_total = price * item.quantity
                cart_items.append({
                    'product': item.product,
                    'quantity': item.quantity,
                    'price': price,
                    'item_total': item_total,
                })
                total += item_total
        return cart_items, total, cart

    cart_data = request.session.get('cart', {})
    product_ids = [int(pid) for pid in cart_data.keys() if str(pid).isdigit()]
    products = Product.objects.filter(id__in=product_ids, is_active=True)
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

    return cart_items, total, None


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


@login_required(login_url='login')
def inventory_page(request):
    query = (request.GET.get('q') or '').strip()
    products = Product.objects.all().order_by('-created_at')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    return render(request, 'inventory.html', {
        'page_title': 'Inventory',
        'heading': 'Inventory Management',
        'products': products,
        'query': query,
    })


@login_required(login_url='login')
@require_POST
def update_stock(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    action = request.POST.get('action', '').strip().lower()
    query = request.POST.get('query', '').strip()

    if action == 'increase':
        product.stock += 1
    elif action == 'decrease' and product.stock > 0:
        product.stock -= 1
    product.save(update_fields=['stock'])

    redirect_url = reverse('inventory')
    if query:
        redirect_url = f"{redirect_url}?q={query}"
    return redirect(redirect_url)


def _render_product_detail(request, product):
    feedbacks = product.feedbacks.filter(is_approved=True).order_by('-created_at')
    return render(request, 'product_detail.html', {
        'page_title': product.name,
        'heading': product.name,
        'product': product,
        'feedback_form': ProductFeedbackForm(),
        'feedbacks': feedbacks,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, Q(slug=slug) | Q(sku__iexact=slug), is_active=True)
    return _render_product_detail(request, product)


def product_detail_by_sku(request, sku):
    product = get_object_or_404(Product, sku__iexact=sku, is_active=True)
    return _render_product_detail(request, product)


def submit_feedback(request, slug):
    product = get_object_or_404(Product, Q(slug=slug) | Q(sku__iexact=slug), is_active=True)

    if request.method == 'POST':
        form = ProductFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.product = product
            feedback.customer_name = request.POST.get('customer_name', '').strip() or 'Guest'
            feedback.customer_email = request.POST.get('customer_email', '').strip() or None
            feedback.save()
            messages.success(request, 'Feedback submitted successfully. It is now pending approval.')
            return redirect('product_detail', slug=product.slug)

        messages.error(request, 'Please provide a valid review and rating.')
        return render(request, 'product_detail.html', {
            'page_title': product.name,
            'heading': product.name,
            'product': product,
            'feedback_form': form,
            'feedbacks': product.feedbacks.filter(is_approved=True).order_by('-created_at'),
        })

    return redirect('product_detail', slug=product.slug)


@user_passes_test(lambda user: user.is_staff)
def feedback_dashboard(request):
    feedbacks = ProductFeedback.objects.select_related('product').all().order_by('-created_at')

    if request.method == 'POST':
        feedback_id = request.POST.get('feedback_id')
        action = request.POST.get('action', '').strip().lower()
        feedback = get_object_or_404(ProductFeedback, id=feedback_id)

        if action == 'approve':
            feedback.is_approved = True
            feedback.save(update_fields=['is_approved'])
            messages.success(request, 'Feedback approved successfully.')
        elif action == 'delete':
            feedback.delete()
            messages.success(request, 'Feedback deleted successfully.')
        else:
            messages.error(request, 'Unknown action.')
        return redirect('feedback_dashboard')

    return render(request, 'feedback_dashboard.html', {
        'page_title': 'Feedback Dashboard',
        'heading': 'Feedback Dashboard',
        'feedbacks': feedbacks,
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

    if request.user.is_authenticated:
        cart = _get_or_create_user_cart(request)
        item, _ = CartItem.objects.get_or_create(cart=cart, product=product)
        item.quantity += 1
        item.save()
    else:
        cart = request.session.get('cart', {})
        cart[str(product.id)] = cart.get(str(product.id), 0) + 1
        request.session['cart'] = cart

    messages.success(request, f'Added {product.name} to cart.')
    return redirect('cart')


def cart_page(request):
    cart_items, total, _ = _build_cart_context(request)
    return render(request, 'cart.html', {
        'page_title': 'Cart',
        'heading': 'My Cart',
        'cart_items': cart_items,
        'cart_total': total,
    })


@login_required(login_url='login')
def checkout(request):
    cart_items, total, cart = _build_cart_context(request)
    if not cart_items:
        messages.info(request, 'Your cart is empty. Add some products to place an order.')
        return redirect('product')

    order_items = []
    for item in cart_items:
        order_items.append({
            'product': item['product'],
            'quantity': item['quantity'],
            'unit_price': item['price'],
            'item_total': item['item_total'],
        })

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip() or request.user.full_name or request.user.get_full_name() or request.user.email
        phone_no = request.POST.get('phone_no', '').strip() or request.user.mobile_no or ''
        alternate_phone_no = request.POST.get('alternate_phone_no', '').strip() or request.user.alternate_mobile_no or ''
        home_address = request.POST.get('home_address', '').strip() or request.user.address or ''
        city = request.POST.get('city', '').strip() or ''
        pincode = request.POST.get('pincode', '').strip() or ''
        shipping_address = '\n'.join(filter(None, [home_address, f"City: {city}" if city else '', f"Pincode: {pincode}" if pincode else ''])) or request.user.address or ''

        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            full_name=full_name,
            phone_no=phone_no,
            alternate_phone_no=alternate_phone_no,
            home_address=home_address,
            city=city,
            pincode=pincode,
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

        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'
        if is_ajax:
            try:
                import razorpay
            except ImportError:
                return JsonResponse({'success': False, 'message': 'Razorpay package is not installed.'}, status=400)

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order_payload = {
                'amount': int(order.total_amount * Decimal('100')),
                'currency': 'INR',
                'receipt': str(order.id),
                'notes': {'email': request.user.email, 'name': full_name},
                'payment_capture': 1,
            }
            razorpay_order = client.order.create(data=order_payload)
            order.razorpay_order_id = razorpay_order['id']
            order.save(update_fields=['razorpay_order_id'])
            return JsonResponse({
                'success': True,
                'order_id': razorpay_order['id'],
                'db_order_id': order.id,
                'key': settings.RAZORPAY_KEY_ID,
                'amount': int(order.total_amount * 100),
                'currency': 'INR',
                'name': 'Easy Kart',
                'description': 'Order payment',
                'prefill': {'name': full_name, 'email': request.user.email, 'contact': phone_no},
            })

        if cart:
            cart.items.all().delete()
        else:
            request.session['cart'] = {}
        messages.success(request, f'Your order {order.order_number} has been placed successfully!')
        return redirect('my_orders')

    return render(request, 'checkout.html', {
        'page_title': 'Checkout',
        'heading': 'Checkout',
        'order_items': order_items,
        'order_total': total,
        'full_name': request.user.full_name or request.user.get_full_name() or '',
        'phone_no': request.user.mobile_no or '',
        'alternate_phone_no': request.user.alternate_mobile_no or '',
        'home_address': request.user.address or '',
    })


@login_required(login_url='login')
@require_POST
def verify_razorpay_payment(request):
    try:
        payload = json.loads(request.body)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid request body.'}, status=400)

    razorpay_order_id = payload.get('order_id')
    razorpay_payment_id = payload.get('payment_id')
    razorpay_signature = payload.get('signature')
    db_order_id = payload.get('db_order_id')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature, db_order_id]):
        return JsonResponse({'success': False, 'message': 'Missing payment details.'}, status=400)

    order = get_object_or_404(Order, id=db_order_id, user=request.user, razorpay_order_id=razorpay_order_id)

    try:
        import razorpay
    except ImportError:
        return JsonResponse({'success': False, 'message': 'Razorpay package is not installed.'}, status=400)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except Exception:
        return JsonResponse({'success': False, 'message': 'Payment verification failed.'}, status=400)

    order.razorpay_payment_id = razorpay_payment_id
    order.razorpay_signature = razorpay_signature
    order.status = 'processing'
    order.save(update_fields=['razorpay_payment_id', 'razorpay_signature', 'status'])

    cart = _get_or_create_user_cart(request)
    if cart:
        cart.items.all().delete()
    else:
        request.session['cart'] = {}

    return JsonResponse({'success': True, 'redirect_url': reverse('my_orders')})


@login_required(login_url='login')
@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = _get_or_create_user_cart(request)
    if not cart:
        messages.error(request, 'Please log in to update your cart.')
        return redirect('cart')

    item = cart.items.filter(product=product).first()
    if not item:
        messages.info(request, 'This product is not in your cart.')
        return redirect('cart')

    quantity_change = int(request.POST.get('quantity', 0))
    new_quantity = item.quantity + quantity_change

    if new_quantity <= 0:
        item.delete()
        messages.success(request, f'Removed {product.name} from your cart.')
    else:
        item.quantity = new_quantity
        item.save()
        messages.success(request, f'Updated {product.name} quantity.')

    return redirect('cart')


@login_required(login_url='login')
@require_POST
def remove_from_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = _get_or_create_user_cart(request)
    if not cart:
        messages.error(request, 'Please log in to remove items from your cart.')
        return redirect('cart')

    item = cart.items.filter(product=product).first()
    if item:
        item.delete()
        messages.success(request, f'Removed {product.name} from your cart.')
    else:
        messages.info(request, 'This product is not in your cart.')
    return redirect('cart')


@login_required(login_url='login')
@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status in ['completed', 'cancelled']:
        messages.warning(request, 'This order cannot be cancelled.')
        return redirect('my_orders')

    order.status = 'cancelled'
    order.save(update_fields=['status'])
    messages.success(request, f'Order {order.order_number} has been cancelled.')
    return redirect('my_orders')


@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('order_items__product')
    query = (request.GET.get('q') or '').strip()
    date_filter = request.GET.get('date_filter', '').strip()
    product_name = (request.GET.get('product_name') or '').strip()

    if query:
        orders = orders.filter(
            Q(full_name__icontains=query) |
            Q(order_number__icontains=query) |
            Q(shipping_address__icontains=query)
        )

    if date_filter:
        if date_filter == 'today':
            orders = orders.filter(created_at__date=timezone.now().date())
        elif date_filter == 'week':
            start_date = timezone.now().date() - timedelta(days=7)
            orders = orders.filter(created_at__date__gte=start_date)
        elif date_filter == 'month':
            start_date = timezone.now().date().replace(day=1)
            orders = orders.filter(created_at__date__gte=start_date)

    if product_name:
        orders = orders.filter(order_items__product__name__icontains=product_name).distinct()

    orders = orders.order_by('-created_at')

    return render(request, 'my_orders.html', {
        'page_title': 'My Orders',
        'heading': 'My Orders',
        'orders': orders,
        'query': query,
        'date_filter': date_filter,
        'product_name': product_name,
    })


@login_required(login_url='login')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {
        'page_title': f'Order #{order.order_number}',
        'heading': f'Order #{order.order_number}',
        'order': order,
    })


@login_required(login_url='login')
def order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_invoice.html', {
        'page_title': f'Invoice #{order.order_number}',
        'heading': f'Invoice #{order.order_number}',
        'order': order,
    })


@login_required(login_url='login')
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    content = f"Invoice for Order #{order.order_number}\nCustomer: {order.full_name or order.user.full_name}\nTotal: {order.total_amount}\nStatus: {order.status}\n"
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_number}.txt"'
    return response


@login_required(login_url='login')
@require_POST
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.delete()
    messages.success(request, 'Order deleted successfully.')
    return redirect('my_orders')


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


@ensure_csrf_cookie
def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Attempt to create user inside a transaction to avoid partial state
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.is_active = False # Keep user inactive until OTP verification
                    user.save()
            except IntegrityError:
                form.add_error('email', 'A user with this email already exists.')
                return render(request, 'register.html', {'form': form})
            except Exception as e:
                messages.error(request, f'Error creating account: {e}')
                return render(request, 'register.html', {'form': form})

            # Generate OTP and send email; if sending fails, delete the inactive user
            try:
                otp_code = user.generate_email_otp()
                send_otp_email(user, otp_code)
            except Exception:
                try:
                    user.delete()
                except Exception:
                    pass
                messages.error(request, 'Unable to send OTP email. Please try again later.')
                return render(request, 'register.html', {'form': form})

            request.session['email_for_verification'] = user.email.lower()
            messages.success(request, 'Registration successful! Enter the OTP sent to your email.')
            return redirect('verify_otp')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


@ensure_csrf_cookie
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

        if not user.email_otp_code:
            messages.error(request, 'No OTP was sent to this account. Please register again.')
            return redirect('register')

        if user.is_otp_expired():
            messages.error(request, 'OTP has expired. Please resend a new one.')
            return render(request, 'verify_otp.html', {'email': email, 'form': form})

        if user.verify_email_otp(otp_code):
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
            otp_code = user.generate_email_otp()
            send_otp_email(user, otp_code)
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


def login(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            user = CustomUser.objects.filter(email__iexact=email).first()
            if not user:
                messages.error(request, 'Invalid email or password!')
            elif not user.is_email_verified:
                messages.warning(request, 'Please verify your email before logging in.')
                request.session['email_for_verification'] = email
                return redirect('verify_otp')
            else:
                # Use email for authentication kwargs since we updated USERNAME_FIELD
                authenticated_user = authenticate(request, email=email, password=password)
                if authenticated_user is not None:
                    auth_login(request, authenticated_user)
                    if remember_me:
                        request.session.set_expiry(1209600)
                    else:
                        request.session.set_expiry(0)
                    
                    messages.success(request, f'Welcome back, {authenticated_user.full_name or authenticated_user.email}!')
                    return redirect('home')
                else:
                    messages.error(request, 'Invalid email or password!')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'login.html', {'form': form})


def logout(request):
    if request.method in ('POST', 'GET'):
        auth_logout(request)
        messages.success(request, 'You have been logged out successfully!')
    return redirect('home')

def team_members(request):
    members = TeamMember.objects.all()

    context = {
        'members': members
    }

    return render(request, 'team_members.html', context)