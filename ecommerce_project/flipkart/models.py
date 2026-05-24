from django.db import models
# from django.contrib.auth.models import AbstractUser


# # ------------------ Custom User Model ------------------

# class CustomUser(AbstractUser):
#     username = None

#     GENDER_CHOICES = (
#         ('Male', 'Male'),
#         ('Female', 'Female'),
#         ('Other', 'Other'),
#     )

#     full_name = models.CharField(max_length=150)
#     email = models.EmailField(unique=True)
#     mobile_no = models.CharField(max_length=15)
#     alternate_mobile_no = models.CharField(max_length=15, blank=True, null=True)
#     dob = models.DateField()
#     address = models.TextField()
#     profile_image = models.ImageField(
#         upload_to='profile_images/',
#         blank=True,
#         null=True
#     )
#     gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['full_name']

#     def __str__(self):
#         return self.full_name


# # ------------------ Category Model ------------------

# class Category(models.Model):
#     category_name = models.CharField(max_length=100, unique=True)
#     category_image = models.ImageField(upload_to='category_images/')
#     category_product_stock = models.PositiveIntegerField(default=0)

#     def __str__(self):
#         return self.category_name


# # ------------------ Product Model ------------------

# class Product(models.Model):
#     product_name = models.CharField(max_length=200)
#     product_image = models.ImageField(upload_to='product_images/')
#     product_description = models.TextField()

#     product_category = models.ForeignKey(
#         Category,
#         on_delete=models.CASCADE,
#         related_name='products'
#     )

#     product_original_price = models.DecimalField(
#         max_digits=10,
#         decimal_places=2
#     )

#     product_sale_price = models.DecimalField(
#         max_digits=10,
#         decimal_places=2
#     )

#     def __str__(self):
#         return self.product_name