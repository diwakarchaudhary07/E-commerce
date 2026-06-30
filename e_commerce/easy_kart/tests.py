import json

from django.test import TestCase, override_settings
from django.urls import reverse
from django.core import mail
from django.conf import settings

from .models import CustomUser, Product, Cart, CartItem, Order


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class OTPRegistrationTests(TestCase):
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
