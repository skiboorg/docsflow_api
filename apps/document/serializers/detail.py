from rest_framework import serializers

from apps.document.models.document import Document
from apps.document.serializers.list import DocumentListSerializer

class DocumentDetailShortSerializer(DocumentListSerializer):
    document_type_name = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    class Meta:
        model = Document
        fields = [
            'uuid',
            'document_type',
            'document_type_name',
            'company',
            'name',
        ]
    def get_document_type_name(self, obj):
        if obj.document_type:
            return obj.document_type.name
        else:
            return None
            # return "Тип отсутсвует"

    def get_company(self, obj):
        from apps.company.serializers.company import CompanyShortSerializer
        if obj.company:
            return CompanyShortSerializer(obj.company).data


class DocumentDetailSerializer(DocumentListSerializer):
    class Meta:
        model = Document
        fields = '__all__'
