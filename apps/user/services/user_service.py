from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.authtoken.models import Token

User = get_user_model()

class UserService:
    @staticmethod
    def get_user_by_uuid(uuid):
        try:
            return User.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            return None
    
    @staticmethod
    def get_user_by_email(email):
        try:
            return User.objects.get(email=email)
        except ObjectDoesNotExist:
            return None
    
    @staticmethod
    def create_user(email, password, **extra_fields):
        return User.objects.create_user(
            email=email,
            password=password,
            **extra_fields
        )
    
    @staticmethod
    def update_user(user, **data):
        for field, value in data.items():
            setattr(user, field, value)
        user.save()
        return user
    
    @staticmethod
    def create_token(user):
        token, created = Token.objects.get_or_create(user=user)
        return token.key
    
    @staticmethod
    def delete_token(user):
        Token.objects.filter(user=user).delete()
