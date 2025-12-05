from rest_framework import serializers

from apps.document.models import DocumentTag, DocumentType, Document
from apps.company.models.company import Company, CompanyType

from apps.company.serializers.company import CompanyTypeSerializer


class DocumentTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTag
        fields = '__all__'


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
            'id', 'name',
            'aliases', 'aliases_ids',
            'applicable_company_types', 'applicable_company_type_ids'
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    document_type_name = serializers.CharField(source='document_type.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_size_human = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()
    status_info = serializers.SerializerMethodField()
    class Meta:
        model = Document
        fields = [
            'id',
            'name',
            'company',
            'company_name',
            'document_type',
            'document_type_name',
            'upload_date',
            'uploaded_by',
            'uploaded_by_name',
            'status',
            'get_status_info',
            'file',
            'file_size_human',
            'comment'
        ]
        read_only_fields = ['upload_date', 'uploaded_by', 'file_size_human']

    def get_status(self, obj):
        if obj.approved:
            return 'Утвержден'
        elif obj.rejected:
            return 'Отклонен'
        else:
            return 'На утверждении'

    def get_status_info(self, obj):
        """Возвращает полную информацию о статусе для фронтенда"""
        status_config = {
            'approved': {
                'label': 'Утвержден',
                'color': 'text-green-500',
                'icon': 'pi pi-check-circle',

            },
            'rejected': {
                'label': 'Отклонен',
                'color': 'text-red-900',
                'icon': 'pi pi-times-circle',

            },
            'pending': {
                'label': 'На утверждении',
                'color': 'text-yellow-500',
                'icon': 'pi pi-exclamation-triangle',
            },
            'missing': {
                'label': 'Отсутствует',
                'color': 'text-red-400',
                'icon': 'pi pi-times-circle',
            }
        }

        if obj.approved:
            return status_config['approved']
        elif obj.rejected:
            return status_config['rejected']
        elif obj.missing:
            return status_config['missing']
        else:
            return status_config['pending']

