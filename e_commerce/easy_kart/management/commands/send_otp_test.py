from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from easy_kart.email_utils import send_otp_email
from types import SimpleNamespace


class Command(BaseCommand):
    help = 'Send a real OTP test email using the registration email workflow.'

    def add_arguments(self, parser):
        parser.add_argument('recipient', help='Email address that should receive the OTP.')

    def handle(self, *args, **options):
        recipient = options['recipient'].strip()
        try:
            validate_email(recipient)
        except ValidationError as exc:
            raise CommandError('Please provide a valid recipient email address.') from exc

        if settings.EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend':
            raise CommandError(
                'SMTP is not active. Configure EMAIL_HOST_USER, '
                'EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL in e_commerce/.env.'
            )

        user = SimpleNamespace(email=recipient, full_name='OTP Test User')
        import secrets
        otp_code = f'{secrets.randbelow(900000) + 100000:06d}'

        try:
            send_otp_email(user, otp_code)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f'OTP test email sent to {recipient}.'))
        self.stdout.write(f'OTP code: {otp_code}')
