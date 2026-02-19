from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_active", "created_at")
    list_filter = ("is_active", "is_staff", "created_at")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-created_at",)