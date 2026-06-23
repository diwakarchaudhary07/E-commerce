from django.utils import timezone
from django.db import models

from .models import Announcement


def active_announcements(request):
    """Provide active announcements to templates."""
    now = timezone.now()
    announcements = Announcement.objects.filter(is_active=True).filter(
        models.Q(start_at__lte=now) | models.Q(start_at__isnull=True)
    ).filter(models.Q(end_at__gte=now) | models.Q(end_at__isnull=True))
    return {"announcements": announcements}
