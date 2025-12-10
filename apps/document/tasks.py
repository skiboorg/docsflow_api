from celery import shared_task
from apps.document.services import ArchiveDocumentImportService
from apps.document.models import UploadedDocument


@shared_task
def process_uploaded_archive(uploaded_document_id: int, uploaded_by_id:int):
    """Фоновая задача обработки архива."""
    uploaded = UploadedDocument.objects.get(id=uploaded_document_id)
    service = ArchiveDocumentImportService(uploaded,uploaded_by_id)
    service.process()