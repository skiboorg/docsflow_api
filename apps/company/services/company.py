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
    def create_or_update_company(cls, inn: str, generate_pdf: bool = True) -> Optional[Company] or Optional[Dict]:
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

            # ФИО директора
            director_name = cls._extract_director_name(kontur_data)

            if not director_name:
                director_name = 'Не указан'

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
                    'director_name': director_name,
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