import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from django.core.files.base import ContentFile
from django.db import transaction

from apps.company.models import Company, CompanyType
from apps.company.services import KonturAPIClient
from apps.company.services import PDFGenerator


logger = logging.getLogger(__name__)


class CompanyService:
    """Сервис для работы с компаниями"""

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Парсинг даты из строки"""
        if not date_str:
            return None
        try:
            from dateutil import parser
            return parser.parse(date_str).date()
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None

    @staticmethod
    def _extract_director_name(kontur_data: Dict[str, Any]) -> str:
        """Извлечение ФИО директора из данных Kontur"""
        ul = kontur_data.get('UL', {})
        heads = ul.get('heads', [])

        if not heads:
            return ''

        current_head = heads[0]
        structured_fio = current_head.get('structuredFio', {})

        if structured_fio:
            last = structured_fio.get('lastName', '')
            first = structured_fio.get('firstName', '')
            middle = structured_fio.get('middleName', '')
            return f"{last} {first} {middle}".strip()

        return current_head.get('fio', '')

    @staticmethod
    def _extract_authorized_capital(kontur_data: Dict[str, Any]) -> Decimal:
        """Извлечение уставного капитала из данных Kontur"""
        ul = kontur_data.get('UL', {})
        capital = ul.get('capital', {})

        # Уставной капитал может быть в разных полях
        capital_value = 0

        if isinstance(capital, dict):
            capital_value = capital.get('sum', 0)

        if not capital_value:
            capital_value = ul.get('authorizedCapitalAmount', 0)

        # Если капитал не найден, используем значение по умолчанию
        if not capital_value:
            capital_value = 10000  # Минимальный уставной капитал для ООО

        try:
            return Decimal(str(capital_value))
        except:
            return Decimal('10000.00')

    @staticmethod
    def _get_or_create_company_type(kontur_data: Dict[str, Any]) -> Optional[CompanyType]:
        """Получение или создание типа компании на основе данных Kontur"""
        ul = kontur_data.get('UL', {})
        opf = ul.get('opf')

        type_name = ''

        # OPF может быть строкой или объектом
        if isinstance(opf, str):
            # Если строка, используем её напрямую
            type_name = opf
        elif isinstance(opf, dict):
            # Если объект, извлекаем short или full
            type_name = opf.get('short', '') or opf.get('full', '')

        # Если нет данных об ОПФ, извлекаем из названия
        if not type_name:
            legal_name = ul.get('legalName', {})
            full_name = legal_name.get('full', '')

            # Пытаемся извлечь тип из полного названия
            if 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ' in full_name.upper():
                type_name = 'ООО'
            elif 'АКЦИОНЕРНОЕ ОБЩЕСТВО' in full_name.upper():
                type_name = 'АО'
            elif 'ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО' in full_name.upper():
                type_name = 'ПАО'
            elif 'НЕПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО' in full_name.upper():
                type_name = 'НАО'
            elif 'ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ' in full_name.upper():
                type_name = 'ИП'
            else:
                type_name = 'ООО'  # По умолчанию

        # Нормализуем название (убираем лишнее)
        type_name = type_name.strip()

        # Если это полное название ОПФ, сокращаем
        opf_map = {
            'Общества с ограниченной ответственностью': 'ООО',
            'Акционерные общества': 'АО',
            'Публичные акционерные общества': 'ПАО',
            'Непубличные акционерные общества': 'НАО',
        }

        type_name = opf_map.get(type_name, type_name)

        # Создаём или получаем тип компании
        company_type, created = CompanyType.objects.get_or_create(
            name=type_name
        )

        if created:
            logger.info(f"Created new company type: {type_name}")

        return company_type

    @classmethod
    @transaction.atomic
    def create_or_update_company(cls, inn: str, generate_pdf: bool = False) -> Optional[Dict]:
        """
        Создание или обновление компании по ИНН

        Args:
            inn: ИНН компании
            generate_pdf: Генерировать ли PDF отчёт

        Returns:
            Словарь с результатом операции
        """
        from django.db import transaction

        try:
            # Получаем данные из Kontur API
            with KonturAPIClient() as client:
                kontur_data = client.get_company_by_inn(inn)

                if not kontur_data:
                    logger.error(f"Company with INN {inn} not found in Kontur API")
                    return {"success": False, "message": "Company not found"}

            # Извлекаем данные
            ul = kontur_data.get('UL', {})
            legal_name = ul.get('legalName', {})

            # Название компании
            company_name = legal_name.get('short', '') or legal_name.get('full', '')

            if not company_name:
                logger.error(f"Cannot extract company name for INN {inn}")
                return {"success": False, "message": "Cannot extract company name for INN"}

            # Дата регистрации (founding_date)
            registration_date_str = ul.get('registrationDate', '')
            founding_date = cls._parse_date(registration_date_str)

            if not founding_date:
                logger.error(f"Cannot parse founding_date for INN {inn}")
                return {"success": False, "message": "Cannot parse founding_date for INN"}



            # Уставной капитал
            authorized_capital = cls._extract_authorized_capital(kontur_data)

            # Тип компании
            company_type = cls._get_or_create_company_type(kontur_data)

            # Используем транзакцию для атомарности
            with transaction.atomic():
                # Создаём или обновляем компанию
                company, created = Company.objects.update_or_create(
                    inn=inn,
                    defaults={
                        'name': company_name,
                        'company_type': company_type,
                        'founding_date': founding_date,
                        'authorized_capital': authorized_capital,
                    }
                )

                logger.info(f"Company {'created' if created else 'updated'}: {company}")

                # Обрабатываем руководителей
                cls._process_company_heads(company, kontur_data)

            # Генерируем PDF если требуется
            if generate_pdf:
                generator = PDFGenerator()
                pdf_bytes = generator.generate_report(kontur_data, inn)

                if pdf_bytes:
                    # Сохраняем PDF
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    pdf_filename = f"company_report_{inn}_{timestamp}.pdf"

                    # Удаляем старый PDF если есть
                    if hasattr(company, 'pdf_report') and company.pdf_report:
                        company.pdf_report.delete(save=False)

                    # Сохраняем новый PDF (если поле есть в модели)
                    if hasattr(company, 'pdf_report'):
                        company.pdf_report.save(
                            pdf_filename,
                            ContentFile(pdf_bytes),
                            save=True
                        )
                        logger.info(f"PDF saved for company {inn}: {company.pdf_report.url}")
                    else:
                        logger.info(f"PDF generated for company {inn}, but no pdf_report field in model")
                else:
                    logger.warning(f"Failed to generate PDF for company {inn}")

            return {"success": True, "message": "Done", "company": company}

        except Exception as e:
            logger.error(f"Error creating/updating company {inn}: {e}", exc_info=True)
            return {"success": False, "message": f"Error creating/updating company: {str(e)}"}

    @classmethod
    def _process_company_heads(cls, company, kontur_data: Dict[str, Any]) -> None:
        """
        Обработка руководителей компании (текущих и исторических)

        Args:
            company: Объект Company
            kontur_data: Данные от Kontur API
        """
        from apps.company.models import Head, CompanyHead
        from django.utils.dateparse import parse_date

        try:
            ul_data = kontur_data.get('UL', {})

            # Собираем всех руководителей
            heads_to_process = []

            # Текущие руководители
            current_heads = ul_data.get('heads', [])
            logger.info(f"Found {len(current_heads)} current heads for company {company.inn}")

            for head in current_heads:
                structured_fio = head.get('structuredFio', {})
                fio = head.get('fio', '')

                # Если нет полного ФИО, собираем из структурированного
                if not fio and structured_fio:
                    fio = ' '.join(filter(None, [
                        structured_fio.get('lastName', ''),
                        structured_fio.get('firstName', ''),
                        structured_fio.get('middleName', '')
                    ]))

                if fio:
                    heads_to_process.append({
                        'fio': fio,
                        'inn': head.get('innfl'),
                        'position': head.get('position'),
                        'start_date': head.get('firstDate') or head.get('date'),
                        'end_date': None,
                        'is_active': True
                    })

            # Исторические руководители
            history = ul_data.get('history', {})
            historical_heads = history.get('heads', [])
            logger.info(f"Found {len(historical_heads)} historical heads for company {company.inn}")

            for head in historical_heads:
                structured_fio = head.get('structuredFio', {})
                fio = head.get('fio', '')

                if not fio and structured_fio:
                    fio = ' '.join(filter(None, [
                        structured_fio.get('lastName', ''),
                        structured_fio.get('firstName', ''),
                        structured_fio.get('middleName', '')
                    ]))

                if not fio:
                    continue

                # Проверяем, не является ли этот руководитель текущим
                start_date = head.get('firstDate') or head.get('date')
                is_current = any(
                    h['fio'] == fio and h['start_date'] == start_date
                    for h in heads_to_process if h['is_active']
                )

                if not is_current:
                    heads_to_process.append({
                        'fio': fio,
                        'inn': head.get('innfl'),
                        'position': head.get('position'),
                        'start_date': start_date,
                        'end_date': None,
                        'is_active': False
                    })

            logger.info(f"Total heads to process: {len(heads_to_process)}")

            # Обрабатываем каждого руководителя
            for idx, head_data in enumerate(heads_to_process):
                logger.info(f"Processing head {idx + 1}/{len(heads_to_process)}: {head_data['fio']}")

                # Создаем или получаем Head (уникальность по FIO)
                head_obj, head_created = Head.objects.get_or_create(
                    fio=head_data['fio'],
                    defaults={
                        'inn': head_data.get('inn'),
                    }
                )

                logger.info(f"Head {'created' if head_created else 'found'}: {head_obj.fio} (ID: {head_obj.id})")

                # Если Head уже существует, обновляем ИНН если он был пустой
                if not head_created and head_data.get('inn') and not head_obj.inn:
                    head_obj.inn = head_data['inn']
                    head_obj.save()
                    logger.info(f"Updated INN for head {head_obj.fio}")

                # Парсим даты
                start_date = None
                if head_data.get('start_date'):
                    start_date = parse_date(head_data['start_date'])

                end_date = None
                if head_data.get('end_date'):
                    end_date = parse_date(head_data['end_date'])

                # Создаем или обновляем CompanyHead
                company_head, ch_created = CompanyHead.objects.update_or_create(
                    company=company,
                    head=head_obj,
                    start_date=start_date,
                    defaults={
                        'end_date': end_date,
                        'is_active': head_data.get('is_active', False)
                    }
                )

                ch_action = "Created" if ch_created else "Updated"
                logger.info(
                    f"{ch_action} CompanyHead (ID: {company_head.id}): "
                    f"{head_obj.fio} -> {company.name} "
                    f"(active: {company_head.is_active}, from: {start_date})"
                )

            logger.info(f"Successfully processed {len(heads_to_process)} heads for company {company.name}")

        except Exception as e:
            logger.error(f"Error processing heads for company {company.inn}: {e}", exc_info=True)
            # Не поднимаем исключение, чтобы не прерывать создание компании
    def create_or_update_company_old(cls, inn: str, generate_pdf: bool = False) -> Optional[Company] or Optional[Dict]:
        """
        Создание или обновление компании по ИНН

        Args:
            inn: ИНН компании
            generate_pdf: Генерировать ли PDF отчёт

        Returns:
            Объект Company или None в случае ошибки
        """
        try:
            # Получаем данные из Kontur API
            with KonturAPIClient() as client:
                kontur_data = client.get_company_by_inn(inn)

                if not kontur_data:
                    logger.error(f"Company with INN {inn} not found in Kontur API")
                    return {"success": False, "message": "Company not found"}

            # Извлекаем данные
            ul = kontur_data.get('UL', {})
            legal_name = ul.get('legalName', {})

            # Название компании
            company_name = legal_name.get('short', '') or legal_name.get('full', '')

            if not company_name:
                logger.error(f"Cannot extract company name for INN {inn}")
                return {"success": False, "message": "Cannot extract company name for INN"}

            # Дата регистрации (founding_date)
            registration_date_str = ul.get('registrationDate', '')
            founding_date = cls._parse_date(registration_date_str)

            if not founding_date:
                logger.error(f"Cannot parse founding_date for INN {inn}")
                return {"success": False, "message": "Cannot parse founding_date for INN"}



            # Уставной капитал
            authorized_capital = cls._extract_authorized_capital(kontur_data)

            # Тип компании
            company_type = cls._get_or_create_company_type(kontur_data)

            # Создаём или обновляем компанию
            company, created = Company.objects.update_or_create(
                inn=inn,
                defaults={
                    'name': company_name,
                    'company_type': company_type,

                    'founding_date': founding_date,
                    'authorized_capital': authorized_capital,
                }
            )

            logger.info(f"Company {'created' if created else 'updated'}: {company}")

            # Генерируем PDF если требуется
            if generate_pdf:
                generator = PDFGenerator()
                pdf_bytes = generator.generate_report(kontur_data, inn)

                if pdf_bytes:
                    # Сохраняем PDF
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    pdf_filename = f"company_report_{inn}_{timestamp}.pdf"

                    # Удаляем старый PDF если есть
                    if hasattr(company, 'pdf_report') and company.pdf_report:
                        company.pdf_report.delete(save=False)

                    # Сохраняем новый PDF (если поле есть в модели)
                    if hasattr(company, 'pdf_report'):
                        company.pdf_report.save(
                            pdf_filename,
                            ContentFile(pdf_bytes),
                            save=True
                        )
                        logger.info(f"PDF saved for company {inn}: {company.pdf_report.url}")
                    else:
                        logger.info(f"PDF generated for company {inn}, but no pdf_report field in model")
                else:
                    logger.warning(f"Failed to generate PDF for company {inn}")

            return {"success": True, "message": "Done"}

        except Exception as e:
            logger.error(f"Error creating/updating company {inn}: {e}", exc_info=True)
            return {"success": False, "message": "Error creating/updating company"}

    @classmethod
    def get_company_info(cls, inn: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о компании из Kontur API без сохранения в БД

        Args:
            inn: ИНН компании

        Returns:
            Словарь с данными компании или None
        """
        try:
            with KonturAPIClient() as client:
                kontur_data = client.get_company_by_inn(inn)

                if not kontur_data:
                    return None

                ul = kontur_data.get('UL', {})
                legal_name = ul.get('legalName', {})
                opf = ul.get('opf')

                # Безопасно извлекаем тип компании
                company_type_str = ''
                if isinstance(opf, str):
                    company_type_str = opf
                elif isinstance(opf, dict):
                    company_type_str = opf.get('short', '') or opf.get('full', '')

                # Адрес
                legal_address = ul.get('legalAddress', {})
                parsed_address = legal_address.get('parsedAddressRF', {})
                address = parsed_address.get('oneLineFormatOfAddress', '')

                return {
                    'inn': kontur_data.get('inn', ''),
                    'ogrn': kontur_data.get('ogrn', ''),
                    'name': legal_name.get('short', '') or legal_name.get('full', ''),
                    'full_name': legal_name.get('full', ''),
                    'director_name': cls._extract_director_name(kontur_data),
                    'founding_date': ul.get('registrationDate', ''),
                    'authorized_capital': float(cls._extract_authorized_capital(kontur_data)),
                    'company_type': company_type_str,
                    'status': ul.get('status', {}).get('statusString', ''),
                    'address': address,
                    'kpp': ul.get('kpp', ''),
                    'okpo': ul.get('okpo', ''),
                }

        except Exception as e:
            logger.error(f"Error getting company info for INN {inn}: {e}", exc_info=True)
            return None