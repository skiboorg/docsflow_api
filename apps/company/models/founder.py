from django.db import models

from apps.common.models import BaseModel


class Founder(BaseModel):
    fio = models.CharField('ФИО', max_length=255, null=True, blank=False)

    class Meta:
        verbose_name = 'Учредитель компании'
        verbose_name_plural = 'Учредители компаний'

    def __str__(self):
        return f"{self.fio}"