from rest_framework import serializers
from apps.shared.models import *
from apps.user.serializers.roles_permissions import RoleSerializer,PermissionSerializer


class PagePermissionSerializer(serializers.ModelSerializer):
    role = RoleSerializer(many=False, read_only=True)
    permissions = PermissionSerializer(many=True, read_only=True)
    class Meta:
        model = PagePermission
        fields = '__all__'

class PageSerializer(serializers.ModelSerializer):
    permissions = PagePermissionSerializer(many=True, read_only=True)
    class Meta:
        model = Page
        fields = '__all__'

class SubMenuItemSerializer(serializers.ModelSerializer):
    page = PageSerializer(many=False, read_only=True, required=False)
    class Meta:
        model = SubMenuItem
        fields = '__all__'


class MenuItemSerializer(serializers.ModelSerializer):
    #menu_items = SubMenuItemSerializer(many=True, read_only=True, required=False)
    page = PageSerializer(many=False, read_only=True, required=False)

    class Meta:
        model = MenuItem
        exclude = ['role_can_view']

