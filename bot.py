"""
Telegram Bot для работы с Django Document Management System
Версия: 4.0 FINAL (Kontur Focus + PDF Reports)

ФУНКЦИОНАЛ:
- Работа с Telegram USERNAME
- Просмотр компаний и документов
- Проверка ИНН через Контур.Фокус API
- Генерация PDF отчётов

ЗАВИСИМОСТИ:
pip install python-telegram-bot requests psycopg2-binary flask python-dotenv aiohttp jinja2 weasyprint python-dateutil

ЗАПУСК: python bot.py
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import threading
import time

from dotenv import load_dotenv
from flask import Flask, jsonify
import requests

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    from psycopg2 import pool
except ImportError:
    print("❌ pip install psycopg2-binary")
    sys.exit(1)

try:
    from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import (
        ApplicationBuilder, CommandHandler, MessageHandler,
        CallbackQueryHandler, ContextTypes, ConversationHandler, filters,
    )
except ImportError:
    print("❌ pip install python-telegram-bot")
    sys.exit(1)

try:
    import aiohttp
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from weasyprint import HTML
    from datetime import datetime
except ImportError:
    print("❌ pip install aiohttp jinja2 weasyprint python-dateutil")
    sys.exit(1)

# ================== Настройка логирования ==================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("="*60)
print("🤖 TELEGRAM BOT STARTING...")
print("="*60)

# ================== Загрузка .env ==================
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / '.env'

if not env_path.exists():
    print(f"❌ Файл .env не найден: {env_path}")
    sys.exit(1)

load_dotenv(env_path)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000/api")
KONTUR_API_KEY = os.getenv("KONTUR_API_KEY", "")
KONTUR_API_URL = os.getenv("KONTUR_API_URL", "https://focus-api.kontur.ru/api3")

DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = os.getenv('DB_PORT', '5432')

if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
    print("❌ BOT_TOKEN не установлен!")
    sys.exit(1)

logger.info(f"DB: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
logger.info(f"Django API: {DJANGO_API_URL}")
logger.info(f"Kontur API: {'✅' if KONTUR_API_KEY else '❌ НЕ НАСТРОЕН'}")

# Директории
TEMPLATES_DIR = BASE_DIR / 'templates'
REPORTS_DIR = BASE_DIR / 'reports'
TEMPLATES_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Состояния
WAITING_FOR_INN = 1

# Тест БД
print("\n" + "="*60)
print("ПРОВЕРКА БД")
print("="*60)

try:
    test_conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT, connect_timeout=5
    )
    test_conn.close()
    print(f"✅ PostgreSQL OK: {DB_NAME}@{DB_HOST}:{DB_PORT}")
except Exception as e:
    print(f"❌ БД ошибка: {e}")
    sys.exit(1)

print("="*60 + "\n")

# Connection Pool
db_pool = psycopg2.pool.ThreadedConnectionPool(
    1, 10, dbname=DB_NAME, user=DB_USER,
    password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
)

def get_db_connection():
    return db_pool.getconn()

def return_db_connection(conn):
    db_pool.putconn(conn)

# Flask & Bot
app = Flask(__name__)
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Константы
MSG_NOT_LINKED = "❌ Username не привязан"
MSG_NO_USERNAME = "❌ Нет username!"
MSG_NO_PERMISSION = "❌ Нет прав"


# ================== Kontur.Focus Client ==================

class KonturAPIClient:
    def __init__(self, api_key: str, base_url: str = KONTUR_API_URL):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_company_by_inn(self, inn: str) -> Optional[Dict[str, Any]]:
        try:
            logger.info(f"Kontur API request: INN={inn}")

            url = f"{self.base_url}/req"
            params = {'inn': inn, 'key': self.api_key}

            async with self.session.get(url, params=params, timeout=30) as response:
                logger.info(f"Kontur API response: {response.status}")

                if response.status == 200:
                    data = await response.json()

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

                elif response.status == 404:
                    logger.warning(f"INN {inn} not found")
                    return None
                else:
                    logger.error(f"Kontur API error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Kontur API exception: {e}", exc_info=True)
            return None


# ================== PDF Generator ==================

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
            except:
                pass

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

    async def generate_report(self, company_data: Dict[str, Any], inn: str) -> Optional[str]:
        try:
            logger.info(f"Generating PDF for INN: {inn}")

            # Преобразуем данные Kontur в формат шаблона
            transformed_data = self._transform_kontur_data(company_data)

            template_data = self._prepare_data(transformed_data)
            template = self.jinja_env.get_template('report_template.html')
            html_content = template.render(**template_data)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f"company_report_{inn}_{timestamp}.pdf"
            pdf_path = REPORTS_DIR / pdf_filename

            HTML(string=html_content).write_pdf(str(pdf_path))

            logger.info(f"PDF created: {pdf_path}")
            return str(pdf_path)

        except Exception as e:
            logger.error(f"PDF generation error: {e}", exc_info=True)
            return None


# ================== Helper Functions ==================

def get_user_permissions(tg_username: str) -> Optional[Dict[str, Any]]:
    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)

        check_query = "SELECT id, email, tg_id FROM users WHERE LOWER(tg_id) = LOWER(%s);"
        cur.execute(check_query, (tg_username,))
        user = cur.fetchone()

        if not user:
            return None

        query = """
        SELECT 
            u.id as user_id, u.email, r.name AS role_name,
            COALESCE(BOOL_OR(p.can_view), FALSE) as can_view,
            COALESCE(BOOL_OR(p.can_edit), FALSE) as can_edit,
            COALESCE(BOOL_OR(p.can_add), FALSE) as can_add,
            COALESCE(BOOL_OR(p.can_delete), FALSE) as can_delete
        FROM users u
        LEFT JOIN user_role r ON r.id = u.role_id
        LEFT JOIN user_role_permissions rp ON rp.role_id = r.id
        LEFT JOIN user_permission p ON p.id = rp.permission_id
        WHERE LOWER(u.tg_id) = LOWER(%s)
        GROUP BY u.id, u.email, r.name;
        """

        cur.execute(query, (tg_username,))
        result = cur.fetchone()

        if result:
            return dict(result)

        return {
            'user_id': user['id'], 'email': user['email'],
            'role_name': None, 'can_view': False,
            'can_edit': False, 'can_add': False, 'can_delete': False
        }

    except Exception as e:
        logger.error(f"get_user_permissions error: {e}", exc_info=True)
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            return_db_connection(conn)


def get_companies_list(limit: int = 50) -> List[Dict]:
    try:
        response = requests.get(
            f"{DJANGO_API_URL}/company/companies/",
            params={'page_size': limit},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'results' in data:
                return data['results']
            return data
        return []
    except Exception as e:
        logger.error(f"get_companies_list error: {e}")
        return []


def get_company_details(company_id: int) -> Optional[Dict]:
    try:
        response = requests.get(
            f"{DJANGO_API_URL}/company/companies/{company_id}/",
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"get_company_details error: {e}")
        return None


def get_company_documents(company_uuid: str) -> List[Dict]:
    try:
        response = requests.get(
            f"{DJANGO_API_URL}/document/documents/",
            params={'company_uuid': company_uuid},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'results' in data:
                return data['results']
            return data
        return []
    except Exception as e:
        logger.error(f"get_company_documents error: {e}")
        return []


def check_company_exists_by_inn(inn: str) -> Optional[Dict]:
    """Проверить существование компании по ИНН в Django"""
    try:
        response = requests.get(
            f"{DJANGO_API_URL}/company/companies/",
            params={'inn': inn},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', []) if isinstance(data, dict) else data

            if results and len(results) > 0:
                logger.info(f"Company with INN {inn} found in Django: {results[0].get('name')}")
                return results[0]

            logger.info(f"Company with INN {inn} not found in Django")
            return None

        logger.error(f"Error checking company: HTTP {response.status_code}")
        return None

    except Exception as e:
        logger.error(f"check_company_exists_by_inn error: {e}")
        return None


def create_company_in_django(kontur_data: Dict[str, Any]) -> Optional[Dict]:
    """Создать компанию в Django из данных Kontur"""
    try:
        ul = kontur_data.get('UL', {})
        legal_name = ul.get('legalName', {})
        legal_address = ul.get('legalAddress', {})
        parsed_address = legal_address.get('parsedAddressRF', {})
        heads = ul.get('heads', [])

        # Дата регистрации
        registration_date = ul.get('registrationDate', '')

        # Директор
        director_name = 'Не указан'  # Дефолтное значение
        if heads and len(heads) > 0:
            head = heads[0]
            fio = head.get('fio', '')

            structured = head.get('structuredFio', {})
            if structured:
                last = structured.get('lastName', '')
                first = structured.get('firstName', '')
                middle = structured.get('middleName', '')
                fio = f"{last} {first} {middle}".strip()

            if fio:
                director_name = fio

        # Подготовка данных для создания
        company_data = {
            'inn': kontur_data.get('inn', ''),
            'name': legal_name.get('short', '') or legal_name.get('full', '') or 'Компания',
            'director_name': director_name,  # ОБЯЗАТЕЛЬНОЕ поле
            'founding_date': registration_date or '2024-01-01',  # ОБЯЗАТЕЛЬНОЕ поле
            'authorized_capital': '10000.00',  # ОБЯЗАТЕЛЬНОЕ поле
        }

        # Опциональные поля (если есть в модели)
        optional_fields = {
            'full_name': legal_name.get('full', ''),
            'ogrn': kontur_data.get('ogrn', ''),
            'kpp': ul.get('kpp', ''),
            'legal_address': parsed_address.get('oneLineFormatOfAddress', ''),
            'registration_date': registration_date,
            'okpo': ul.get('okpo', ''),
            'oktmo': ul.get('oktmo', ''),
        }

        # Добавляем только непустые опциональные поля
        for key, value in optional_fields.items():
            if value:
                company_data[key] = value

        logger.info(f"Creating company: {company_data.get('name')} (INN: {company_data.get('inn')})")
        logger.debug(f"Company data: {company_data}")

        # POST запрос к Django API
        response = requests.post(
            f"{DJANGO_API_URL}/company/companies/",
            json=company_data,
            timeout=10
        )

        if response.status_code in [200, 201]:
            created_company = response.json()
            logger.info(f"Company created: ID={created_company.get('id')}, UUID={created_company.get('uuid')}")
            return created_company
        else:
            logger.error(f"Failed to create company: HTTP {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None

    except Exception as e:
        logger.error(f"create_company_in_django error: {e}", exc_info=True)
        return None


# ================== Bot Handlers ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = update.message.from_user
    tg_username = user_data.username
    tg_id = str(user_data.id)

    if not tg_username:
        await update.message.reply_text(MSG_NO_USERNAME)
        return

    checking_msg = await update.message.reply_text("⏳ Проверяю...")

    perm = get_user_permissions(tg_username)

    if not perm:
        message = f"{MSG_NOT_LINKED}\n\nUsername: <code>@{tg_username}</code>\nID: <code>{tg_id}</code>"
        await checking_msg.edit_text(message, parse_mode='HTML')
        return

    role_name = perm.get('role_name') or 'Не назначена'
    can_view = perm.get('can_view', False)
    can_add = perm.get('can_add', False)

    buttons = []

    if can_view:
        buttons.append(["🏢 Компании", "📄 Документы"])
        buttons.append(["🔍 Проверить ИНН"])
    if can_add:
        buttons.append(["➕ Загрузить документ"])

    buttons.append(["ℹ️ Помощь", "🔧 Статус"])

    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    welcome = f"👋 Роль: <b>{role_name}</b>\n\n"
    welcome += f"📧 {perm.get('email')}\n"
    welcome += f"👤 @{tg_username}\n\n"
    welcome += f"<b>Права:</b> Просмотр {'✅' if can_view else '❌'} | Добавление {'✅' if can_add else '❌'}"

    await checking_msg.delete()
    await update.message.reply_text(welcome, reply_markup=keyboard, parse_mode='HTML')


async def check_inn_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not KONTUR_API_KEY:
        await update.message.reply_text(
            "❌ Kontur.Focus API не настроен\n\nДобавьте KONTUR_API_KEY в .env"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🔍 <b>Проверка ИНН</b>\n\n"
        "Введите ИНН (10 или 12 цифр)\n"
        "Отмена: /cancel",
        parse_mode='HTML'
    )

    return WAITING_FOR_INN


async def process_inn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inn = update.message.text.strip()

    if not inn.isdigit() or len(inn) not in [10, 12]:
        await update.message.reply_text(
            "❌ Неверный формат ИНН (должно быть 10 или 12 цифр)\n"
            "Попробуйте ещё раз или /cancel"
        )
        return WAITING_FOR_INN

    loading_msg = await update.message.reply_text(
        f"⏳ Запрашиваю данные: <code>{inn}</code>...",
        parse_mode='HTML'
    )

    try:
        # Получение данных из Kontur
        async with KonturAPIClient(KONTUR_API_KEY) as kontur:
            company_data = await kontur.get_company_by_inn(inn)

        if not company_data:
            await loading_msg.edit_text(
                f"❌ Компания с ИНН <code>{inn}</code> не найдена в Контур.Фокус\n"
                f"Попробуйте другой ИНН или /cancel",
                parse_mode='HTML'
            )
            return WAITING_FOR_INN

        # Получаем название компании
        ul = company_data.get('UL', {})
        legal_name = ul.get('legalName', {})
        company_name = legal_name.get('short', '') or legal_name.get('full', '') or 'Компания'

        await loading_msg.edit_text(
            f"✅ Данные получены!\n"
            f"<b>{company_name}</b>\n\n"
            f"🔍 Проверяю наличие в базе...",
            parse_mode='HTML'
        )

        # Проверяем существование компании в Django
        existing_company = check_company_exists_by_inn(inn)

        if not existing_company:
            # Компании нет в базе - предлагаем создать
            await loading_msg.edit_text(
                f"📋 <b>Компания найдена в Контур.Фокус</b>\n\n"
                f"<b>{company_name}</b>\n"
                f"ИНН: <code>{inn}</code>\n\n"
                f"⚠️ Компании НЕТ в вашей базе данных\n\n"
                f"Создать компанию в базе?",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Создать", callback_data=f"create_company_{inn}"),
                        InlineKeyboardButton("📄 Только PDF", callback_data=f"pdf_only_{inn}")
                    ],
                    [InlineKeyboardButton("❌ Отмена", callback_data="cancel_create")]
                ])
            )

            # Сохраняем данные Kontur в контекст для последующего использования
            context.user_data[f'kontur_data_{inn}'] = company_data

            return WAITING_FOR_INN

        # Компания уже есть в базе
        await loading_msg.edit_text(
            f"✅ Компания найдена в базе!\n"
            f"📄 Генерирую PDF отчёт...",
            parse_mode='HTML'
        )

        # Генерация PDF
        pdf_gen = PDFGenerator()
        pdf_path = await pdf_gen.generate_report(company_data, inn)

        if not pdf_path:
            await loading_msg.edit_text("❌ Ошибка генерации PDF")
            return ConversationHandler.END

        await loading_msg.edit_text("📤 Отправляю...")

        caption = f"📊 <b>Отчёт о компании</b>\n\n"
        caption += f"<b>{company_name}</b>\n"
        caption += f"ИНН: <code>{inn}</code>\n\n"
        caption += f"✅ Компания уже есть в базе данных"

        with open(pdf_path, 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"report_{inn}.pdf",
                caption=caption,
                parse_mode='HTML'
            )

        await loading_msg.delete()

        # Удаляем файл
        try:
            os.remove(pdf_path)
        except:
            pass

        await update.message.reply_text(
            "✅ Отчёт готов!\n\nЕщё один ИНН? Введите или /cancel"
        )

        return WAITING_FOR_INN

    except Exception as e:
        logger.error(f"process_inn error: {e}", exc_info=True)
        await loading_msg.edit_text(
            f"❌ Ошибка обработки\n\nПопробуйте /cancel"
        )
        return WAITING_FOR_INN


async def cancel_inn_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено")
    return ConversationHandler.END


async def create_company_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание компании в Django после подтверждения"""
    query = update.callback_query
    await query.answer()

    inn = query.data.replace("create_company_", "")

    # Получаем сохранённые данные Kontur
    kontur_data = context.user_data.get(f'kontur_data_{inn}')

    if not kontur_data:
        await query.edit_message_text("❌ Данные компании не найдены. Попробуйте снова.")
        return

    await query.edit_message_text("⏳ Создаю компанию в базе данных...")

    try:
        # Создаём компанию в Django
        created_company = create_company_in_django(kontur_data)

        if not created_company:
            await query.edit_message_text(
                "❌ Ошибка при создании компании в базе данных\n\n"
                "Проверьте:\n"
                "• Доступность Django API\n"
                "• Права пользователя\n"
                "• Логи сервера"
            )
            return

        # Компания создана успешно
        ul = kontur_data.get('UL', {})
        legal_name = ul.get('legalName', {})
        company_name = legal_name.get('short', '') or legal_name.get('full', '')

        await query.edit_message_text(
            f"✅ <b>Компания создана в базе!</b>\n\n"
            f"<b>{company_name}</b>\n"
            f"ИНН: <code>{inn}</code>\n"
            f"ID: <code>{created_company.get('id')}</code>\n"
            f"UUID: <code>{created_company.get('uuid')}</code>\n\n"
            f"📄 Генерирую PDF отчёт...",
            parse_mode='HTML'
        )

        # Генерируем PDF
        pdf_gen = PDFGenerator()
        pdf_path = await pdf_gen.generate_report(kontur_data, inn)

        if pdf_path:
            caption = f"📊 <b>Отчёт о компании</b>\n\n"
            caption += f"<b>{company_name}</b>\n"
            caption += f"ИНН: <code>{inn}</code>\n\n"
            caption += f"✅ Компания добавлена в базу данных\n"
            caption += f"ID: {created_company.get('id')}"

            with open(pdf_path, 'rb') as pdf_file:
                await query.message.reply_document(
                    document=pdf_file,
                    filename=f"report_{inn}.pdf",
                    caption=caption,
                    parse_mode='HTML'
                )

            # Удаляем временный файл
            try:
                os.remove(pdf_path)
            except:
                pass

        await query.message.reply_text(
            "✅ Готово!\n\nМожете продолжить работу с компанией через раздел \"🏢 Компании\""
        )

        # Очищаем данные из контекста
        if f'kontur_data_{inn}' in context.user_data:
            del context.user_data[f'kontur_data_{inn}']

    except Exception as e:
        logger.error(f"create_company_callback error: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Ошибка при создании компании\n\n{str(e)}"
        )


async def pdf_only_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерация только PDF без создания компании"""
    query = update.callback_query
    await query.answer()

    inn = query.data.replace("pdf_only_", "")

    # Получаем сохранённые данные Kontur
    kontur_data = context.user_data.get(f'kontur_data_{inn}')

    if not kontur_data:
        await query.edit_message_text("❌ Данные компании не найдены. Попробуйте снова.")
        return

    await query.edit_message_text("📄 Генерирую PDF отчёт...")

    try:
        # Генерируем PDF
        pdf_gen = PDFGenerator()
        pdf_path = await pdf_gen.generate_report(kontur_data, inn)

        if not pdf_path:
            await query.edit_message_text("❌ Ошибка генерации PDF")
            return

        ul = kontur_data.get('UL', {})
        legal_name = ul.get('legalName', {})
        company_name = legal_name.get('short', '') or legal_name.get('full', '')

        caption = f"📊 <b>Отчёт о компании</b>\n\n"
        caption += f"<b>{company_name}</b>\n"
        caption += f"ИНН: <code>{inn}</code>\n\n"
        caption += f"⚠️ Компания НЕ добавлена в базу данных"

        with open(pdf_path, 'rb') as pdf_file:
            await query.message.reply_document(
                document=pdf_file,
                filename=f"report_{inn}.pdf",
                caption=caption,
                parse_mode='HTML'
            )

        await query.edit_message_text("✅ PDF отчёт отправлен")

        # Удаляем временный файл
        try:
            os.remove(pdf_path)
        except:
            pass

        # Очищаем данные из контекста
        if f'kontur_data_{inn}' in context.user_data:
            del context.user_data[f'kontur_data_{inn}']

    except Exception as e:
        logger.error(f"pdf_only_callback error: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


async def cancel_create_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания компании"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("❌ Создание компании отменено")

    # Очищаем все сохранённые данные Kontur
    keys_to_delete = [key for key in context.user_data.keys() if key.startswith('kontur_data_')]
    for key in keys_to_delete:
        del context.user_data[key]


async def companies_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loading = await update.message.reply_text("⏳ Загружаю...")

    companies = get_companies_list(limit=20)

    if not companies:
        await loading.edit_text("📂 Компании не найдены")
        return

    keyboard = []
    for company in companies:
        name = company.get('name', 'Без названия')
        inn = company.get('inn', '')
        company_id = company.get('id', '')

        display = name[:35] + '...' if len(name) > 35 else name
        button_text = f"🏢 {display} (ИНН: {inn})"

        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"company_{company_id}")
        ])

    markup = InlineKeyboardMarkup(keyboard)
    message = f"🏢 <b>Компании</b>\n\nНайдено: {len(companies)}"

    await loading.edit_text(message, reply_markup=markup, parse_mode='HTML')


async def company_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    company_id = int(query.data.replace("company_", ""))

    await query.edit_message_text("⏳ Загружаю...")

    company = get_company_details(company_id)

    if not company:
        await query.edit_message_text("❌ Не найдена")
        return

    uuid = company.get('uuid', '')

    msg = f"🏢 <b>{company.get('name', 'Без названия')}</b>\n\n"
    msg += f"• ID: <code>{company_id}</code>\n"
    msg += f"• ИНН: <code>{company.get('inn', '')}</code>\n"

    if company.get('company_type'):
        ct = company['company_type']
        if isinstance(ct, dict):
            msg += f"• Тип: {ct.get('name', '')}\n"

    if uuid:
        msg += f"\n🔑 UUID: <code>{uuid}</code>"

    keyboard = [
        [
            InlineKeyboardButton("📄 Документы", callback_data=f"docs_{uuid}"),
            InlineKeyboardButton("🔍 Проверить ИНН", callback_data=f"checkinn_{company.get('inn')}")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_companies")]
    ]

    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def company_documents_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uuid = query.data.replace("docs_", "")

    await query.edit_message_text("⏳ Загружаю документы...")

    docs = get_company_documents(uuid)

    # Поиск компании
    companies = get_companies_list(limit=1000)
    company = None
    for c in companies:
        if c.get('uuid') == uuid:
            company = c
            break

    name = company.get('name', 'Компания') if company else 'Компания'
    company_id = company.get('id') if company else None

    if not docs:
        msg = f"📂 <b>{name}</b>\n\nДокументов нет"
        keyboard = [[InlineKeyboardButton(
            "⬅️ Назад",
            callback_data=f"company_{company_id}" if company_id else "back_to_companies"
        )]]

        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return

    msg = f"📄 <b>Документы: {name}</b>\n\nВсего: {len(docs)}\n\n"

    for idx, doc in enumerate(docs[:10], 1):
        doc_name = doc.get('name', 'Без названия')
        doc_type = 'Не указан'

        if doc.get('document_type'):
            dt = doc['document_type']
            if isinstance(dt, dict):
                doc_type = dt.get('name', 'Не указан')

        date = doc.get('created_date', '')

        msg += f"{idx}. <b>{doc_name}</b>\n   Тип: {doc_type}\n   Дата: {date}\n\n"

    if len(docs) > 10:
        msg += f"<i>...и ещё {len(docs) - 10}</i>"

    keyboard = [[InlineKeyboardButton(
        "⬅️ Назад",
        callback_data=f"company_{company_id}" if company_id else "back_to_companies"
    )]]

    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def check_inn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    inn = query.data.replace("checkinn_", "")

    await query.edit_message_text(f"⏳ Запрос для ИНН: <code>{inn}</code>...", parse_mode='HTML')

    if not KONTUR_API_KEY:
        await query.edit_message_text("❌ Kontur API не настроен")
        return

    try:
        async with KonturAPIClient(KONTUR_API_KEY) as kontur:
            data = await kontur.get_company_by_inn(inn)

        if not data:
            await query.edit_message_text(f"❌ Данные для ИНН <code>{inn}</code> не найдены", parse_mode='HTML')
            return

        await query.edit_message_text("✅ Данные получены!\n📄 Генерирую PDF...")

        pdf_gen = PDFGenerator()
        pdf_path = await pdf_gen.generate_report(data, inn)

        if not pdf_path:
            await query.edit_message_text("❌ Ошибка генерации PDF")
            return

        name = data.get('short_name') or data.get('full_name') or 'Компания'
        caption = f"📊 <b>Отчёт</b>\n\n<b>{name}</b>\nИНН: <code>{inn}</code>"

        with open(pdf_path, 'rb') as pdf_file:
            await query.message.reply_document(
                document=pdf_file,
                filename=f"report_{inn}.pdf",
                caption=caption,
                parse_mode='HTML'
            )

        await query.message.reply_text("✅ Готово!")

        try:
            os.remove(pdf_path)
        except:
            pass

    except Exception as e:
        logger.error(f"check_inn_callback error: {e}", exc_info=True)
        await query.edit_message_text("❌ Ошибка")


async def back_to_companies_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("⏳ Загружаю...")

    companies = get_companies_list(limit=20)

    if not companies:
        await query.edit_message_text("📂 Нет компаний")
        return

    keyboard = []
    for company in companies:
        name = company.get('name', 'Без названия')
        inn = company.get('inn', '')
        company_id = company.get('id', '')

        display = name[:35] + '...' if len(name) > 35 else name
        button_text = f"🏢 {display} (ИНН: {inn})"

        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"company_{company_id}")
        ])

    markup = InlineKeyboardMarkup(keyboard)
    msg = f"🏢 <b>Компании</b>\n\nНайдено: {len(companies)}"

    await query.edit_message_text(msg, reply_markup=markup, parse_mode='HTML')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📖 <b>Справка</b>

<b>Команды:</b>
/start - Начать
/help - Справка
/companies - Компании
/checkinn - Проверить ИНН

<b>Кнопки:</b>
🏢 Компании
🔍 Проверить ИНН - PDF отчёт
📄 Документы
    """
    await update.message.reply_text(text, parse_mode='HTML')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Проверяю...")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        ver = cur.fetchone()[0]
        cur.close()
        return_db_connection(conn)

        text = "✅ <b>Статус</b>\n\n"
        text += f"🗄 PostgreSQL: OK\n"
        text += f"🔌 Kontur API: {'✅' if KONTUR_API_KEY else '❌'}\n"

        await msg.edit_text(text, parse_mode='HTML')

    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)}")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🏢 Компании":
        await companies_list(update, context)
    elif text == "🔍 Проверить ИНН":
        return await check_inn_start(update, context)
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
    elif text == "🔧 Статус":
        await status_command(update, context)
    elif text == "📄 Документы":
        await update.message.reply_text("📄 В разработке")
    elif text == "➕ Загрузить документ":
        await update.message.reply_text("➕ В разработке")
    else:
        await update.message.reply_text("Команда не распознана. /help")


# ================== Flask ==================

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200


# ================== Main ==================

def run_telegram_bot():
    print("\n" + "="*60)
    print("🤖 TELEGRAM БОТ ЗАПУЩЕН")
    print("="*60)
    print("✅ Готов!")
    print("📱 /start")
    print("🏢 Компании + Документы")
    print("🔍 Проверка ИНН + PDF")
    print("🛑 Ctrl+C")
    print("="*60 + "\n")

    try:
        telegram_app.run_polling(
            stop_signals=None,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Polling error: {e}", exc_info=True)


def main():
    # ConversationHandler для ИНН
    inn_handler = ConversationHandler(
        entry_points=[
            CommandHandler("checkinn", check_inn_start),
            MessageHandler(filters.Regex("^🔍 Проверить ИНН$"), check_inn_start)
        ],
        states={
            WAITING_FOR_INN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_inn)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_inn_check)]
    )

    # Регистрация
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("status", status_command))
    telegram_app.add_handler(CommandHandler("companies", companies_list))
    telegram_app.add_handler(inn_handler)

    telegram_app.add_handler(CallbackQueryHandler(
        company_details_callback, pattern='^company_\d+$'
    ))
    telegram_app.add_handler(CallbackQueryHandler(
        company_documents_callback, pattern='^docs_'
    ))
    telegram_app.add_handler(CallbackQueryHandler(
        check_inn_callback, pattern='^checkinn_'
    ))
    telegram_app.add_handler(CallbackQueryHandler(
        back_to_companies_callback, pattern='^back_to_companies$'
    ))

    # Callback handlers для создания компании
    telegram_app.add_handler(CallbackQueryHandler(
        create_company_callback, pattern='^create_company_'
    ))
    telegram_app.add_handler(CallbackQueryHandler(
        pdf_only_callback, pattern='^pdf_only_'
    ))
    telegram_app.add_handler(CallbackQueryHandler(
        cancel_create_callback, pattern='^cancel_create$'
    ))

    telegram_app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, echo
    ))

    # Запуск
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    time.sleep(2)

    flask_host = os.getenv('FLASK_HOST', '0.0.0.0')
    flask_port = int(os.getenv('FLASK_PORT', 5000))

    print(f"🌐 Flask: http://{flask_host}:{flask_port}\n")

    try:
        app.run(host=flask_host, port=flask_port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n🛑 Остановлено")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Выход")
    except Exception as e:
        logger.error(f"Fatal: {e}", exc_info=True)
        print(f"\n\n❌ Ошибка: {e}")
        sys.exit(1)