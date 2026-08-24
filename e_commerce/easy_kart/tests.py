import hashlib
import hmac
import json

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.core import mail
from django.core.exceptions import FieldDoesNotExist
from django.conf import settings

from .models import CustomUser, Product, Cart, CartItem, Order, ProductFeedback, Inventory, AIHelpChatMessage
from .views import _verify_razorpay_signature


class RazorpaySignatureTests(SimpleTestCase):
    @override_settings(RAZORPAY_KEY_SECRET='test_secret')
    def test_verifies_valid_razorpay_signature(self):
        order_id = 'order_123'
        payment_id = 'pay_456'
        signature = hmac.new(
            b'test_secret',
            f'{order_id}|{payment_id}'.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

        self.assertTrue(_verify_razorpay_signature(order_id, payment_id, signature))

    @override_settings(RAZORPAY_KEY_SECRET='test_secret')
    def test_rejects_invalid_razorpay_signature(self):
        order_id = 'order_123'
        payment_id = 'pay_456'

        self.assertFalse(_verify_razorpay_signature(order_id, payment_id, 'invalid-signature'))


class ProductSkuTests(TestCase):
    def test_product_model_does_not_have_color_code_field(self):
        with self.assertRaises(FieldDoesNotExist):
            Product._meta.get_field('color_code')

    def test_product_sku_is_generated_when_missing(self):
        product = Product.objects.create(
            name='SKU Test Product',
            slug='sku-test-product',
            price='199.99',
        )

        self.assertTrue(product.sku.startswith('SKU-'))
        self.assertTrue(len(product.sku) > 10)


class InventoryTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='inventory@example.com',
            password='StrongPass123!',
            full_name='Inventory User',
            mobile_no='9876543210',
            address='Inventory Address',
        )

    def test_inventory_search_finds_product_by_sku(self):
        Product.objects.create(
            name='Inventory Widget',
            slug='inventory-widget',
            sku='PT56',
            price='12.50',
            stock=5,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('inventory'), {'q': 'PT56'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inventory Widget')
        self.assertContains(response, 'PT56')

    def test_update_stock_changes_stock_value(self):
        product = Product.objects.create(
            name='Stock Product',
            slug='stock-product',
            sku='SP100',
            price='25.00',
            stock=3,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('update_stock', args=[product.id]),
            {'action': 'increase', 'query': 'SP100'},
        )

        self.assertRedirects(response, reverse('inventory') + '?q=SP100')
        product.refresh_from_db()
        self.assertEqual(product.stock, 4)

    def test_inventory_model_can_be_searched_by_name_and_sku(self):
        Product.objects.create(
            name='Inventory Proxy Product',
            slug='inventory-proxy-product',
            sku='INV-900',
            price='18.00',
            stock=2,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('inventory'), {'q': 'Inventory Proxy'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inventory Proxy Product')

        sku_response = self.client.get(reverse('inventory'), {'q': 'INV-900'})
        self.assertContains(sku_response, 'Inventory Proxy Product')
        self.assertContains(sku_response, 'INV-900')


class PasswordResetFlowTests(TestCase):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_login_page_shows_forgot_password_link(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forgot password?')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_request_sends_email(self):
        user = CustomUser.objects.create_user(
            email='reset@example.com',
            password='StrongPass123!',
            full_name='Reset User',
            mobile_no='9876543210',
            address='Reset Address',
            is_email_verified=True,
        )

        response = self.client.post(reverse('password_reset'), {'email': user.email})

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset Your EasyKart Password', mail.outbox[0].subject)


class NeedHelpAssistantTests(TestCase):
    def test_need_help_page_renders_and_saves_chat_message(self):
        user = CustomUser.objects.create_user(
            email='assistant@example.com',
            password='StrongPass123!',
            full_name='Assistant User',
            mobile_no='9876543210',
            address='Test Address',
            is_email_verified=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('need_help'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Help Assistant')

        submit_response = self.client.post(
            reverse('need_help'),
            {'message': 'How do I track my order?'}
        )

        self.assertEqual(submit_response.status_code, 200)
        self.assertTrue(AIHelpChatMessage.objects.filter(user=user).exists())
        self.assertContains(submit_response, 'How do I track my order?')


class FeedbackSystemTests(TestCase):
    def test_feedback_submission_saves_review_for_current_product(self):
        product = Product.objects.create(
            name='Feedback Product',
            slug='feedback-product',
            sku='FB-100',
            price='99.00',
            stock=7,
        )
        
        user = CustomUser.objects.create_user(
            email='feedback@example.com',
            password='StrongPass123!',
            full_name='Feedback User',
            mobile_no='9876543210',
            address='Test Address',
            is_email_verified=True,
        )
        
        self.client.force_login(user)

        response = self.client.post(
            reverse('submit_feedback', args=[product.slug]),
            {'message': 'Excellent quality and fast delivery.', 'rating': '5'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        feedback = ProductFeedback.objects.get(product=product)
        self.assertEqual(feedback.message, 'Excellent quality and fast delivery.')
        self.assertEqual(feedback.rating, 5)
        self.assertContains(response, 'Feedback submitted successfully')

    def test_staff_dashboard_can_approve_or_delete_feedback(self):
        product = Product.objects.create(
            name='Desk Product',
            slug='desk-product',
            sku='DSK-1',
            price='49.00',
            stock=3,
        )
        feedback = ProductFeedback.objects.create(
            product=product,
            message='Nice product.',
            rating=4,
        )
        staff_user = CustomUser.objects.create_user(
            email='staff@example.com',
            password='StrongPass123!',
            full_name='Staff User',
            mobile_no='9876543210',
            address='Staff Address',
            is_staff=True,
            is_superuser=True,
        )

        self.client.force_login(staff_user)
        response = self.client.get(reverse('feedback_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nice product.')

        delete_response = self.client.post(
            reverse('feedback_dashboard'),
            {'feedback_id': feedback.id, 'action': 'delete'},
        )

        self.assertRedirects(delete_response, reverse('feedback_dashboard'))
        self.assertFalse(ProductFeedback.objects.filter(id=feedback.id).exists())


class OrdersModuleTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='orders@example.com',
            password='StrongPass123!',
            full_name='Orders User',
            mobile_no='9876543210',
            address='Orders Address',
        )
        self.product = Product.objects.create(
            name='Order Product',
            slug='order-product',
            sku='ORD-100',
            price='45.00',
            stock=10,
        )
        self.order = Order.objects.create(
            user=self.user,
            full_name=self.user.full_name,
            phone_no=self.user.mobile_no,
            shipping_address='Test address',
            total_amount='45.00',
            status='pending',
        )
        self.order.order_items.create(
            product=self.product,
            quantity=1,
            unit_price='45.00',
            total_price='45.00',
        )

    def test_my_orders_page_lists_orders_and_filters_by_product_name(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('my_orders'), {'product_name': 'Order Product'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Order Product')
        self.assertContains(response, '#{}'.format(self.order.order_number))

    def test_invoice_preview_and_download_work(self):
        self.client.force_login(self.user)
        preview_response = self.client.get(reverse('order_invoice', args=[self.order.id]))
        download_response = self.client.get(reverse('download_invoice', args=[self.order.id]))

        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, 'Invoice')
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response['Content-Type'], 'text/plain; charset=utf-8')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class OTPRegistrationTests(TestCase):
    def test_register_reuses_incomplete_registration(self):
        user = CustomUser.objects.create_user(
            email='retry@example.com',
            password='OldPass123!',
            full_name='Old Name',
            mobile_no='',
            address='',
            is_active=False,
            is_email_verified=False,
        )

        response = self.client.post(
            reverse('register'),
            data={
                'full_name': 'New Name',
                'email': user.email,
                'password': 'NewPass123!',
                'confirm_password': 'NewPass123!',
            },
        )

        self.assertRedirects(response, reverse('verify_otp'))
        user.refresh_from_db()
        self.assertEqual(user.full_name, 'New Name')
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertIsNotNone(user.email_otp_code)

    def test_register_creates_frontend_only_customer(self):
        response = self.client.post(
            reverse('register'),
            data={
                'full_name': 'Frontend Customer',
                'email': 'frontend-customer@example.com',
                'password': 'StrongPass123!',
                'confirm_password': 'StrongPass123!',
            },
        )

        self.assertRedirects(response, reverse('verify_otp'))
        user = CustomUser.objects.get(email='frontend-customer@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)

        self.client.force_login(user)
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_checkout_creates_order_with_customer_details(self):
        user = CustomUser.objects.create_user(
            email='checkout@example.com',
            password='StrongPass123!',
            full_name='Checkout User',
            mobile_no='9876543210',
            address='Old address',
        )
        product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price='100.00',
            discount=0,
        )
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=2)

        self.client.force_login(user)
        response = self.client.post(
            reverse('checkout'),
            data={
                'full_name': 'John Doe',
                'phone_no': '9876543210',
                'alternate_phone_no': '9988776655',
                'home_address': '123 Main Street',
                'city': 'Mumbai',
                'pincode': '400001',
            },
        )

        self.assertRedirects(response, reverse('my_orders'))
        order = Order.objects.get(user=user)
        self.assertEqual(order.full_name, 'John Doe')
        self.assertEqual(order.phone_no, '9876543210')
        self.assertEqual(order.alternate_phone_no, '9988776655')
        self.assertEqual(order.home_address, '123 Main Street')
        self.assertEqual(order.city, 'Mumbai')
        self.assertEqual(order.pincode, '400001')

    def test_checkout_returns_razorpay_payment_payload(self):
        user = CustomUser.objects.create_user(
            email='payment@example.com',
            password='StrongPass123!',
            full_name='Payment User',
            mobile_no='9876543210',
            address='Old address',
        )
        product = Product.objects.create(
            name='Payment Product',
            slug='payment-product',
            price='100.00',
            discount=0,
        )
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        self.client.force_login(user)
        response = self.client.post(
            reverse('checkout'),
            data={
                'full_name': 'Jane Doe',
                'phone_no': '9876543210',
                'home_address': '10 Downing Street',
                'city': 'Mumbai',
                'pincode': '400001',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload['success'])
        self.assertEqual(payload['key'], settings.RAZORPAY_KEY_ID)
        order = Order.objects.get(user=user)
        self.assertEqual(order.razorpay_order_id, payload['order_id'])

    def test_register_creates_inactive_user_and_sends_otp(self):
        response = self.client.post(
            reverse('register'),
            data={
                'full_name': 'Test User',
                'email': 'test@example.com',
                'password': 'StrongPass123!',
                'confirm_password': 'StrongPass123!',
            }
        )

        self.assertRedirects(response, reverse('verify_otp'))

        user = CustomUser.objects.get(email__iexact='test@example.com')
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertIsNotNone(user.email_otp_code)
        self.assertIsNotNone(user.email_otp_expires_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email_otp_code, mail.outbox[0].body)

    def test_register_accepts_valid_email_from_any_domain(self):
        response = self.client.post(
            reverse('register'),
            data={
                'full_name': 'Domain User',
                'email': 'domain.user@shop.example.co.uk',
                'password': 'StrongPass123!',
                'confirm_password': 'StrongPass123!',
            }
        )

        self.assertRedirects(response, reverse('verify_otp'))
        self.assertTrue(CustomUser.objects.filter(email='domain.user@shop.example.co.uk').exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_verify_otp_with_valid_code_verifies_user(self):
        user = CustomUser.objects.create_user(
            username='testuser1',
            email='verify@example.com',
            password='StrongPass123!',
            full_name='Verify User',
            is_active=False,
            is_email_verified=False,
        )
        user.generate_email_otp()

        response = self.client.post(
            reverse('verify_otp'),
            data={'email': user.email, 'otp_code': user.email_otp_code},
        )

        self.assertRedirects(response, reverse('login'))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)
        self.assertIsNone(user.email_otp_code)
        self.assertIsNone(user.email_otp_expires_at)

    def test_verify_otp_with_invalid_code_shows_error(self):
        user = CustomUser.objects.create_user(
            username='testuser2',
            email='invalid@example.com',
            password='StrongPass123!',
            full_name='Invalid User',
            is_active=False,
            is_email_verified=False,
        )
        user.generate_email_otp()

        response = self.client.post(
            reverse('verify_otp'),
            data={'email': user.email, 'otp_code': '000000'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid OTP')
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)

    def test_verify_otp_uses_session_email_instead_of_posted_email(self):
        response = self.client.post(
            reverse('register'),
            data={
                'full_name': 'Session User',
                'email': 'session@example.com',
                'password': 'StrongPass123!',
                'confirm_password': 'StrongPass123!',
            },
        )
        self.assertRedirects(response, reverse('verify_otp'))
        user = CustomUser.objects.get(email='session@example.com')
        user.generate_email_otp()

        response = self.client.post(
            reverse('verify_otp'),
            data={'email': 'other@example.com', 'otp_code': user.email_otp_code},
        )

        self.assertRedirects(response, reverse('verify_otp'))
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)

    def test_resend_otp_updates_expiry_and_sends_new_email(self):
        user = CustomUser.objects.create_user(
            username='testuser3',
            email='resend@example.com',
            password='StrongPass123!',
            full_name='Resend User',
            is_active=False,
            is_email_verified=False,
        )
        user.generate_email_otp()
        old_expiry = user.email_otp_expires_at

        response = self.client.post(
            reverse('resend_otp'),
            data={'email': user.email},
        )

        self.assertRedirects(response, reverse('verify_otp'))
        user.refresh_from_db()
        self.assertIsNotNone(user.email_otp_code)
        self.assertIsNotNone(user.email_otp_expires_at)
        self.assertGreaterEqual(user.email_otp_expires_at, old_expiry)
        self.assertNotEqual(user.email_otp_code, None)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email_otp_code, mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    def test_resend_otp_keeps_previous_code_when_delivery_fails(self):
        user = CustomUser.objects.create_user(
            username='failedresend',
            email='failed-resend@example.com',
            password='StrongPass123!',
            full_name='Failed Resend User',
            is_active=False,
            is_email_verified=False,
        )
        old_code = user.generate_email_otp()
        old_expiry = user.email_otp_expires_at

        response = self.client.post(reverse('resend_otp'), {'email': user.email}, follow=True)

        user.refresh_from_db()
        self.assertEqual(user.email_otp_code, old_code)
        self.assertEqual(user.email_otp_expires_at, old_expiry)
        self.assertContains(response, 'Unable to send the OTP email')

    def test_full_registration_otp_verification_and_login_flow(self):
        response = self.client.post(
            reverse('register'),
            data={
                'full_name': 'Flow User',
                'email': 'flow@example.com',
                'password': 'StrongPass123!',
                'confirm_password': 'StrongPass123!',
            }
        )

        self.assertRedirects(response, reverse('verify_otp'))
        user = CustomUser.objects.get(email__iexact='flow@example.com')
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertIsNotNone(user.email_otp_code)

        # Verify the OTP returned by the registration process
        response = self.client.post(
            reverse('verify_otp'),
            data={'email': user.email, 'otp_code': user.email_otp_code},
        )

        self.assertRedirects(response, reverse('login'))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)

        # Login after verification
        response = self.client.post(
            reverse('login'),
            data={'email': user.email, 'password': 'StrongPass123!', 'remember_me': False},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].email, user.email)
