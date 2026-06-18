from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('product/', product_page, name='product'),
    path('category/', category_page, name='category'),
    path('gallery/', gallery_page, name='gallery'),
    path('about-us/', about_us, name='about_us'),
    path('wishlist/', wishlist_page, name='wishlist'),
    path('cart/', cart_page, name='cart'),
    path('profile/', profile_page, name='my_profile'),
    path('orders/', orders_page, name='my_orders'),
    path('register/', register, name='register'),
    path('verify-otp/', verify_otp, name='verify_otp'),
    path('resend-otp/', resend_otp, name='resend_otp'),
    path('send-login-otp/', send_login_otp, name='send_login_otp'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('test-email/', send_test_email, name='send_test_email'),
]
