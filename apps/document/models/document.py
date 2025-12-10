from django.db import models
from django.contrib.auth import get_user_model
from datetime import  datetime

from apps.common.models import BaseModel
from apps.company.models.company import Company
from apps.document.models.tag_type import DocumentType

User = get_user_model()

class UploadedDocument(BaseModel):
    file = models.FileField(upload_to='documents/%Y/%m/%d')
    is_done = models.BooleanField(default=False, null=False)



class Document(BaseModel):
    """Модель документа"""
    name = models.CharField('Название документа', max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name='documents',
                                verbose_name='Компания')
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE,
                                      blank=True,
                                      null=True,
                                      verbose_name='Тип документа')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='created_documents',
                                   verbose_name='Кто создал')
    created_date = models.DateField('Дата создания', auto_now_add=True)
    description = models.TextField('Описание', blank=True)

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['company', 'document_type']),
            models.Index(fields=['created_date']),
        ]

    def __str__(self):
        return f"{self.name} - {self.company.name}"