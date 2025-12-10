from django.contrib.auth import get_user_model
User = get_user_model()

import os
import tempfile
import zipfile
import rarfile
from pathlib import Path
from django.core.files import File

from apps.company.models import Company, CompanyType
from apps.document.models import DocumentType, Document, DocumentVersion, UploadedDocument

from apps.document.services.version import VersionManager

class ArchiveDocumentImportService:

    def __init__(self, uploaded_document: UploadedDocument, uploaded_by_id:int):
        self.uploaded_document = uploaded_document
        self.uploaded_by_id = uploaded_by_id

    def process(self):
        """Основной вход — распаковываем и обрабатываем файлы."""
        temp_dir = tempfile.mkdtemp()

        # Распаковка
        extracted_files_dir = self._extract_archive(temp_dir)

        # Обработка файлов
        for file_path in Path(extracted_files_dir).rglob("*"):
            if file_path.is_file():
                self._process_file(file_path)

    # ---------------------------------------------
    # Распаковка архива
    # ---------------------------------------------
    def _extract_archive(self, destination: str) -> str:
        file_path = self.uploaded_document.file.path

        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path) as z:
                z.extractall(destination)
            return destination

        if rarfile.is_rarfile(file_path):
            with rarfile.RarFile(file_path) as r:
                r.extractall(destination)
            return destination

        raise ValueError("Формат архива не поддерживается (только ZIP или RAR)")

    # ---------------------------------------------
    # Парсинг файлов
    # ---------------------------------------------
    def _process_file(self, file_path: Path):
        """Ожидается формат ИНН_document_type_slug.ext"""
        name = file_path.stem  # без расширения

        if "_" not in name:
            print(f"⚠ Файл пропущен: {name} — нет разделителя '_'")
            return

        inn, doc_slug = name.split("_", 1)

        company = self._get_or_create_company(inn)
        doc_type = self._get_document_type(doc_slug)

        # if not doc_type:
        #     print(f"⚠ document_type_slug '{doc_slug}' не найден")
        #     return

        # Document
        document, _ = Document.objects.get_or_create(
            company=company,
            document_type=doc_type,
            created_by=User.objects.get(id=self.uploaded_by_id )
        )
        version_manager = VersionManager()
        # Создаем версию
        with open(file_path, "rb") as f:
            version = DocumentVersion.objects.create(
                document=document,
                version=version_manager.calculate_next_version(document),
                file=File(f, name=file_path.name),
                uploaded_by=User.objects.get(id=self.uploaded_by_id )
            )

        print(f"✔ Документ создан: {file_path.name}")

    # ---------------------------------------------
    # Company
    # ---------------------------------------------
    def _get_or_create_company(self, inn: str) -> Company:
        company = Company.objects.filter(inn=inn).first()
        if company:
            return company

        # ---------- Заглушка для запроса во внешний API ----------
        # В реальном проекте здесь будет запрос:
        # data = external_api.get_company_by_inn(inn)
        # name = data["name"]
        # director = data["director"]
        # основание = data["founding_date"]
        #
        # Пока создаем компанию с минимальными данными:
        name = f"Компания {inn}"
        director = "Неизвестен"
        founding_date = "2000-01-01"

        company_type = CompanyType.objects.first()

        return Company.objects.create(
            inn=inn,
            name=name,
            director_name=director,
            founding_date=founding_date,
            company_type=company_type,
            authorized_capital=0
        )

    # ---------------------------------------------
    # DocumentType
    # ---------------------------------------------
    def _get_document_type(self, slug: str) -> DocumentType | None:
        return DocumentType.objects.filter(slug=slug).first()
