import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_otp_email(user, otp_code):
    """Send OTP email to user"""
    subject = 'Email Verification OTP - ShopSphere'
    html_message = render_to_string('otp_email.html', {
        'full_name': user.full_name,
        'otp_code': otp_code,
    })
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
    to_email = [user.email]

    msg = EmailMultiAlternatives(subject, plain_message, from_email, to_email)
    msg.attach_alternative(html_message, "text/html")

    logger = logging.getLogger(__name__)
    try:
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.exception("Failed to send OTP email to %s: %s", user.email, e)
        raise


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


def send_password_reset_email(user, reset_link):
    """Send password reset email"""
    subject = 'Reset Your ShopSphere Password'
    html_message = render_to_string('password_reset_email.html', {
        'full_name': user.full_name,
        'reset_link': reset_link,
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
        settings.EMAIL_HOST_USER,
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
        settings.EMAIL_HOST_USER,
        [recipient_email],
        html_message=html_message,
        fail_silently=False,
    )
