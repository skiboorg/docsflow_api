import django_filters
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.document.models import DocumentTag, DocumentType, Document, UploadedDocument
from apps.document.serializers import (
    DocumentTagSerializer, DocumentTypeSerializer,
    DocumentListSerializer, DocumentDetailSerializer, DocumentCreateSerializer
)

from apps.document.tasks import process_uploaded_archive

class DocumentTagViewSet(viewsets.ModelViewSet):
    queryset = DocumentTag.objects.all()
    serializer_class = DocumentTagSerializer
    #permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']


class DocumentTypeViewSet(viewsets.ModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    # permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['applicable_company_types']
    search_fields = ['name', 'aliases__name']
    ordering_fields = ['name']

class DocumentFilter(django_filters.FilterSet):
    # Фильтрация по UUID компании
    company_uuid = django_filters.UUIDFilter(field_name='company__uuid')

    # Фильтрация по одному или нескольким document_type
    document_type_ids = django_filters.BaseInFilter(field_name='document_type_id', lookup_expr='in')

    # Фильтрация по статусу
    status = django_filters.CharFilter(method='filter_status')

    class Meta:
        model = Document
        fields = ['company_uuid', 'document_type_ids', 'status']

    def filter_status(self, queryset, name, value):
        if value == 'approved':
            return queryset.filter(approved=True)
        if value == 'rejected':
            return queryset.filter(rejected=True)
        if value == 'pending':
            return queryset.filter(on_approval=True)
        return queryset

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    #permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['upload_date', 'name']
    filter_backends = [DjangoFilterBackend]
    filterset_class = DocumentFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentCreateSerializer
        elif self.action == 'list':
            return DocumentListSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return DocumentDetailSerializer
        return DocumentListSerializer

    def get_queryset(self):
        return Document.objects.select_related('company', 'document_type')

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)



    @action(detail=False, methods=['post'])
    def upload(self, request, pk=None):
        for file in request.FILES.getlist('file'):
            uploaded = UploadedDocument.objects.create(file=file)

            # передаём id в задачу .delay
            process_uploaded_archive(uploaded.id,request.user.id)

        return Response({
            'status': 'Файлы загружены. Обработка запущена.'
        })

