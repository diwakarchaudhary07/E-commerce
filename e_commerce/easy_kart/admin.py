from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ("__str__", "email", "mobile_no", "gender")
	search_fields = ("full_name", "email", "mobile_no")
