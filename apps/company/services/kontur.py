import logging
import requests
from typing import Optional, Dict, Any, List
import os
from datetime import datetime
from django.utils.dateparse import parse_date

logger = logging.getLogger(__name__)

KONTUR_API_KEY = os.getenv("KONTUR_API_KEY", "")
KONTUR_API_URL = os.getenv("KONTUR_API_URL", "https://focus-api.kontur.ru/api3")


class KonturAPIClient:
    def __init__(self):
        self.api_key = KONTUR_API_KEY
        self.base_url = KONTUR_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Django-KonturClient/1.0'
        })

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def get_company_by_inn(self, inn: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о компании по ИНН из API Контур.

        Args:
            inn: ИНН компании

        Returns:
            Словарь с данными компании или None в случае ошибки
        """
        try:
            logger.info(f"Kontur API request: INN={inn}")

            url = f"{self.base_url}/req"
            params = {'inn': inn, 'key': self.api_key}

            response = self.session.get(url, params=params, timeout=30)
            logger.info(f"Kontur API response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                # Kontur API возвращает список компаний
                if isinstance(data, list):
                    if len(data) > 0:
                        logger.info(f"Kontur API returned list with {len(data)} items, taking first")
                        return data[0]
                    else:
                        logger.warning(f"Kontur API returned empty list for INN {inn}")
                        return None

                return data

            elif response.status_code == 404:
                logger.warning(f"INN {inn} not found")
                return None
            else:
                logger.error(f"Kontur API error: {response.status_code}, response: {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Kontur API timeout for INN {inn}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Kontur API request exception: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Kontur API exception: {e}", exc_info=True)
            return None

    def parse_company_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Парсинг данных компании из ответа API Контур.

        Args:
            data: Данные от API

        Returns:
            Словарь с распарсенными данными компании
        """
        try:
            ul_data = data.get('UL', {})
            legal_name = ul_data.get('legalName', {})

            company_info = {
                'inn': data.get('inn'),
                'ogrn': data.get('ogrn'),
                'kpp': ul_data.get('kpp'),
                'name': legal_name.get('short', ''),
                'full_name': legal_name.get('full', ''),
                'registration_date': ul_data.get('registrationDate'),
                'status': ul_data.get('status', {}).get('statusString'),
            }

            return company_info

        except Exception as e:
            logger.error(f"Error parsing company data: {e}", exc_info=True)
            return {}

    def parse_heads(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Парсинг данных о руководителях из ответа API.

        Args:
            data: Данные от API

        Returns:
            Список словарей с данными о руководителях (текущих и исторических)
        """
        heads_list = []

        try:
            logger.info(f"Starting parse_heads with data keys: {data.keys()}")
            ul_data = data.get('UL', {})
            logger.info(f"UL data keys: {ul_data.keys()}")

            # Текущие руководители
            current_heads = ul_data.get('heads', [])
            logger.info(f"Found {len(current_heads)} current heads")

            for idx, head in enumerate(current_heads):
                logger.info(f"Processing current head #{idx}: {head}")
                structured_fio = head.get('structuredFio', {})
                fio = head.get('fio', '')

                # Если нет полного ФИО, собираем из структурированного
                if not fio and structured_fio:
                    fio = ' '.join(filter(None, [
                        structured_fio.get('lastName', ''),
                        structured_fio.get('firstName', ''),
                        structured_fio.get('middleName', '')
                    ]))

                logger.info(f"Current head FIO: {fio}, INN: {head.get('innfl')}")

                heads_list.append({
                    'fio': fio,
                    'inn': head.get('innfl'),
                    'position': head.get('position'),
                    'start_date': head.get('firstDate') or head.get('date'),
                    'end_date': None,
                    'is_active': True
                })

            # Исторические руководители
            history = ul_data.get('history', {})
            logger.info(f"History data keys: {history.keys() if history else 'No history'}")
            historical_heads = history.get('heads', [])
            logger.info(f"Found {len(historical_heads)} historical heads")

            for idx, head in enumerate(historical_heads):
                logger.info(f"Processing historical head #{idx}: {head}")
                structured_fio = head.get('structuredFio', {})
                fio = head.get('fio', '')

                if not fio and structured_fio:
                    fio = ' '.join(filter(None, [
                        structured_fio.get('lastName', ''),
                        structured_fio.get('firstName', ''),
                        structured_fio.get('middleName', '')
                    ]))

                logger.info(f"Historical head FIO: {fio}, INN: {head.get('innfl')}")

                # Проверяем, не является ли этот руководитель текущим
                is_current = any(
                    current['fio'] == fio and current['start_date'] == (head.get('firstDate') or head.get('date'))
                    for current in current_heads
                )

                if not is_current:
                    heads_list.append({
                        'fio': fio,
                        'inn': head.get('innfl'),
                        'position': head.get('position'),
                        'start_date': head.get('firstDate') or head.get('date'),
                        'end_date': None,
                        'is_active': False
                    })
                else:
                    logger.info(f"Skipping historical head {fio} - already in current heads")

            logger.info(f"Total parsed heads: {len(heads_list)}")
            logger.info(f"Heads list: {heads_list}")
            return heads_list

        except Exception as e:
            logger.error(f"Error parsing heads data: {e}", exc_info=True)
            return []

    def create_or_update_company_with_heads(self, inn: str, Company, Head, CompanyHead):
        """
        Создать или обновить компанию вместе с руководителями.
        """
        from django.db import transaction

        logger.info(f"=== Starting create_or_update_company_with_heads for INN: {inn} ===")

        api_data = self.get_company_by_inn(inn)
        if not api_data:
            logger.error(f"Failed to get company data for INN {inn}")
            return None

        logger.info(f"API data received: {api_data.keys() if isinstance(api_data, dict) else type(api_data)}")

        try:
            with transaction.atomic():
                # Парсим данные компании
                company_info = self.parse_company_data(api_data)
                logger.info(f"Parsed company info: {company_info}")

                # Создаем или обновляем компанию
                company, created = Company.objects.update_or_create(
                    inn=company_info['inn'],
                    defaults={
                        'name': company_info['name'],
                        'ogrn': company_info.get('ogrn'),
                        'kpp': company_info.get('kpp'),
                    }
                )

                action = "Created" if created else "Updated"
                logger.info(f"{action} company: {company.name} (INN: {company.inn}, ID: {company.id})")

                # Парсим руководителей
                logger.info("Starting to parse heads...")
                heads_data = self.parse_heads(api_data)
                logger.info(f"Parsed {len(heads_data)} heads data entries")

                # Обрабатываем каждого руководителя
                for idx, head_data in enumerate(heads_data):
                    logger.info(f"=== Processing head #{idx + 1}/{len(heads_data)} ===")
                    logger.info(f"Head data: {head_data}")

                    if not head_data['fio']:
                        logger.warning("Skipping head with empty FIO")
                        continue

                    # Создаем или получаем Head
                    logger.info(f"Creating/getting Head with FIO: {head_data['fio']}")
                    head, head_created = Head.objects.get_or_create(
                        fio=head_data['fio'],
                        defaults={
                            'inn': head_data.get('inn'),
                        }
                    )
                    logger.info(f"Head {'created' if head_created else 'found'}: {head.fio} (ID: {head.id})")

                    # Обновляем ИНН если нужно
                    if not head_created and head_data.get('inn') and not head.inn:
                        logger.info(f"Updating Head INN from None to {head_data['inn']}")
                        head.inn = head_data['inn']
                        head.save()

                    # Парсим даты
                    start_date = None
                    if head_data.get('start_date'):
                        start_date = parse_date(head_data['start_date'])
                        logger.info(f"Parsed start_date: {start_date}")

                    end_date = None
                    if head_data.get('end_date'):
                        end_date = parse_date(head_data['end_date'])
                        logger.info(f"Parsed end_date: {end_date}")

                    # Создаем или обновляем CompanyHead
                    logger.info(f"Creating/updating CompanyHead for company {company.id} and head {head.id}")
                    company_head, ch_created = CompanyHead.objects.update_or_create(
                        company=company,
                        head=head,
                        start_date=start_date,
                        defaults={
                            'end_date': end_date,
                            'is_active': head_data.get('is_active', False)
                        }
                    )

                    ch_action = "Created" if ch_created else "Updated"
                    logger.info(
                        f"{ch_action} CompanyHead (ID: {company_head.id}): "
                        f"{head.fio} -> {company.name} "
                        f"(active: {company_head.is_active}, from: {start_date})"
                    )

                logger.info(f"=== Successfully processed company {company.name} with {len(heads_data)} heads ===")
                return company

        except Exception as e:
            logger.error(f"Error creating/updating company with heads: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def close(self):
        """Закрыть сессию"""
        self.session.close()