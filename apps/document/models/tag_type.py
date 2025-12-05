from django.db import models

from apps.company.models import CompanyType


class DocumentTag(models.Model):
    name = models.CharField('Название тега документа', max_length=255)

    class Meta:
        verbose_name = 'Тег документа'
        verbose_name_plural = 'Теги документов'

    def __str__(self):
        return self.name

class DocumentType(models.Model):
    name = models.CharField('Название типа документа', max_length=255)
    aliases = models.ManyToManyField(DocumentTag,
                                     blank=True,
                                     verbose_name='Алиасы (теги)'
                                     )
    applicable_company_types = models.ManyToManyField(CompanyType,
                                                      blank=True,
                                                      verbose_name='Применимые типы компаний')

    class Meta:
        verbose_name = 'Тип документа'
        verbose_name_plural = 'Типы документов'

    def __str__(self):
        return self.name
