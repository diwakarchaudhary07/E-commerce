from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path, reverse
from django.utils.safestring import mark_safe

from .models import CustomUser, Category, Announcement, Product, Gallery, AboutUs, Contact, WishlistItem, Cart, CartItem, Order, OrderItem, TeamMember, ProductFeedback, ProductHelpRequest, Inventory, RelatedProduct


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


class InventoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'stock', 'preview_image', 'is_active', 'stock_actions')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('name', 'sku', 'description')
    readonly_fields = ('created_at', 'updated_at')

    def preview_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="width:40px;height:40px;object-fit:cover;border-radius:4px;" />')
        return '-'

    preview_image.short_description = 'Image'

    def stock_actions(self, obj):
        increase_url = reverse('admin:easy_kart_inventory_increase', args=[obj.pk])
        decrease_url = reverse('admin:easy_kart_inventory_decrease', args=[obj.pk])
        preview_url = reverse('admin:easy_kart_inventory_change', args=[obj.pk])
        return mark_safe(
            f'<a class="button" href="{decrease_url}" title="Decrease stock">-</a>'
            f'&nbsp;'
            f'<a class="button" href="{increase_url}" title="Increase stock">+</a>'
            f'&nbsp;'
            f'<a class="button" href="{preview_url}" title="Edit product">Preview</a>'
        )

    stock_actions.short_description = 'Actions'
    stock_actions.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/increase-stock/', self.admin_site.admin_view(self.increase_stock), name='easy_kart_inventory_increase'),
            path('<path:object_id>/decrease-stock/', self.admin_site.admin_view(self.decrease_stock), name='easy_kart_inventory_decrease'),
        ]
        return custom_urls + urls

    def increase_stock(self, request, object_id, *args, **kwargs):
        obj = self.get_object(request, object_id)
        if obj is not None:
            obj.increase_stock()
            self.message_user(request, f'Stock increased for {obj.name}.')
        return self.response_change(request, obj)

    def decrease_stock(self, request, object_id, *args, **kwargs):
        obj = self.get_object(request, object_id)
        if obj is not None:
            obj.decrease_stock()
            self.message_user(request, f'Stock decreased for {obj.name}.')
        return self.response_change(request, obj)


admin.site.register(Inventory, InventoryAdmin)


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


class ProductHelpRequestAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'created_at')
    list_filter = ('created_at', 'product')
    search_fields = ('product__name', 'user__email', 'query')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Help Request Details', {'fields': ('product', 'user', 'query')}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )


admin.site.register(ProductHelpRequest, ProductHelpRequestAdmin)


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


class RelatedProductAdmin(admin.ModelAdmin):
    list_display = ('product', 'related_to', 'order', 'created_at')
    list_filter = ('created_at', 'product__category')
    search_fields = ('product__name', 'related_to__name')
    ordering = ('product', 'order')
    fieldsets = (
        ('Related Product Information', {
            'fields': ('product', 'related_to', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(RelatedProduct, RelatedProductAdmin)