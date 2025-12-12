from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from apps.company.models import Company
from apps.document.models import DocumentType
from apps.company.serializers.summary import CompanySummaryRowSerializer, STATUS_META

class CompanyDocumentMatrixViewOLD(APIView):

    def get(self, request):
        companies = Company.objects.select_related('company_type').all()
        document_types = DocumentType.objects.prefetch_related(
            'applicable_company_types'
        ).all()

        rows = CompanySummaryRowSerializer(
            companies,
            many=True,
            context={'document_types': document_types}
        ).data

        columns = [
            {"key": dt.id, "name": dt.name}
            for dt in document_types
        ]

        return Response({
            "columns": columns,
            "rows": rows,
            "legend": STATUS_META,
        })


class CompanyMatrixPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 200
    page_size = 1   # значение по умолчанию


class CompanyDocumentMatrixView(APIView):

    def get(self, request):
        search = request.query_params.get("search")
        filter_status = request.query_params.get("status")  # один или список через запятую
        paginator = CompanyMatrixPagination()

        # ---- 1. Базовый queryset ----
        companies = Company.objects.select_related("company_type").all()

        # ---- 2. Поиск по названию или ИНН ----
        if search:
            companies = companies.filter(
                Q(name__icontains=search) |
                Q(inn__icontains=search)
            )

        # ---- 3. Загрузка типов документов ----
        document_types = DocumentType.objects.prefetch_related(
            "applicable_company_types"
        ).all()

        # ---- 4. Сериализуем строки (пока без пагинации) ----
        rows = CompanySummaryRowSerializer(
            companies,
            many=True,
            context={"document_types": document_types}
        ).data

        # ---- 5. Фильтрация по статусу ----
        if filter_status:
            statuses = {s.strip() for s in filter_status.split(",")}

            def company_matches(row):
                print(row["documents"].items())
                for dt_id, doc in row["documents"].items():
                    if doc["status"] in statuses:
                        return True
                return False

            rows = [row for row in rows if company_matches(row)]

        # ---- 6. Пагинация ----
        paginated_rows = paginator.paginate_queryset(rows, request)

        columns = [
            {"key": dt.id, "name": dt.name}
            for dt in document_types
        ]

        return paginator.get_paginated_response({
            "columns": columns,
            "rows": paginated_rows,
            "legend": STATUS_META,
        })
