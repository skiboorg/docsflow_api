from django.db import models
from pytils.translit import slugify


class Permission(models.Model):
    name = models.CharField('Название доступа', max_length=20, blank=True, null=True)
    slug = models.CharField(max_length=20, blank=True, null=True)
    can_edit = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_view = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name= "Права роли"
        verbose_name_plural= "Права ролей"


class Role(models.Model):
    name = models.CharField(max_length=50, blank=True, null=True)
    slug = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name= "Роль"
        verbose_name_plural= "Роли"
        ordering = ['id']