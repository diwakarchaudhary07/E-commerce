from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
	class Gender(models.TextChoices):
		MALE = "M", _("Male")
		FEMALE = "F", _("Female")
		OTHER = "O", _("Other")

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
	)
	full_name = models.CharField(max_length=255, blank=True)
	email = models.EmailField(blank=True)
	mobile_no = models.CharField(max_length=20, blank=True)
	alternate_mobile_no = models.CharField(max_length=20, blank=True)
	dob = models.DateField(null=True, blank=True)
	address = models.TextField(blank=True)
	profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
	gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self) -> str:  # pragma: no cover - simple representation
		return self.full_name or getattr(self.user, "username", str(self.user))


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
	"""Create or update the Profile whenever the auth user is saved."""
	if created:
		Profile.objects.create(user=instance, email=getattr(instance, "email", ""))
	else:
		try:
			instance.profile.save()
		except Profile.DoesNotExist:
			Profile.objects.create(user=instance, email=getattr(instance, "email", ""))

