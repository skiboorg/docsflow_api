import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.user.managers import UserManager
from apps.user.models.roles_and_permissions import Role


class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, blank=True, null=True)

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name='UUID'
    )
    email = models.EmailField(
        unique=True,
        verbose_name='Email'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Phone'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Avatar'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Verified'
    )
    
    username = None
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
