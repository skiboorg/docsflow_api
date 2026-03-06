from django.db import models

from apps.common.models import BaseModel



class Founder(BaseModel):
    fio_company = models.CharField('ФИО\Название компании', max_length=255, null=True, blank=False)
    inn = models.CharField('ИНН', max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = 'Учредитель компании'
        verbose_name_plural = 'Учредители компаний'

    def __str__(self):
        return f"{self.fio_company}"


class CompanyFounder(BaseModel):
    company = models.ForeignKey('Company', on_delete=models.CASCADE,related_name='founders')
    founder = models.ForeignKey('Founder', on_delete=models.CASCADE)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True, blank=False, null=False)

    class Meta:
        verbose_name = 'Учредитель конкретной компании'
        verbose_name_plural = 'Учредители конкретной компаний'

    def __str__(self):
        return f"Учредители {self.company} {self.founder}"