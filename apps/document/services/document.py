from typing import Optional, List, Dict, Any
from datetime import date

from django.contrib.auth import get_user_model

from apps.document.models import Document,DocumentVersion, DocumentType
from apps.company.models import Company

User = get_user_model()

class DocumentService:
    """Сервисный класс для работы с документами и версиями"""

    def __init__(self, document: Optional[Document] = None):
        self.document = document

    @classmethod
    def create_document(cls, name: str, company: Company, document_type: DocumentType,
                        created_by: User, description: str = '') -> Document:
        """
        Создает новый документ
        """
        document = Document.objects.create(
            name=name,
            company=company,
            document_type=document_type,
            created_by=created_by,
            description=description
        )
        return document

    def create_version(self, uploaded_by: User, file=None, comment: str = '',
                       valid_from: Optional[date] = None, valid_until: Optional[date] = None) -> DocumentVersion:
        """
        Создает новую версию документа
        """
        if not self.document:
            raise ValueError("Документ не установлен")

        # Получаем номер следующей версии
        last_version = self.get_latest_version()
        next_version = last_version.version + 1 if last_version else 1

        # Создаем новую версию
        version = DocumentVersion.objects.create(
            document=self.document,
            version=next_version,
            file=file,
            uploaded_by=uploaded_by,
            comment=comment,
            valid_from=valid_from,
            valid_until=valid_until,
            on_approval=bool(file),  # Если есть файл - на утверждении, если нет - отсутствует
            missing=not bool(file)
        )

        return version

    def approve_version(self, version_number: int, reviewed_by: User,
                        rejection_reason: str = '') -> DocumentVersion:
        """
        Утверждает или отклоняет версию документа
        """
        if not self.document:
            raise ValueError("Документ не установлен")

        version = self.get_version(version_number)
        if not version:
            raise ValueError(f"Версия {version_number} не найдена")

        if rejection_reason:
            # Отклонение версии
            version.rejected = True
            version.on_approval = False
            version.approved = False
            version.rejection_reason = rejection_reason
            version.reviewed_by = reviewed_by
            version.review_date = date.today()
        else:
            # Утверждение версии
            version.approved = True
            version.on_approval = False
            version.rejected = False
            version.reviewed_by = reviewed_by
            version.review_date = date.today()

            # Снимаем флаг текущей версии у других версий
            DocumentVersion.objects.filter(
                document=self.document,
                is_current=True
            ).update(is_current=False)

            version.is_current = True

        version.save()
        return version

    def get_current_version(self) -> Optional[DocumentVersion]:
        """
        Возвращает текущую утвержденную версию
        """
        if not self.document:
            return None

        return self.document.versions.filter(
            is_current=True,
            is_active=True,
            approved=True
        ).first()

    def get_latest_version(self) -> Optional[DocumentVersion]:
        """
        Возвращает последнюю версию (любого статуса)
        """
        if not self.document:
            return None

        return self.document.versions.filter(
            is_active=True
        ).order_by('-version').first()

    def get_version(self, version_number: int) -> Optional[DocumentVersion]:
        """
        Возвращает конкретную версию по номеру
        """
        if not self.document:
            return None

        return self.document.versions.filter(
            version=version_number,
            is_active=True
        ).first()

    def get_valid_version_on_date(self, target_date: date) -> Optional[DocumentVersion]:
        """
        Возвращает версию, действительную на указанную дату
        """
        if not self.document:
            return None

        # Ищем версию, которая была утверждена до target_date
        # и срок действия которой включает target_date
        return self.document.versions.filter(
            approved=True,
            is_active=True,
            valid_from__lte=target_date,
            valid_until__gte=target_date
        ).order_by('-version').first()

    def get_all_versions(self, include_inactive: bool = False) -> List[DocumentVersion]:
        """
        Возвращает все версии документа
        """
        if not self.document:
            return []

        queryset = self.document.versions.all()
        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return list(queryset.order_by('-version'))

    def get_versions_by_status(self, status: str) -> List[DocumentVersion]:
        """
        Возвращает версии по статусу
        """
        if not self.document:
            return []

        status_filters = {
            'approved': {'approved': True},
            'rejected': {'rejected': True},
            'missing': {'missing': True},
            'on_approval': {'on_approval': True},
        }

        if status not in status_filters:
            raise ValueError(f"Неизвестный статус: {status}")

        return list(self.document.versions.filter(
            is_active=True,
            **status_filters[status]
        ).order_by('-version'))

    def update_version(self, version_number: int, **kwargs) -> DocumentVersion:
        """
        Обновляет версию документа
        """
        if not self.document:
            raise ValueError("Документ не установлен")

        version = self.get_version(version_number)
        if not version:
            raise ValueError(f"Версия {version_number} не найдена")

        # Запрещаем обновление утвержденных версий
        if version.approved and not kwargs.get('force', False):
            raise ValueError("Нельзя изменять утвержденные версии")

        # Обновляем поля
        for field, value in kwargs.items():
            if field == 'file' and value:
                version.file = value
                version.missing = False
                version.on_approval = True
            elif field == 'valid_from':
                version.valid_from = value
            elif field == 'valid_until':
                version.valid_until = value
            elif field == 'comment':
                version.comment = value
            elif field not in ['force']:  # Игнорируем служебные поля
                setattr(version, field, value)

        version.save()
        return version

    def deactivate_version(self, version_number: int) -> DocumentVersion:
        """
        Деактивирует версию документа
        """
        if not self.document:
            raise ValueError("Документ не установлен")

        version = self.get_version(version_number)
        if not version:
            raise ValueError(f"Версия {version_number} не найдена")

        if version.is_current:
            raise ValueError("Нельзя деактивировать текущую версию")

        version.is_active = False
        version.save()
        return version

    def get_document_status_summary(self) -> Dict[str, Any]:
        """
        Возвращает сводку по статусам документа
        """
        if not self.document:
            return {}

        versions = self.document.versions.filter(is_active=True)

        return {
            'total_versions': versions.count(),
            'approved_versions': versions.filter(approved=True).count(),
            'rejected_versions': versions.filter(rejected=True).count(),
            'pending_versions': versions.filter(on_approval=True).count(),
            'missing_versions': versions.filter(missing=True).count(),
            'current_version': self.get_current_version().version if self.get_current_version() else None,
            'latest_version': self.get_latest_version().version if self.get_latest_version() else None,
            'is_expired': self.is_document_expired(),
        }

    def is_document_expired(self) -> bool:
        """
        Проверяет, истек ли срок действия текущей версии
        """
        current_version = self.get_current_version()
        if not current_version or not current_version.valid_until:
            return False

        return date.today() > current_version.valid_until

    def search_versions(self, search_params: Dict[str, Any]) -> List[DocumentVersion]:
        """
        Поиск версий по параметрам
        """
        if not self.document:
            return []

        queryset = self.document.versions.filter(is_active=True)

        if 'status' in search_params:
            status = search_params['status']
            if status == 'approved':
                queryset = queryset.filter(approved=True)
            elif status == 'rejected':
                queryset = queryset.filter(rejected=True)
            elif status == 'on_approval':
                queryset = queryset.filter(on_approval=True)
            elif status == 'missing':
                queryset = queryset.filter(missing=True)

        if 'uploaded_by' in search_params:
            queryset = queryset.filter(uploaded_by=search_params['uploaded_by'])

        if 'reviewed_by' in search_params:
            queryset = queryset.filter(reviewed_by=search_params['reviewed_by'])

        if 'date_from' in search_params:
            queryset = queryset.filter(upload_date__gte=search_params['date_from'])

        if 'date_to' in search_params:
            queryset = queryset.filter(upload_date__lte=search_params['date_to'])

        if 'valid_from' in search_params:
            queryset = queryset.filter(valid_from__gte=search_params['valid_from'])

        if 'valid_until' in search_params:
            queryset = queryset.filter(valid_until__lte=search_params['valid_until'])

        return list(queryset.order_by('-version'))