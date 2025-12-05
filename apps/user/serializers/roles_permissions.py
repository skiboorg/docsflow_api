from rest_framework import serializers
from apps.user.models.roles_and_permissions import  *

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        exclude = [
            'id',
            'name',
            'slug'
        ]

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id']