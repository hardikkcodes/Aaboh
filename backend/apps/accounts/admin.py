from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import SavedLocation, User, UserPreference


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Aaboh", {"fields": ("display_name", "role")}),)
    list_display = ("username", "email", "display_name", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "display_name")


@admin.register(SavedLocation)
class SavedLocationAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "latitude", "longitude", "created_at")
    search_fields = ("label", "user__email")
    readonly_fields = ("id", "created_at")


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "default_area", "temperature_unit", "updated_at")
