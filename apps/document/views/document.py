from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.document.models import DocumentTag, DocumentType, Document
from apps.document.serializers import (
    DocumentTagSerializer, DocumentTypeSerializer,
    DocumentListSerializer, DocumentDetailSerializer, DocumentCreateSerializer
)


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


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['company', 'document_type', 'on_approval', 'approved', 'rejected']
    search_fields = ['name', 'company__name', 'document_type__name', 'comment']
    ordering_fields = ['upload_date', 'name']

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentCreateSerializer
        elif self.action == 'list':
            return DocumentListSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return DocumentDetailSerializer
        return DocumentListSerializer

    def get_queryset(self):
        queryset = Document.objects.all()

        # Фильтрация по компании (если передан параметр)
        company_id = self.request.query_params.get('company_id')
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        # Фильтрация по статусу
        status_param = self.request.query_params.get('status')
        if status_param:
            if status_param == 'approved':
                queryset = queryset.filter(approved=True)
            elif status_param == 'rejected':
                queryset = queryset.filter(rejected=True)
            elif status_param == 'pending':
                queryset = queryset.filter(on_approval=True)

        return queryset.select_related('company', 'document_type', 'uploaded_by')

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        document = self.get_object()
        document.approved = True
        document.save()
        return Response({'status': 'Документ утвержден'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        document = self.get_object()
        document.rejected = True
        document.save()
        return Response({'status': 'Документ отклонен'})

    @action(detail=True, methods=['post'])
    def reset_status(self, request, pk=None):
        document = self.get_object()
        document.on_approval = True
        document.approved = False
        document.rejected = False
        document.save()
        return Response({'status': 'Статус сброшен на "На утверждении"'})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика по документам"""
        total = Document.objects.count()
        approved = Document.objects.filter(approved=True).count()
        rejected = Document.objects.filter(rejected=True).count()
        pending = Document.objects.filter(on_approval=True).count()

        return Response({
            'total': total,
            'approved': approved,
            'rejected': rejected,
            'pending': pending
        })