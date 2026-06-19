from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
	GENDER_CHOICES = (
		("Male", "Male"),
		("Female", "Female"),
		("Other", "Other"),
	)

	full_name = models.CharField(max_length=255)
	email = models.EmailField(unique=True)
	is_email_verified = models.BooleanField(default=False)
	mobile_no = models.CharField(max_length=15)
	dob = models.DateField(null=True, blank=True)
	address = models.TextField()
	alternate_mobile_no = models.CharField(max_length=15, null=True, blank=True)
	profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
	gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)

	def __str__(self):
		return self.email


class OTP(models.Model):
	user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='otp')
	code = models.CharField(max_length=6, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	expires_at = models.DateTimeField()
	is_verified = models.BooleanField(default=False)

	def __str__(self):
		return f"{self.user.email} - OTP"

	@staticmethod
	def generate_otp(user):
		"""Generate and save OTP for user"""
		import random
		otp_code = str(random.randint(100000, 999999))
		expires_at = timezone.now() + timedelta(minutes=10)

		OTP.objects.filter(user=user).delete()

		otp = OTP.objects.create(
			user=user,
			code=otp_code,
			expires_at=expires_at,
		)
		return otp

	def is_expired(self):
		"""Check if OTP has expired"""
		return timezone.now() > self.expires_at

	def verify(self, code):
		"""Verify OTP code"""
		if self.is_expired():
			return False
		if self.code == code:
			self.is_verified = True
			self.save()
			return True
		return False


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


class Category(models.Model):
	name = models.CharField(max_length=200, unique=True)
	slug = models.SlugField(max_length=200, unique=True)
	description = models.TextField(blank=True, null=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name_plural = "Categories"
		ordering = ['name']

	def __str__(self):
		return self.name