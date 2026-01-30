import logging
import requests
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

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
                # Берём первый элемент если это список
                if isinstance(data, list):
                    if len(data) > 0:
                        logger.info(f"Kontur API returned list with {len(data)} items, taking first")
                        return data[0]
                    else:
                        logger.warning(f"Kontur API returned empty list for INN {inn}")
                        return None

                # Если уже словарь, возвращаем как есть
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

    def close(self):
        """Закрыть сессию"""
        self.session.close()