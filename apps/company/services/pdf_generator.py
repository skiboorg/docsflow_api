import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from django.conf import settings
from django.core.files import File
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

logger = logging.getLogger(__name__)

# Настройки путей из Django settings
TEMPLATES_DIR = Path(getattr(settings, 'PDF_TEMPLATES_DIR', settings.BASE_DIR / 'templates' / 'pdf'))

# Убедимся, что директория шаблонов существует
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


class PDFGenerator:
    def __init__(self, templates_dir: Path = TEMPLATES_DIR):
        self.templates_dir = templates_dir
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def _transform_kontur_data(self, kontur_data: Dict[str, Any]) -> Dict[str, Any]:
        """Преобразование данных Kontur API в формат шаблона"""

        # Базовые данные
        ul = kontur_data.get('UL', {})
        legal_name = ul.get('legalName', {})
        legal_address = ul.get('legalAddress', {})
        parsed_address = legal_address.get('parsedAddressRF', {})

        # Формируем адрес
        address = parsed_address.get('oneLineFormatOfAddress', '')

        # Получаем директора
        heads = ul.get('heads', [])
        current_head = heads[0] if heads else {}

        # Преобразованные данные
        transformed = {
            'inn': kontur_data.get('inn', ''),
            'ogrn': kontur_data.get('ogrn', ''),
            'kpp': ul.get('kpp', ''),
            'oktmo': ul.get('oktmo', ''),
            'okpo': ul.get('okpo', ''),
            'full_name': legal_name.get('full', ''),
            'short_name': legal_name.get('short', ''),
            'address': address,
            'registration_date': ul.get('registrationDate', ''),
            'status': ul.get('status', {}).get('statusString', ''),
            'heads_history': [],
            'kpp_history': [],
            'address_history': [],
            'accounts': []
        }

        # Обрабатываем директоров
        for head in heads:
            structured_fio = head.get('structuredFio', {})
            fio = head.get('fio', '')

            if structured_fio:
                last = structured_fio.get('lastName', '')
                first = structured_fio.get('firstName', '')
                middle = structured_fio.get('middleName', '')
                fio = f"{last} {first} {middle}".strip()

            transformed['heads_history'].append({
                'date': head.get('date', ''),
                'fio': fio,
                'name': fio,
                'position': head.get('position', '')
            })

        # История КПП
        history = ul.get('history', {})

        if transformed['kpp']:
            transformed['kpp_history'].append({
                'date': legal_name.get('date', ''),
                'kpp': transformed['kpp']
            })

        # История адресов
        if address:
            transformed['address_history'].append({
                'date': legal_address.get('date', ''),
                'address': address,
                'addressStr': address
            })

        # Обработка history
        if history:
            kpp_history = history.get('kpp', [])
            for item in kpp_history:
                if item.get('kpp') and item.get('kpp') != transformed['kpp']:
                    transformed['kpp_history'].append({
                        'date': item.get('date', ''),
                        'kpp': item.get('kpp', '')
                    })

            address_history = history.get('legalAddress', [])
            for item in address_history:
                addr_parsed = item.get('parsedAddressRF', {})
                addr_str = addr_parsed.get('oneLineFormatOfAddress', '')
                if addr_str and addr_str != address:
                    transformed['address_history'].append({
                        'date': item.get('date', ''),
                        'address': addr_str,
                        'addressStr': addr_str
                    })

            heads_history = history.get('heads', [])
            for item in heads_history:
                if item.get('fio') != current_head.get('fio'):
                    structured = item.get('structuredFio', {})
                    fio = item.get('fio', '')

                    if structured:
                        last = structured.get('lastName', '')
                        first = structured.get('firstName', '')
                        middle = structured.get('middleName', '')
                        fio = f"{last} {first} {middle}".strip()

                    transformed['heads_history'].append({
                        'date': item.get('date', ''),
                        'fio': fio,
                        'name': fio,
                        'position': item.get('position', '')
                    })

        logger.info(f"Transformed: {len(transformed['heads_history'])} heads, "
                    f"{len(transformed['kpp_history'])} KPP, {len(transformed['address_history'])} addresses")

        return transformed

    def _prepare_data(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        generation_date = datetime.now().strftime('%d.%m.%Y')
        current_year = datetime.now().year

        # Дата регистрации
        reg_date = company_data.get('registration_date')
        if reg_date and isinstance(reg_date, str):
            try:
                from dateutil import parser
                dt = parser.parse(reg_date)
                company_data['registration_date'] = dt.strftime('%d.%m.%Y')
            except Exception as e:
                logger.warning(f"Failed to parse registration date: {e}")

        # Статус
        status = company_data.get('status', '')
        if status:
            status_map = {
                'active': 'Действующее',
                'liquidating': 'Ликвидируется',
                'liquidated': 'Ликвидировано',
                'bankrupt': 'Банкрот',
                'reorganizing': 'Реорганизуется'
            }
            company_data['status'] = status_map.get(status.lower(), status)

        return {
            'company': company_data,
            'generation_date': generation_date,
            'current_year': current_year
        }

    def generate_report(self, company_data: Dict[str, Any], inn: str) -> Optional[bytes]:
        """
        Генерация PDF отчёта для компании.

        Args:
            company_data: Данные компании из Kontur API
            inn: ИНН компании

        Returns:
            Байты PDF файла или None в случае ошибки
        """
        try:
            logger.info(f"Generating PDF for INN: {inn}")

            # Преобразуем данные Kontur в формат шаблона
            transformed_data = self._transform_kontur_data(company_data)

            template_data = self._prepare_data(transformed_data)
            template = self.jinja_env.get_template('report_template.html')
            html_content = template.render(**template_data)

            # Генерируем PDF в память
            pdf_bytes = HTML(string=html_content).write_pdf()

            logger.info(f"PDF generated successfully for INN: {inn}")
            return pdf_bytes

        except Exception as e:
            logger.error(f"PDF generation error: {e}", exc_info=True)
            return None