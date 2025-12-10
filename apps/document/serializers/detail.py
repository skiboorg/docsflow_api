from rest_framework import serializers

from apps.document.models.document import Document
from apps.document.serializers.list import DocumentListSerializer

class DocumentDetailShortSerializer(DocumentListSerializer):
    document_type_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    class Meta:
        model = Document
        fields = [
            'uuid',
            'document_type',
            'document_type_name',
            'company_name',
            'name',
        ]
    def get_document_type_name(self, obj):
        if obj.document_type:
            return obj.document_type.name
        else:
            return "Тип отсутсвует"

    def get_company_name(self, obj):
        if obj.company:
            return f'{obj.company.company_type.name} {obj.company.name}'


class DocumentDetailSerializer(DocumentListSerializer):
    class Meta:
        model = Document
        fields = '__all__'
