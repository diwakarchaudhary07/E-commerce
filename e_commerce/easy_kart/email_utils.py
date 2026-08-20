import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def get_default_sender():
    return settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER or 'noreply@localhost'


def validate_recipient_email(email):
    if not email:
        raise ValidationError('Email address is required.')
    try:
        validate_email(email)
    except ValidationError as exc:
        raise ValidationError('Please enter a valid email address.') from exc
    return email


def send_otp_email(user, otp_code):
    """Send OTP email to user using the configured SMTP sender for all outbound messages."""
    recipient_email = validate_recipient_email(user.email)
    subject = 'Email Verification OTP - EasyKart'
    html_message = render_to_string('otp_email.html', {
        'full_name': user.full_name,
        'otp_code': otp_code,
    })
    plain_message = strip_tags(html_message)
    from_email = get_default_sender()
    to_email = [recipient_email]

    msg = EmailMultiAlternatives(subject, plain_message, from_email, to_email)
    msg.attach_alternative(html_message, "text/html")

    logger = logging.getLogger(__name__)
    try:
        sent_count = msg.send(fail_silently=False)
        if sent_count != 1:
            raise ValueError('The SMTP provider did not accept the OTP message.')
        return True
    except Exception as e:
        logger.exception("Failed to send OTP email to %s: %s", recipient_email, e)
        raise ValueError('Unable to send the OTP email. Please verify the email address or SMTP configuration.') from e


def send_welcome_email(user):
    """Send welcome email to user after verification"""
    subject = 'Welcome to EasyKart!'
    html_message = render_to_string('welcome_email.html', {
        'full_name': user.full_name,
    })
    plain_message = strip_tags(html_message)
    from_email = get_default_sender()

    send_mail(
        subject,
        plain_message,
        from_email,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_password_reset_email(user, reset_link):
    """Send password reset email"""
    subject = 'Reset Your EasyKart Password'
    html_message = render_to_string('password_reset_email.html', {
        'full_name': user.full_name,
        'reset_link': reset_link,
    })
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        get_default_sender(),
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_order_confirmation_email(user, order_details):
    """Send order confirmation email"""
    subject = f"Order Confirmation - Order #{order_details.get('order_id', 'N/A')}"
    html_message = render_to_string('order_confirmation_email.html', {
        'full_name': user.full_name,
        'order_details': order_details,
    })
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        get_default_sender(),
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_notification_email(recipient_email, subject, template_name, context):
    """Send generic notification email"""
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        get_default_sender(),
        [recipient_email],
        html_message=html_message,
        fail_silently=False,
    )
