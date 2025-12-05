import uuid
from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True,null=True)
    updated_at = models.DateTimeField(auto_now=True,null=True)
    
    class Meta:
        abstract = True

class UUIDModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    class Meta:
        abstract = True

class BaseModel(TimeStampedModel, UUIDModel):
    class Meta:
        abstract = True


class TestModel(BaseModel):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Тестовая модель'
        verbose_name_plural = 'Тестовые модели'

    def __str__(self):
        return self.name