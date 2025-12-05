from rest_framework import serializers
from apps.document.models.document import Document


class DocumentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'name', 'company', 'document_type', 'file', 'comment'
        ]

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)