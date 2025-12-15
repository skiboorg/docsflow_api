from rest_framework import serializers

from apps.document.models import DocumentTag, DocumentType, Document
from apps.company.models.company import Company, CompanyType

from apps.company.serializers.company import CompanyTypeSerializer, CompanyShortSerializer
from apps.document.serializers.version import DocumentVersionShortSerializer


class DocumentTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTag
        fields = '__all__'


class DocumentTypeShortSerializer(serializers.ModelSerializer):
    model = DocumentType
    fields = [
        'id', 'name',
    ]
class DocumentTypeSerializer(serializers.ModelSerializer):
    aliases = DocumentTagSerializer(many=True, read_only=True)
    aliases_ids = serializers.PrimaryKeyRelatedField(
        queryset=DocumentTag.objects.all(),
        source='aliases',
        many=True,
        write_only=True,
        required=False
    )

    # Более точные названия
    applicable_company_types = CompanyTypeSerializer(many=True, read_only=True)
    applicable_company_type_ids = serializers.PrimaryKeyRelatedField(
        queryset=CompanyType.objects.all(),
        source='applicable_company_types',
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = DocumentType
        fields = [
            'id', 'name','slug',
            'aliases', 'aliases_ids',
            'applicable_company_types', 'applicable_company_type_ids'
        ]


class DocumentListSerializer(serializers.ModelSerializer):

    company = CompanyShortSerializer(read_only=True)
    document_type_name = serializers.CharField(source='document_type.name', read_only=True)

    versions = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id',
            'uuid',
            'name',
            'company',
            'document_type',
            'document_type_name',
            'versions'
        ]

    def get_versions(self, obj):
        # Отдаём только версии, у которых on_approval=False
        queryset = obj.versions.filter(on_approval=False).order_by('-version')
        return DocumentVersionShortSerializer(queryset, many=True).data





