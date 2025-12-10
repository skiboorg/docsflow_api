def document_upload_path(instance, filename):
    """Путь для загрузки файлов документов"""
    now = datetime.now()
    company_inn = instance.document.company.inn
    version = instance.version
    return f'documents/{company_inn}/{now.year}/{now.month}/v{version}/{filename}'
from django.db import models
from django.contrib.auth import get_user_model
from datetime import  datetime

from apps.common.models import BaseModel


User = get_user_model()

class DocumentVersion(BaseModel):
    """Модель версии документа"""
    document = models.ForeignKey('Document', on_delete=models.CASCADE,
                                 related_name='versions',
                                 verbose_name='Документ')
    version = models.PositiveIntegerField('Версия', default=1)
    file = models.FileField('Файл', upload_to=document_upload_path, null=True, blank=True)

    # Статусы
    on_approval = models.BooleanField('На утверждении', default=True)
    approved = models.BooleanField('Утвержден', default=False)
    rejected = models.BooleanField('Отклонен', default=False)
    missing = models.BooleanField('Отсутствует', default=False)

    # Даты
    upload_date = models.DateField('Дата загрузки', auto_now_add=True)
    valid_from = models.DateField('Действует с', null=True, blank=True,
                                  help_text='Дата начала действия версии')
    valid_until = models.DateField('Действует до', null=True, blank=True,
                                   help_text='Дата окончания действия версии')

    # Ответственные лица
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name='uploaded_document_versions',
                                    verbose_name='Кто загрузил')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='reviewed_document_versions',
                                    verbose_name='Кто проверил')
    review_date = models.DateField('Дата проверки', null=True, blank=True)

    # Комментарии
    comment = models.TextField('Комментарий', blank=True)
    rejection_reason = models.TextField('Причина отказа', blank=True,
                                        help_text='Заполняется при отклонении версии')

    # Активность
    is_active = models.BooleanField('Активна', default=True)
    is_current = models.BooleanField('Текущая версия', default=False)

    class Meta:
        verbose_name = 'Версия документа'
        verbose_name_plural = 'Версии документов'
        ordering = ['document', '-version']
        unique_together = ['document', 'version']
        indexes = [
            models.Index(fields=['document', 'is_current', 'is_active']),
            models.Index(fields=['document', 'approved', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.document.name} - v{self.version}"

    @property
    def status_display(self):
        """Отображаемое имя статуса"""
        if self.approved:
            return 'Утвержден'
        elif self.rejected:
            return 'Отклонен'
        elif self.missing:
            return 'Отсутствует'
        elif self.on_approval:
            return 'На утверждении'
        return 'Неизвестно'


    @property
    def file_size(self):
        """Возвращает размер файла в байтах"""
        from apps.document.services.version import VersionManager
        if self.file and hasattr(self.file, 'size'):
            manager = VersionManager()
            return manager.format_file_size(self.file.size)
        return 0