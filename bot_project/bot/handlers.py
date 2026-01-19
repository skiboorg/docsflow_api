from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from .db import get_user_permissions
from .keyboard import generate_keyboard
import requests
from pathlib import Path

waiting_for_file = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.message.from_user.username)
    rows = get_user_permissions(tg_id)

    if not rows:
        await update.message.reply_text("Привет! Твой Telegram не привязан к аккаунту.")
        return

    role_name, keyboard = generate_keyboard(rows)
    user_id = rows[0]['user_id']
    await update.message.reply_text(
        f"Привет! Твоя роль: {role_name} {user_id}",
        reply_markup=keyboard
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Вы написали: {update.message.text}")


# Обработка нажатия кнопок
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    tg_id = str(update.message.from_user.id)

    # Проверяем права пользователя
    rows = get_user_permissions(tg_id)
    if not rows:
        await update.message.reply_text("У вас нет прав")
        return

    role_name, _ = generate_keyboard(rows)
    can_view = any(r['can_view'] for r in rows)
    can_add = any(r['can_add'] for r in rows)
    can_edit = any(r['can_edit'] for r in rows)
    can_delete = any(r['can_delete'] for r in rows)

    if text == "👀 Просмотр" and can_view:
        await update.message.reply_text("Вы открыли просмотр")
    elif text == "➕ Добавить" and can_add:
        await update.message.reply_text("Вы можете добавить новый элемент")
    elif text == "➕ Добавить файл" and can_add:
        waiting_for_file[tg_id] = True
        await update.message.reply_text("Отправьте архив ZIP или RAR, чтобы загрузить файл")
    elif text == "✏️ Редактировать" and can_edit:
        await update.message.reply_text("Вы можете редактировать")
    elif text == "🗑 Удалить" and can_delete:
        await update.message.reply_text("Вы можете удалить")
    else:
        await update.message.reply_text("У вас нет прав на это действие")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.message.from_user.id)
    # Проверяем, нажимал ли пользователь кнопку "Добавить файл"
    if not waiting_for_file.get(tg_id):
        await update.message.reply_text("Сначала нажмите кнопку ➕ Добавить файл")
        return

    # Сбрасываем состояние после начала загрузки
    waiting_for_file[tg_id] = False
    rows = get_user_permissions(tg_id)

    if not rows or not any(r['can_add'] for r in rows):
        await update.message.reply_text("У вас нет прав на загрузку файлов")
        return

    user_id = rows[0]['user_id']

    file = update.message.document
    if not file:
        await update.message.reply_text("Файл не найден")
        return

    # Создаём временную папку
    temp_dir = Path("./temp") / tg_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_path = temp_dir / file.file_name

    # Скачиваем файл
    file_obj = await context.bot.get_file(file.file_id)
    await file_obj.download_to_drive(file_path)

    # Отправка на Django API
    # api_url = "http://127.0.0.1:8000/api/document/documents/upload/"
    api_url = "https://docs.webinfo.cc/api/document/documents/upload/"
    files = {"file": open(file_path, "rb")}
    data = {"user_id": user_id}  # передаём ID пользователя
    try:
        response = requests.post(api_url, files=files, data=data)
        if response.status_code == 200:
            await update.message.reply_text("Файл успешно загружен, обработка запущена")
        else:
            await update.message.reply_text(f"Ошибка загрузки: {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при отправке файла: {str(e)}")

    # Удаляем временный файл
    file_path.unlink()