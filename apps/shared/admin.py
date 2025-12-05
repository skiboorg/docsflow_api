from django.contrib import admin
from .models import *


class PagePermissionInline(admin.TabularInline):
    model = PagePermission
    extra = 0

class SubMenuItemInline(admin.TabularInline):
    model = SubMenuItem
    extra = 0

class MenuItemAdmin(admin.ModelAdmin):
    model = MenuItem
    inlines = [SubMenuItemInline]


class PageAdmin(admin.ModelAdmin):
    model = Page
    inlines = [PagePermissionInline]

admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(Page, PageAdmin)
