from rest_framework import serializers
from apps.company.models.company import Company, CompanyType

from apps.company.serializers.head import HeadSerializer
from apps.company.serializers.head import CompanyHeadSerializer, CompanyHeadWriteSerializer


class CompanyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyType
        fields = ['id', 'name']

class CompanyListSerializer(serializers.ModelSerializer):
    company_type = CompanyTypeSerializer()
    heads = CompanyHeadSerializer(many=True)
    class Meta:
        model = Company
        fields = '__all__'

class CompanyShortSerializer(serializers.ModelSerializer):

    company_type = CompanyTypeSerializer()
    heads = CompanyHeadSerializer(many=True)
    class Meta:
        model = Company
        fields = [
            'uuid',
            'name',
            'company_type',
            'inn',
            'founding_date',
            'authorized_capital',
            'heads'
        ]


class CompanyCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания компании"""
    company_type_id = serializers.PrimaryKeyRelatedField(
        queryset=CompanyType.objects.all(),
        source='company_type',
        write_only=True,
        required=True
    )
    company_type = CompanyTypeSerializer(read_only=True)
    heads = CompanyHeadWriteSerializer(many=True, required=False, allow_empty=True)

    class Meta:
        model = Company
        fields = [
            'inn',
            'name',
            'company_type',
            'company_type_id',
            'founding_date',
            'authorized_capital',
            'heads'
        ]

    def validate_inn(self, value):
        """Валидация ИНН"""
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
        """Валидация уставного капитала"""
        if value < 0:
            raise serializers.ValidationError(
                'Уставной капитал не может быть отрицательным'
            )
        return value

    def create(self, validated_data):
        from apps.company.models import Head, CompanyHead
        """Создание компании с руководителями"""
        heads_data = validated_data.pop('heads', [])

        # Создаем компанию
        company = Company.objects.create(**validated_data)

        # Создаем руководителей
        for head_data in heads_data:
            # Извлекаем данные связи CompanyHead
            start_date = head_data.get('start_date')
            end_date = head_data.get('end_date')
            is_active = head_data.get('is_active', True)

            # Данные для Head
            head_fields = {
                'fio': head_data['fio'],
                'inn': head_data.get('inn'),
                'passport': head_data.get('passport'),
                'registration': head_data.get('registration')
            }

            # Создаем или находим руководителя по ИНН, если он указан
            head_inn = head_fields.get('inn')
            if head_inn:
                head, created = Head.objects.get_or_create(
                    inn=head_inn,
                    defaults=head_fields
                )
                if not created:
                    # Обновляем данные существующего руководителя
                    for key, value in head_fields.items():
                        if value is not None:
                            setattr(head, key, value)
                    head.save()
            else:
                # Создаем нового руководителя без ИНН
                head = Head.objects.create(**head_fields)

            # Создаем связь компания-руководитель
            CompanyHead.objects.create(
                company=company,
                head=head,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active
            )

        return company


class CompanyUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления компании"""
    company_type_id = serializers.PrimaryKeyRelatedField(
        queryset=CompanyType.objects.all(),
        source='company_type',
        write_only=True,
        required=False
    )
    company_type = CompanyTypeSerializer(read_only=True)
    heads = CompanyHeadWriteSerializer(many=True, required=False, allow_empty=True)

    class Meta:
        model = Company
        fields = [
            'name',
            'company_type',
            'company_type_id',
            'founding_date',
            'authorized_capital',
            'heads'
        ]
        read_only_fields = ['inn']

    def validate_authorized_capital(self, value):
        """Валидация уставного капитала"""
        if value < 0:
            raise serializers.ValidationError(
                'Уставной капитал не может быть отрицательным'
            )
        return value

    def validate(self, attrs):
        """Общая валидация"""
        print("CompanyUpdateSerializer.validate called")
        print("attrs:", attrs)
        if 'heads' in attrs:
            print("heads in attrs:", attrs['heads'])
        return attrs

    def update(self, instance, validated_data):
        from apps.company.models import Head,CompanyHead
        """Обновление компании с руководителями"""
        heads_data = validated_data.pop('heads', None)

        # Обновляем основные поля компании
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Если переданы данные о руководителях, обновляем их
        if heads_data is not None:
            # Получаем список ID руководителей из запроса
            incoming_head_ids = [
                head_data.get('id') for head_data in heads_data
                if head_data.get('id')
            ]

            # Удаляем связи, которых нет в запросе
            CompanyHead.objects.filter(
                company=instance
            ).exclude(
                id__in=[hid for hid in incoming_head_ids if hid]
            ).delete()

            # Обновляем или создаем руководителей
            for head_data in heads_data:
                company_head_id = head_data.get('id')
                start_date = head_data.get('start_date')
                end_date = head_data.get('end_date')
                is_active = head_data.get('is_active', True)

                # Данные для Head
                head_fields = {
                    'fio': head_data['fio'],
                    'inn': head_data.get('inn'),
                    'passport': head_data.get('passport'),
                    'registration': head_data.get('registration')
                }

                if company_head_id:
                    # Обновляем существующего руководителя
                    try:
                        company_head = CompanyHead.objects.get(
                            id=company_head_id,
                            company=instance
                        )

                        # Обновляем данные руководителя
                        head = company_head.head
                        for key, value in head_fields.items():
                            if value is not None:
                                setattr(head, key, value)
                        head.save()

                        # Обновляем связь
                        company_head.start_date = start_date
                        company_head.end_date = end_date
                        company_head.is_active = is_active
                        company_head.save()

                    except CompanyHead.DoesNotExist:
                        pass
                else:
                    # Создаем нового руководителя
                    head_inn = head_fields.get('inn')
                    if head_inn:
                        head, created = Head.objects.get_or_create(
                            inn=head_inn,
                            defaults=head_fields
                        )
                        if not created:
                            for key, value in head_fields.items():
                                if value is not None:
                                    setattr(head, key, value)
                            head.save()
                    else:
                        head = Head.objects.create(**head_fields)

                    # Создаем связь
                    CompanyHead.objects.create(
                        company=instance,
                        head=head,
                        start_date=start_date,
                        end_date=end_date,
                        is_active=is_active
                    )

        return instance


class CompanyDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор компании (для чтения)"""
    company_type = CompanyTypeSerializer(read_only=True)
    heads = CompanyHeadSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = [
            'id',
            'uuid',
            'inn',
            'name',
            'company_type',
            'founding_date',
            'authorized_capital',
            'heads',
            'pdf_report',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields

# class CompanyCreateSerializer(serializers.ModelSerializer):
#     """Сериализатор для создания компании"""
#
#     # Добавляем поле для приема company_type_id
#     company_type_id = serializers.PrimaryKeyRelatedField(
#         queryset=CompanyType.objects.all(),
#         source='company_type',
#         write_only=True,
#         required=False,
#         allow_null=True
#     )
#
#     # Опционально: оставляем старое поле для обратной совместимости
#     company_type = CompanyTypeSerializer(read_only=True)
#
#     class Meta:
#         model = Company
#         fields = [
#             'inn',
#             'name',
#             'company_type',  # read-only
#             'company_type_id',  # write-only
#             'director_name',
#             'founding_date',
#             'authorized_capital'
#         ]
#
#     def validate_inn(self, value):
#         if len(value) not in [10, 12]:
#             raise serializers.ValidationError(
#                 'ИНН должен содержать 10 или 12 цифр'
#             )
#         if not value.isdigit():
#             raise serializers.ValidationError(
#                 'ИНН должен содержать только цифры'
#             )
#         return value
#
#     def validate_authorized_capital(self, value):
#         if value < 0:
#             raise serializers.ValidationError(
#                 'Уставной капитал не может быть отрицательным'
#             )
#         return value
#
#
# class CompanyUpdateSerializer(serializers.ModelSerializer):
#     """Сериализатор для редактирования компании"""
#
#     # Аналогично добавляем поле для обновления
#     company_type_id = serializers.PrimaryKeyRelatedField(
#         queryset=CompanyType.objects.all(),
#         source='company_type',
#         write_only=True,
#         required=False,
#         allow_null=True
#     )
#
#     company_type = CompanyTypeSerializer(read_only=True)
#
#     class Meta:
#         model = Company
#         fields = [
#             'name',
#             'company_type',  # read-only
#             'company_type_id',  # write-only
#             'director_name',
#             'founding_date',
#             'authorized_capital'
#         ]
#         read_only_fields = ['inn']
#
#     def validate_authorized_capital(self, value):
#         if value < 0:
#             raise serializers.ValidationError(
#                 'Уставной капитал не может быть отрицательным'
#             )
#         return value
#
#
#
# class CompanyDetailSerializer(serializers.ModelSerializer):
#     """Детальный сериализатор компании (для чтения)"""
#     company_type = CompanyTypeSerializer(read_only=True)
#
#     class Meta:
#         model = Company
#         fields = [
#             'id',
#             'inn',
#             'name',
#             'company_type',
#             'director_name',
#             'founding_date',
#             'authorized_capital',
#             'created_at',
#             'updated_at'
#         ]
#         read_only_fields = fields




