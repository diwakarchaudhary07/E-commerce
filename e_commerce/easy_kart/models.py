from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
	GENDER_CHOICES = (
		("Male", "Male"),
		("Female", "Female"),
		("Other", "Other"),
	)

	full_name = models.CharField(max_length=255)
	email = models.EmailField(unique=True)
	mobile_no = models.CharField(max_length=15)
	dob = models.DateField(null=True, blank=True)
	address = models.TextField()
	alternate_mobile_no = models.CharField(max_length=15, null=True, blank=True)
	profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
	gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)

	def __str__(self):
		return self.email


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