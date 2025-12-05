from django.contrib import admin
from apps.user.models.roles_and_permissions import *

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        'name',
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        'name',
    )