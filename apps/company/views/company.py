import django_filters
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.company.serializers.company import *
from django.db.models import Prefetch, Q

from apps.document.models import Document

class Pagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 10000

class CompanyTypeViewSet(viewsets.ModelViewSet):
    queryset = CompanyType.objects.all()
    serializer_class = CompanyTypeSerializer
    pagination_class = None


class CompanyFilter(filters.FilterSet):
    q = django_filters.CharFilter(method='custom_filter', label="Search")

    def custom_filter(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) |
            Q(inn__icontains=value)

        )
    class Meta:
        model = Company
        fields = [
            'name',
            'inn',
        ]

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = CompanyFilter

    def get_queryset(self):
        # Оптимизируем запросы с prefetch_related
        return Company.objects.select_related('company_type').prefetch_related(
            Prefetch(
                'documents',
                queryset=Document.objects.select_related('document_type')
            )
        )



    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return CompanyCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CompanyUpdateSerializer
        elif self.action == 'retrieve':
            return CompanyDetailSerializer
        else:
            return CompanyListSerializer

    def create(self, request, *args, **kwargs):
        """Создание компании с дополнительной логикой"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Можно добавить дополнительную логику перед сохранением
        company = serializer.save()

        # Возвращаем детальную информацию о созданной компании
        detail_serializer = CompanyDetailSerializer(company)
        return Response(
            detail_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Обновление компании"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)

        # Можно добавить дополнительную логику перед сохранением
        company = serializer.save()

        # Возвращаем детальную информацию об обновленной компании
        detail_serializer = CompanyDetailSerializer(company)
        return Response(detail_serializer.data)

    @action(detail=True, methods=['get'], url_path='details')
    def company_details(self, request, pk=None):
        """Детальная информация о компании"""
        company = self.get_object()
        serializer = CompanyDetailSerializer(company)
        return Response(serializer.data)