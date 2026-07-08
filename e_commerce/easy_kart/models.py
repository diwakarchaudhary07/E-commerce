import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """Custom user manager where email is the unique identifiers for authentication."""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None  # Remove username field, use email instead
    
    GENDER_CHOICES = (
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    )

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    email_otp_code = models.CharField(max_length=6, blank=True, null=True)
    email_otp_expires_at = models.DateTimeField(null=True, blank=True)
    mobile_no = models.CharField(max_length=15)
    dob = models.DateField(null=True, blank=True)
    address = models.TextField()
    alternate_mobile_no = models.CharField(max_length=15, null=True, blank=True)
    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def generate_email_otp(self):
        import random
        self.email_otp_code = f"{random.randint(100000, 999999):06d}"
        self.email_otp_expires_at = timezone.now() + timedelta(minutes=10)
        self.save(update_fields=['email_otp_code', 'email_otp_expires_at'])
        return self.email_otp_code

    def clear_email_otp(self):
        self.email_otp_code = None
        self.email_otp_expires_at = None
        self.save(update_fields=['email_otp_code', 'email_otp_expires_at'])

    def is_otp_expired(self):
        if not self.email_otp_expires_at:
            return True
        return timezone.now() > self.email_otp_expires_at

    def verify_email_otp(self, code):
        if self.is_otp_expired() or not self.email_otp_code:
            return False
        if self.email_otp_code == code:
            self.clear_email_otp()
            return True
        return False

    def __str__(self):
        return self.email


class Profile(models.Model):
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
    gender = models.CharField(max_length=10, choices=CustomUser.GENDER_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  
        return self.full_name or str(self.user.email)


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
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text='Unique stock keeping unit')
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    description = models.TextField(blank=True)
    stock = models.PositiveIntegerField(default=0, help_text='Available stock quantity')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.PositiveIntegerField(default=0, help_text='Discount percentage')
    is_buy_now_available = models.BooleanField(default=True, help_text='If enabled, shows Buy Now button to purchase immediately')
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

        if not self.sku:
            from django.utils.text import slugify
            base_slug = self.slug or slugify(self.name) or 'product'
            self.sku = f"SKU-{base_slug.replace('-', '').upper()[:20]}-{uuid.uuid4().hex[:6].upper()}"

        super().save(*args, **kwargs)


class Inventory(Product):
    class Meta:
        proxy = True
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory'
        ordering = ['-created_at']

    @classmethod
    def search(cls, query=''):
        queryset = cls.objects.all()
        term = (query or '').strip()
        if term:
            queryset = queryset.filter(Q(name__icontains=term) | Q(sku__icontains=term))
        return queryset.order_by('-created_at')

    def increase_stock(self, amount=1):
        self.stock = max(0, self.stock + amount)
        self.save(update_fields=['stock'])
        return self.stock

    def decrease_stock(self, amount=1):
        self.stock = max(0, self.stock - amount)
        self.save(update_fields=['stock'])
        return self.stock


class ProductFeedback(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='feedbacks')
    customer_name = models.CharField(max_length=255, blank=True, default='Guest')
    customer_email = models.EmailField(blank=True, null=True)
    message = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5, choices=[(i, f'{i} star{"s" if i != 1 else ""}') for i in range(1, 6)])
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product Feedback'
        verbose_name_plural = 'Product Feedback'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.rating}★"

    @property
    def customer_avatar_url(self):
        if not self.customer_email:
            return None

        User = get_user_model()
        try:
            user = User.objects.select_related('profile').get(email__iexact=self.customer_email)
        except User.DoesNotExist:
            return None

        if hasattr(user, 'profile') and user.profile.profile_image:
            return user.profile.profile_image.url
        return None


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


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        return f"Cart for {self.user.email}"

    @property
    def total_items(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0

    @property
    def total_price(self):
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.total_price
        return total


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ('cart', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def unit_price(self):
        return self.product.get_discounted_price()

    @property
    def total_price(self):
        return self.unit_price * self.quantity


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
    razorpay_order_id = models.CharField(max_length=255, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    phone_no = models.CharField(max_length=15, blank=True)
    alternate_phone_no = models.CharField(max_length=15, blank=True)
    home_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
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

class TeamMember(models.Model):
    employee_image = models.ImageField(upload_to='team_members/')
    employee_name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.employee_name


class RelatedProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='related_products_from')
    related_to = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='related_products_to')
    order = models.PositiveIntegerField(default=0, help_text='Display order for related products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Related Product'
        verbose_name_plural = 'Related Products'
        unique_together = ('product', 'related_to')
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.product.name} -> {self.related_to.name}"