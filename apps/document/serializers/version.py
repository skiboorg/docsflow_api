from datetime import date

from rest_framework import serializers

from apps.document.models.version import DocumentVersion
from apps.company.serializers.summary import STATUS_META
from apps.user.serializers.user_serializers import UserShortSerializer

class DocumentVersionSerializer(serializers.ModelSerializer):
    document = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    file_size = serializers.CharField(read_only=True)
    uploaded_by = UserShortSerializer(read_only=True)
    reviewed_by = UserShortSerializer(read_only=True)

    def get_document(self, instance):
        from apps.document.serializers.detail import DocumentDetailShortSerializer
        return DocumentDetailShortSerializer(instance.document).data

        # -----------------------------
        # STATUS CALCULATION
        # -----------------------------
    def get_status(self, instance):
        status_code = self.calculate_status(instance)
        return {
            "code": status_code,
            **STATUS_META[status_code]
        }

    def calculate_status(self, v: DocumentVersion) -> str:
        """
        Рассчитывает статус версии документа по правилам,
        аналогичным CompanySummaryRowSerializer.
        """
        today = date.today()

        # --------------------
        # 1. Признаки, заданные флагами
        # --------------------
        if v.on_approval:
            return "on_approval"

        if v.rejected:
            return "rejected"

        if v.missing:
            return "missing"

        # --------------------
        # 2. Валидация по датам
        # --------------------
        if v.valid_from and today < v.valid_from:
            return "not_yet_valid"

        if v.valid_until and today > v.valid_until:
            return "expired"

        # --------------------
        # 3. Признаки утверждения
        # --------------------
        if v.approved:
            return "approved"

        # --------------------
        # 4. По умолчанию
        # --------------------
        return "valid"

    class Meta:
        model = DocumentVersion
        fields = [
            "uuid",
            "version",
            "file",
            "file_size",

            # Статус
            "status",

            # Даты
            "upload_date",
            "valid_from",
            "valid_until",

            # Ответственные
            "uploaded_by",
            "reviewed_by",
            "review_date",

            # Комментарии
            "comment",
            "rejection_reason",

            # Активность
            "is_active",
            "is_current",

            # Связи
            "document",
        ]


# class DocumentVersionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DocumentVersion
#         fields = '__all__'

class DocumentVersionShortSerializer(serializers.ModelSerializer):
    file_size = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    class Meta:
        model = DocumentVersion
        fields = [
            'uuid',
            'version',
            'file',
            'file_size',
            'status_display',
            'upload_date',
        ]