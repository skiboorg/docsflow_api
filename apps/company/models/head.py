from django.db import models

from apps.common.models import BaseModel


class Head(BaseModel):
    fio = models.CharField('ФИО', max_length=255, null=True, blank=False)
    inn = models.CharField('ИНН', max_length=255, null=True, blank=True)
    passport = models.CharField('Номер паспорта', max_length=255, null=True, blank=True)
    registration = models.TextField('Прописка', null=True, blank=True)

    class Meta:
        verbose_name = 'Руководитель компании'
        verbose_name_plural = 'Руководители компаний'

    def __str__(self):
        return f"{self.fio}"


class CompanyHead(BaseModel):
    company = models.ForeignKey('Company', on_delete=models.CASCADE,related_name='heads')
    head = models.ForeignKey('Head', on_delete=models.CASCADE)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True, blank=False, null=False)

    class Meta:
        verbose_name = 'Руководитель конкретной компании'
        verbose_name_plural = 'Руководители конкретной компаний'

    def __str__(self):
        return f"Руководитель {self.company} {self.head}"