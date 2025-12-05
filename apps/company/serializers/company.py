from rest_framework import serializers
from apps.company.models.company import Company, CompanyType




class CompanyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyType
        fields = ['id', 'name']

class CompanyListSerializer(serializers.ModelSerializer):
    company_type = CompanyTypeSerializer()

    class Meta:
        model = Company
        fields = '__all__'


class CompanyCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания компании"""

    # Добавляем поле для приема company_type_id
    company_type_id = serializers.PrimaryKeyRelatedField(
        queryset=CompanyType.objects.all(),
        source='company_type',
        write_only=True,
        required=False,
        allow_null=True
    )

    # Опционально: оставляем старое поле для обратной совместимости
    company_type = CompanyTypeSerializer(read_only=True)

    class Meta:
        model = Company
        fields = [
            'inn',
            'name',
            'company_type',  # read-only
            'company_type_id',  # write-only
            'director_name',
            'founding_date',
            'authorized_capital'
        ]

    def validate_inn(self, value):
        if len(value) not in [10, 12]:
            raise serializers.ValidationError(
                'ИНН должен содержать 10 или 12 цифр'
            )
        if not value.isdigit():
            raise serializers.ValidationError(
                'ИНН должен содержать только цифры'
            )
        return value

    def validate_authorized_capital(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'Уставной капитал не может быть отрицательным'
            )
        return value


class CompanyUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для редактирования компании"""

    # Аналогично добавляем поле для обновления
    company_type_id = serializers.PrimaryKeyRelatedField(
        queryset=CompanyType.objects.all(),
        source='company_type',
        write_only=True,
        required=False,
        allow_null=True
    )

    company_type = CompanyTypeSerializer(read_only=True)

    class Meta:
        model = Company
        fields = [
            'name',
            'company_type',  # read-only
            'company_type_id',  # write-only
            'director_name',
            'founding_date',
            'authorized_capital'
        ]
        read_only_fields = ['inn']

    def validate_authorized_capital(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'Уставной капитал не может быть отрицательным'
            )
        return value



class CompanyDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор компании (для чтения)"""
    company_type = CompanyTypeSerializer(read_only=True)

    class Meta:
        model = Company
        fields = [
            'id',
            'inn',
            'name',
            'company_type',
            'director_name',
            'founding_date',
            'authorized_capital',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields




