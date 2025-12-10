from rest_framework.views import APIView
from rest_framework.response import Response
from apps.company.models import Company
from apps.document.models import DocumentType
from apps.company.serializers.summary import CompanySummaryRowSerializer, STATUS_META


class CompanyDocumentMatrixView(APIView):

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

