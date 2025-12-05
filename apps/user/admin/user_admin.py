from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.user.models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'first_name', 'last_name', 'phone', 
        'is_verified', 'is_staff', 'is_active', 'date_joined'
    ]
    list_filter = ['is_verified', 'is_staff', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Role', {'fields': ('role',)}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Permissions', {'fields': ('is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('role','email', 'password1', 'password2', 'first_name', 'last_name', 'phone'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']
