from rest_framework import serializers
from apps.company.models.company import Company, CompanyType
from apps.document.models import DocumentType


class CompanyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyType
        fields = '__all__'

class CompanyPivotTableSerializer(serializers.ModelSerializer):
    company_type = CompanyTypeSerializer(read_only=True)


    class Meta:
        model = Company
        fields = [
            'uuid',
            'inn',
            'name',
            'company_type',
            'director_name',
            'founding_date',
            'authorized_capital',
        ]



class CompanyFlatPivotTableSerializer(serializers.ModelSerializer):
    company_type = CompanyTypeSerializer(read_only=True)

    class Meta:
        model = Company
        fields = [
            'uuid',
            'inn',
            'name',
            'company_type',
            'director_name',
            'founding_date',
            'authorized_capital',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Получаем все типы документов
        all_document_types = DocumentType.objects.all()

        # Получаем документы компании
        company_documents = instance.documents.filter(is_active=True)

        # Создаем словарь документов по их типам
        documents_by_type = {}
        for doc in company_documents:
            documents_by_type[doc.document_type_id] = doc

        # Добавляем колонки для каждого типа документа
        for doc_type in all_document_types:
            is_applicable = self._is_document_type_applicable(doc_type, instance.company_type)

            if doc_type.id in documents_by_type:
                doc = documents_by_type[doc_type.id]
                data[f'doc_{doc_type.name}'] = self._get_document_status(doc)
                data[f'doc_{doc_type.name}_applicable'] = is_applicable
                data[f'doc_{doc_type.name}_has_file'] = True
            else:
                data[f'doc_{doc_type.name}'] = 'missing' if is_applicable else 'not_required'
                data[f'doc_{doc_type.name}_applicable'] = is_applicable
                data[f'doc_{doc_type.name}_has_file'] = False

        return data

    def _is_document_type_applicable(self, document_type, company_type):
        if not company_type:
            return False
        if not document_type.applicable_company_types.exists():
            return True
        return document_type.applicable_company_types.filter(id=company_type.id).exists()

    def _get_document_status(self, document):
        if document.missing:
            return 'missing'
        elif document.rejected:
            return 'rejected'
        elif document.approved:
            return 'approved'
        elif document.on_approval:
            return 'on_approval'
        else:
            return 'unknown'