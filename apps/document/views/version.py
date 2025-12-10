import django_filters

from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.document.models.version import DocumentVersion
from apps.document.serializers.version import DocumentVersionSerializer

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

class DocumentVersionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DocumentVersionSerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = Pagination
    filterset_class = DocumentVersionFilter  # <-- используем FilterSet
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"

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
