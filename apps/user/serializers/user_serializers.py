from rest_framework import serializers

from djoser.serializers import TokenCreateSerializer

from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer

from apps.user.models import User
from apps.user.serializers.roles_permissions import RoleSerializer
class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'uuid',
            'email',
        ]

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    role = RoleSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'role',
            'uuid',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'avatar',
            'is_verified',
            'date_joined',
            'last_login'
        ]
        read_only_fields = ['uuid', 'date_joined', 'last_login']

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = [
            'uuid', 'email', 'first_name', 'last_name', 
            'phone', 'password'
        ]

class CustomTokenCreateSerializer(TokenCreateSerializer):
    login = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)



    def validate(self, attrs):
        login = attrs.get("login")
        password = attrs.get("password")
        print(login, password)
        # ищем пользователя по email/username/телефону
        try:
            user = User.objects.get(email=login)
        except User.DoesNotExist:
            try:
                user = User.objects.get(phone=login)
            except User.DoesNotExist:
                raise serializers.ValidationError("User not found")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid password")
        print(user)

        self.user = user
        return attrs
