from django.test import TestCase, override_settings
from django.urls import reverse
from django.core import mail

from .models import CustomUser


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class OTPRegistrationTests(TestCase):
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
