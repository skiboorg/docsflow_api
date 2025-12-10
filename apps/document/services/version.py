from typing import Optional
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.document.models import Document,DocumentVersion

User = get_user_model()


class VersionManager:
    """Менеджер для работы с версиями документа"""

    @staticmethod
    def calculate_next_version(document: Document) -> int:
        """
        Вычисляет номер следующей версии
        """
        last_version = document.versions.filter(is_active=True).order_by('-version').first()
        return last_version.version + 1 if last_version else 1

    @staticmethod
    def validate_version_dates(valid_from: Optional[date], valid_until: Optional[date]) -> None:
        """
        Валидирует даты действия версии
        """
        if valid_from and valid_until and valid_from > valid_until:
            raise ValidationError("Дата начала действия не может быть позже даты окончания")

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Форматирует размер файла в человеко-читаемый вид
        """
        if size_bytes == 0:
            return "0 Б"

        for unit in ['Б', 'Кб', 'Мб', 'Гб']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} Тб"

    @staticmethod
    def get_version_status(version: DocumentVersion) -> str:
        """
        Возвращает текстовое представление статуса версии
        """
        if version.approved:
            return 'Утвержден'
        elif version.rejected:
            return 'Отклонен'
        elif version.missing:
            return 'Отсутствует'
        elif version.on_approval:
            return 'На утверждении'
        return 'Неизвестно'