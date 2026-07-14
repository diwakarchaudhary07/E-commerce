from django.utils import timezone
from django.db import models

from .models import Announcement, Cart


def active_announcements(request):
    """Provide active announcements to templates."""
    now = timezone.now()
    announcements = Announcement.objects.filter(is_active=True).filter(
        models.Q(start_at__lte=now) | models.Q(start_at__isnull=True)
    ).filter(models.Q(end_at__gte=now) | models.Q(end_at__isnull=True))
    return {"announcements": announcements}


def cart_item_count(request):
    """Provide the current cart item count for the navbar badge."""
    count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            count = cart.total_items
    else:
        session_cart = request.session.get('cart', {})
        if isinstance(session_cart, dict):
            try:
                count = sum(int(quantity) for quantity in session_cart.values())
            except (TypeError, ValueError):
                count = 0

    return {"cart_item_count": count}
