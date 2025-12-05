from apps.document.models.document import Document
from apps.document.serializers.list import DocumentListSerializer

class DocumentDetailShortSerializer(DocumentListSerializer):
    class Meta:
        model = Document
        fields = [
            'uuid', 'document_type', 'file', 'file_size_human','status_info'
        ]
        read_only_fields = ['upload_date', 'uploaded_by', 'file_size_human']

class DocumentDetailSerializer(DocumentListSerializer):
    class Meta:
        model = Document
        fields = [
            'id', 'name', 'company', 'company_name', 'document_type', 'document_type_name',
            'upload_date', 'uploaded_by', 'uploaded_by_name', 'on_approval', 'approved', 'rejected',
            'status', 'file', 'file_size_human', 'comment'
        ]
        read_only_fields = ['upload_date', 'uploaded_by', 'file_size_human']
