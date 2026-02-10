from rest_framework import serializers
from apps.company.models import Head, CompanyHead




class HeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Head
        fields = "__all__"

class CompanyHeadSerializer(serializers.ModelSerializer):
    head = HeadSerializer()
    class Meta:
        model = CompanyHead
        fields = "__all__"


class CompanyHeadWriteSerializer(serializers.Serializer):
    """Сериализатор для создания/обновления руководителя в компании"""
    id = serializers.IntegerField(required=False, allow_null=True)
    fio = serializers.CharField(max_length=255, required=True, allow_blank=False)
    inn = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True, default=None)
    passport = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True, default=None)
    registration = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    start_date = serializers.DateField(required=False, allow_null=True, default=None)
    end_date = serializers.DateField(required=False, allow_null=True, default=None)
    is_active = serializers.BooleanField(required=False, default=True)

    def to_internal_value(self, data):
        """Переопределяем для отладки"""
        print(f"CompanyHeadWriteSerializer.to_internal_value called with: {data}")
        result = super().to_internal_value(data)
        print(f"CompanyHeadWriteSerializer.to_internal_value result: {result}")
        return result

    def validate_fio(self, value):
        """Валидация ФИО"""
        print(f"validate_fio: {repr(value)}")
        if not value or not value.strip():
            raise serializers.ValidationError('ФИО обязательно для заполнения')
        return value.strip()

    def validate_inn(self, value):
        """Валидация ИНН руководителя"""
        if value and str(value).strip():
            value = str(value).strip()
            if len(value) not in [10, 12]:
                raise serializers.ValidationError('ИНН должен содержать 10 или 12 цифр')
            if not value.isdigit():
                raise serializers.ValidationError('ИНН должен содержать только цифры')
            return value
        return None

    def validate_passport(self, value):
        """Валидация паспорта"""
        if value and str(value).strip():
            return str(value).strip()
        return None

    def validate_registration(self, value):
        """Валидация прописки"""
        if value and str(value).strip():
            return str(value).strip()
        return None