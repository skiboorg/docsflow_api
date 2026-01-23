# services/version.py
from typing import Optional, List
from datetime import date
from django.utils import timezone
import zipfile
import io
import os

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.document.models import Document, DocumentVersion

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

    def crate_version(self, document: Document, request) -> None:
        file = request.FILES.get('file')
        DocumentVersion.objects.create(
            document=document,
            file=file,
            version=self.calculate_next_version(document),
            valid_from=request.data.get("valid_from"),
            valid_until=request.data.get("valid_from"),
            uploaded_by=request.user,
            comment=request.data.get("comment")
        )

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

    @staticmethod
    def create_zip_archive(versions: List[DocumentVersion]) -> io.BytesIO:
        """
        Создает ZIP архив из списка версий документов

        Args:
            versions: QuerySet или список объектов DocumentVersion

        Returns:
            BytesIO объект с ZIP архивом
        """
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Словарь для отслеживания дубликатов имен файлов
            used_names = {}

            for version in versions:
                if not version.file:
                    continue

                try:
                    # Получаем информацию о документе
                    company_name = version.document.company.name
                    company_inn = version.document.company.inn
                    doc_type = version.document.document_type.name if version.document.document_type else "Без_типа"

                    # Очищаем имена от недопустимых символов
                    company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '_', '-')).strip()
                    doc_type = "".join(c for c in doc_type if c.isalnum() or c in (' ', '_', '-')).strip()

                    # Получаем оригинальное имя файла
                    original_filename = os.path.basename(version.file.name)
                    file_extension = os.path.splitext(original_filename)[1]

                    # Формируем путь внутри архива: ИНН_Компания/Тип_документа/версия_N_файл.ext
                    folder_path = f"{company_inn}_{company_name}/{doc_type}"
                    file_name = f"v{version.version}_{original_filename}"
                    archive_path = f"{folder_path}/{file_name}"

                    # Обрабатываем дубликаты
                    if archive_path in used_names:
                        counter = used_names[archive_path]
                        used_names[archive_path] += 1
                        base_name = os.path.splitext(file_name)[0]
                        archive_path = f"{folder_path}/{base_name}_{counter}{file_extension}"
                    else:
                        used_names[archive_path] = 1

                    # Добавляем файл в архив
                    with version.file.open('rb') as f:
                        zip_file.writestr(archive_path, f.read())

                except Exception as e:
                    # Логируем ошибку, но продолжаем работу
                    print(f"Ошибка при добавлении файла {version.uuid}: {str(e)}")
                    continue

        zip_buffer.seek(0)
        return zip_buffer