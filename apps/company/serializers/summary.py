from datetime import date
from rest_framework import serializers

from apps.document.models import Document
from apps.company.serializers.company import CompanyShortSerializer



STATUS_META = {
    "approved": {"color": "#00ff00", "icon": "pi-check-circle", "label": "Утвержден"},
    "expired": {"color": "#c91b1b", "icon": "pi-clock", "label": "Просрочен"},
    "not_yet_valid": {"color": "#c9951b", "icon": "pi-history", "label": "Еще не действует"},
    "on_approval": {"color": "#adc91b", "icon": "pi-hourglass", "label": "На согласовании"},
    "rejected": {"color": "#ff0000", "icon": "pi-times-circle", "label": "Отклонен"},
    "missing": {"color": "#ff0000", "icon": "pi-question-circle", "label": "Отсутствует"},
    "not_required": {"color": "#000000", "icon": "pi-ban", "label": "Не требуется"},
    "valid": {"color": "#1bc92a", "icon": "pi-check", "label": "Действует"},
}


class CompanySummaryRowSerializer(serializers.Serializer):
    company = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()

    def get_company(self, obj):
        pdf_url = None
        if obj.pdf_report:
            try:
                pdf_url = obj.pdf_report.url
            except (ValueError, AttributeError):
                pdf_url = None

        return {
            'id': obj.id,
            'uuid': obj.uuid,
            'name': obj.name,
            'inn': obj.inn,
            'director_name': obj.director_name,
            'pdf_report': pdf_url,
            'founding_date': obj.founding_date,
            'authorized_capital': obj.authorized_capital,
            'company_type': obj.company_type.name if obj.company_type else None
        }

    def get_documents(self, company):
        from apps.document.serializers.detail import DocumentDetailShortSerializer

        result = {}
        document_types = self.context['document_types']
        today = date.today()

        for doc_type in document_types:

            # --- 1. Тип документа не обязателен ---
            if company.company_type not in doc_type.applicable_company_types.all():
                status = "not_required"
                result[str(doc_type.id)] = {
                    "status": status,
                    **STATUS_META[status],
                }
                continue

            # --- 2. Документ ---
            document = Document.objects.filter(
                company=company,
                document_type=doc_type
            ).first()

            if not document:
                status = "missing"
                result[str(doc_type.id)] = {
                    "company": CompanyShortSerializer(company).data,
                    "document": None,
                    "document_type": None,
                    "status": status,
                    **STATUS_META[status],
                }
                continue

            # --- 3. Версия ---
            version = (
                document.versions.filter(is_current=True).first()
                or document.versions.order_by('-version').first()
            )


            if not version:
                status = "missing"
                result[str(doc_type.id)] = {
                    "company": CompanyShortSerializer(company).data,
                    "document": DocumentDetailShortSerializer(document).data,
                    "status": status,
                    **STATUS_META[status],
                }
                continue
            print(version)

            # --- 4. Статус по срокам ---
            if version.on_approval:
                validity_status = "on_approval"
            elif version.valid_from and today < version.valid_from:
                validity_status = "not_yet_valid"
            elif version.valid_until and today > version.valid_until:
                validity_status = "expired"
            else:
                validity_status = "valid"

            # --- 5. Комбинация статусов ---
            if validity_status == "on_approval":
                final_status = "on_approval"

            elif validity_status == "expired":
                final_status = "expired"
            elif version.rejected:
                final_status = "rejected"

            elif validity_status == "not_yet_valid":
                final_status = "not_yet_valid"

            elif version.approved:
                final_status = "approved"
            else:
                final_status = "valid"

            # --- 6. Итог ---
            result[str(doc_type.id)] = {
                "company": CompanyShortSerializer(company).data,
                "document": DocumentDetailShortSerializer(document).data,
                "status": final_status,
                **STATUS_META[final_status],
                "version": version.version,
                "valid_from": version.valid_from,
                "valid_until": version.valid_until,
            }

        return result
