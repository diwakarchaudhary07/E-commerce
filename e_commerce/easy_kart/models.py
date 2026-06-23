import uuid
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


class Registration(models.Model):
	full_name = models.CharField(max_length=255)
	email = models.EmailField(unique=True)
	password = models.CharField(max_length=128)
	is_active = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Registration"
		verbose_name_plural = "Registrations"
		ordering = ["-created_at"]

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
	image = models.ImageField(upload_to="categories/", blank=True, null=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name_plural = "Categories"
		ordering = ['name']

	def __str__(self):
		return self.name


class Product(models.Model):
	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255, unique=True)
	category = models.ForeignKey(
		Category,
		on_delete=models.CASCADE,
		related_name='products',
		null=True,
		blank=True,
	)
	image = models.ImageField(upload_to='products/', null=True, blank=True)
	color_code = models.CharField(max_length=7, default='#000000', help_text='Hex color code, e.g. #1db947')
	description = models.TextField(blank=True)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	discount = models.PositiveIntegerField(default=0, help_text='Discount percentage')
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'Product'
		verbose_name_plural = 'Products'
		ordering = ['-created_at']

	def __str__(self):
		return self.name

	def get_discounted_price(self):
		if self.discount and self.discount > 0:
			return self.price * (100 - self.discount) / 100
		return self.price

	def save(self, *args, **kwargs):
		if not self.slug:
			from django.utils.text import slugify
			self.slug = slugify(self.name)
		super().save(*args, **kwargs)


class Gallery(models.Model):
	title = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255, unique=True)
	image = models.ImageField(upload_to='gallery/')
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	order = models.PositiveIntegerField(default=0, help_text='Display order in gallery')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'Gallery'
		verbose_name_plural = 'Gallery Items'
		ordering = ['order', '-created_at']

	def __str__(self):
		return self.title

	def save(self, *args, **kwargs):
		if not self.slug:
			from django.utils.text import slugify
			self.slug = slugify(self.title)
		super().save(*args, **kwargs)


class Announcement(models.Model):
	"""Site-wide announcement messages to show in the top bar."""
	title = models.CharField(max_length=255)
	message = models.TextField()
	is_active = models.BooleanField(default=True)
	start_at = models.DateTimeField(null=True, blank=True)
	end_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.title


class AboutUs(models.Model):
	title = models.CharField(max_length=255, default='About Us')
	content = models.TextField(help_text='Main content for the about us page')
	image = models.ImageField(upload_to='about-us/', null=True, blank=True)
	mission = models.TextField(blank=True, help_text='Company mission statement')
	vision = models.TextField(blank=True, help_text='Company vision statement')
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'About Us'
		verbose_name_plural = 'About Us'

	def __str__(self):
		return self.title


class Contact(models.Model):
	STATUS_CHOICES = (
		('new', 'New'),
		('read', 'Read'),
		('replied', 'Replied'),
		('spam', 'Spam'),
	)

	name = models.CharField(max_length=255)
	email = models.EmailField()
	phone = models.CharField(max_length=20, blank=True)
	subject = models.CharField(max_length=255)
	message = models.TextField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'Contact'
		verbose_name_plural = 'Contacts'
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.name} - {self.subject}"


class WishlistItem(models.Model):
	user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wishlist_items')
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = 'Wishlist Item'
		verbose_name_plural = 'Wishlist Items'
		unique_together = ('user', 'product')
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.user.email} - {self.product.name}"

	def is_in_wishlist(self, user):
		return WishlistItem.objects.filter(user=user, product=self.product).exists()


class Order(models.Model):
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('processing', 'Processing'),
		('completed', 'Completed'),
		('cancelled', 'Cancelled'),
	]

	user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
	order_number = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
	total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	shipping_address = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'Order'
		verbose_name_plural = 'Orders'
		ordering = ['-created_at']

	def __str__(self):
		return f"Order {self.order_number} - {self.user.email}"

	@property
	def item_count(self):
		return self.order_items.aggregate(models.Sum('quantity'))['quantity__sum'] or 0

	def calculate_total(self):
		total = sum(item.total_price for item in self.order_items.all())
		self.total_amount = total
		self.save()
		return total


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
	product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
	quantity = models.PositiveIntegerField(default=1)
	unit_price = models.DecimalField(max_digits=10, decimal_places=2)
	total_price = models.DecimalField(max_digits=10, decimal_places=2)

	class Meta:
		verbose_name = 'Order Item'
		verbose_name_plural = 'Order Items'

	def __str__(self):
		return f"{self.product.name if self.product else 'Deleted product'} x {self.quantity}"

	def save(self, *args, **kwargs):
		self.total_price = self.unit_price * self.quantity
		super().save(*args, **kwargs)