from django.db import models

from apps.common.models import BaseModel


class CompanyType(BaseModel):
    name = models.CharField('Название компании', max_length=255)

    class Meta:
        verbose_name = 'Тип компании'
        verbose_name_plural = 'Типы компаний'

    def __str__(self):
        return f"{self.name}"

class Company(BaseModel):

    inn = models.CharField('ИНН', max_length=12, unique=True)
    name = models.CharField('Название компании', max_length=255)
    company_type = models.ForeignKey(CompanyType,
                                     on_delete=models.SET_NULL,
                                     null=True,
                                     blank=True,
                                     verbose_name='Тип компании')
    director_name = models.CharField('ФИО директора', max_length=255)
    founding_date = models.DateField('Дата открытия')
    authorized_capital = models.DecimalField('Уставной капитал', max_digits=15, decimal_places=2)

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'

    def __str__(self):
        return f"{self.name} (ИНН: {self.inn})"