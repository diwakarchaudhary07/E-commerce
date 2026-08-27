from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Test the configured email backend and send a test message.'

    def add_arguments(self, parser):
        parser.add_argument('recipient', help='Email address that should receive the test message.')

    def handle(self, *args, **options):
        recipient = options['recipient'].strip()
        try:
            validate_email(recipient)
        except ValidationError as exc:
            raise CommandError('Please provide a valid recipient email address.') from exc

        smtp_backend = 'django.core.mail.backends.smtp.EmailBackend'
        backend_name = settings.EMAIL_BACKEND.rsplit('.', 1)[-1]
        self.stdout.write(f'Email backend: {backend_name}')
        if settings.EMAIL_BACKEND != smtp_backend:
            raise CommandError(
                'SMTP is not active. Configure EMAIL_HOST_USER, '
                'EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL in .env.'
            )

        try:
            with get_connection(fail_silently=False) as connection:
                connection.open()
                send_mail(
                    'EasyKart SMTP test',
                    'SMTP is configured and EasyKart can send email.',
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient],
                    connection=connection,
                    fail_silently=False,
                )
        except Exception as exc:
            raise CommandError(f'Email delivery failed: {exc}') from exc

        self.stdout.write(self.style.SUCCESS(f'Test email sent to {recipient}.'))
