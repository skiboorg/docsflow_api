
import django_filters
from django.utils import timezone

from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.document.models.version import DocumentVersion
from apps.document.serializers.version import DocumentVersionSerializer

from django.http import HttpResponse
import zipfile
import io
import os

from apps.document.services.version import VersionManager


class Pagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 10000

class DocumentVersionFilter(django_filters.FilterSet):
    """
    Фильтр для версий документов:
    - company: UUID компании
    - document_type_ids: ID,ID типа документа
    - status: approved / rejected / on_approval / missing / current
    """

    company = django_filters.UUIDFilter(
        field_name="document__company__uuid"
    )


    document_type_ids = django_filters.BaseInFilter(field_name='document__document_type_id', lookup_expr='in')

    status = django_filters.CharFilter(method="filter_status")

    def filter_status(self, queryset, name, value):
        value = value.lower()

        STATUS_MAP = {
            "approved": {"approved": True},
            "rejected": {"rejected": True},
            "on_approval": {"on_approval": True},
            "missing": {"missing": True},
            "current": {"is_current": True},
        }

        filters = STATUS_MAP.get(value)
        if filters:
            return queryset.filter(**filters)

        return queryset.none()

    class Meta:
        model = DocumentVersion
        fields = ["company", "document_type_ids", "status"]

class DocumentVersionViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentVersionSerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = Pagination
    filterset_class = DocumentVersionFilter
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"

    @action(detail=False, methods=['post'], url_path='download-zip')
    def download_zip(self, request):
        """
        Скачивание выбранных версий документов в ZIP архиве
        Ожидает: {"version_uuids": ["uuid1", "uuid2", ...]}
        """
        print(request.data)
        version_uuids = request.data.get('version_uuids', [])

        if not version_uuids:
            return Response(
                {"error": "Список version_uuids не может быть пустым"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем версии
        versions = DocumentVersion.objects.filter(
            uuid__in=version_uuids,
            is_active=True
        ).select_related('document__company', 'document__document_type')

        if not versions.exists():
            return Response(
                {"error": "Версии не найдены"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Создаем ZIP в памяти
        manager = VersionManager()
        zip_buffer = manager.create_zip_archive(versions)

        # Возвращаем ZIP файл
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response[
            'Content-Disposition'] = f'attachment; filename="documents_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip"'

        return response

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        print(request.data)

        new_type = request.data.get("type",None)
        valid_from = request.data.get("valid_from",None)
        valid_until = request.data.get("valid_until",None)
        is_current = request.data.get("is_current",False)
        comment = request.data.get("comment",None)
        head = request.data.get("head",None)
        if new_type:
            obj.document.document_type_id = new_type.get("id")
        if comment:
            obj.comment = comment

        if head:
            print(head)
            obj.head_id = head.get("id")
        obj.valid_from = valid_from
        obj.valid_until = valid_until
        obj.is_current = is_current
        obj.save()
        obj.document.save()
        return Response(status=200)

    def get_queryset(self):
        return (
            DocumentVersion.objects
            .select_related(
                "document",
                "document__company",
                "uploaded_by",
                "reviewed_by",
            )
            .all()
        )

    # --------------------------------------------------------
    #                   ACTIONS
    # --------------------------------------------------------


    @action(detail=True, methods=["post"])
    def approve(self, request, uuid=None):
        version = self.get_object()

        version.approved = True
        version.rejected = False
        version.on_approval = False
        version.reviewed_by = request.user
        version.review_date = now().date()
        version.save()

        return Response({"detail": "Версия утверждена"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, uuid=None):
        version = self.get_object()

        # reason = request.data.get("reason")
        # if not reason:
        #     return Response(
        #         {"error": "Необходимо указать причину отказа"},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        version.rejected = True
        version.approved = False
        version.on_approval = False
        #version.rejection_reason = reason
        version.reviewed_by = request.user
        version.review_date = now().date()
        version.save()

        return Response({"detail": "Версия отклонена"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def set_current(self, request, uuid=None):
        version = self.get_object()
        document = version.document

        # сбрасываем текущую у других
        DocumentVersion.objects.filter(
            document=document, is_current=True
        ).exclude(pk=version.pk).update(is_current=False)

        # делаем текущей
        version.is_current = True
        version.approved = True
        version.save(update_fields=["is_current", "approved"])

        return Response({"detail": "Версия установлена как текущая"}, status=status.HTTP_200_OK)
