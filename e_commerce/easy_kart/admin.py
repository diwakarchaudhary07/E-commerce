from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe

from .models import CustomUser, Category, Announcement, Product, Gallery, AboutUs, Contact, WishlistItem, Cart, CartItem, Order, OrderItem, TeamMember, ProductFeedback


class CustomUserAdmin(UserAdmin):
    # Fix 1: Order by email since username is completely gone
    ordering = ('email',)

    # Fix 2: Completely redefine fieldsets to remove 'username' and use 'email' as the primary identifier
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Custom Profile Details', {'fields': ('full_name', 'mobile_no', 'alternate_mobile_no', 'dob', 'address', 'profile_image', 'gender')}),
        ('Email Verification', {'fields': ('is_email_verified', 'email_otp_code', 'email_otp_expires_at')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fix 3: Completely redefine add_fieldsets from scratch so default 'username' isn't inherited
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'full_name', 'mobile_no', 'is_email_verified'),
        }),
    )

    # Fix 4: Remove 'username' from list displays and search fields
    list_display = ('email', 'full_name', 'mobile_no', 'is_staff', 'email_verification_status')
    list_filter = ('is_email_verified', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('email', 'full_name', 'mobile_no')

    def email_verification_status(self, obj):
        """Display email verification status with color"""
        if obj.is_email_verified:
            return mark_safe(
                '<span style="color: green; font-weight: bold;">✓ Verified</span>'
            )
        else:
            return mark_safe(
                '<span style="color: red; font-weight: bold;">✗ Not Verified</span>'
            )
    email_verification_status.short_description = 'Email Status'


admin.site.register(CustomUser, CustomUserAdmin)


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'price', 'discount', 'is_buy_now_available', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'is_buy_now_available', 'discount', 'created_at')
    search_fields = ('name', 'sku', 'description', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'sku', 'category', 'image', 'description', 'stock', 'price', 'discount', 'is_buy_now_available', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(Product, ProductAdmin)


class ProductFeedbackAdmin(admin.ModelAdmin):
    list_display = ('product', 'customer_name', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('product__name', 'customer_name', 'customer_email', 'message')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Feedback', {'fields': ('product', 'customer_name', 'customer_email', 'message', 'rating', 'is_approved')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


admin.site.register(ProductFeedback, ProductFeedbackAdmin)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(Category, CategoryAdmin)

admin.site.register(Announcement)


class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        ('Gallery Information', {
            'fields': ('title', 'slug', 'image', 'description', 'order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(Gallery, GalleryAdmin)


class AboutUsAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'content')
    fieldsets = (
        ('About Us Information', {
            'fields': ('title', 'content', 'image')
        }),
        ('Company Information', {
            'fields': ('mission', 'vision')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(AboutUs, AboutUsAdmin)


class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone', 'subject')
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(Contact, ContactAdmin)


class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__email', 'product__name')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Wishlist Item', {
            'fields': ('user', 'product')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


admin.site.register(WishlistItem, WishlistItemAdmin)


class CartItemInline(admin.TabularInline):
    model = CartItem
    readonly_fields = ('product', 'quantity', 'created_at', 'updated_at')
    extra = 0


class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items', 'total_price', 'updated_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CartItemInline]


admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'quantity', 'unit_price', 'total_price')
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'user__email')
    readonly_fields = ('order_number', 'created_at', 'updated_at', 'total_amount')
    inlines = [OrderItemInline]


admin.site.register(Order, OrderAdmin)


class TeamMemberAdmin(admin.ModelAdmin):
    list_display = (
        'employee_name',
        'role',
    )
    search_fields = (
        'employee_name',
        'role',
    )


admin.site.register(TeamMember, TeamMemberAdmin)