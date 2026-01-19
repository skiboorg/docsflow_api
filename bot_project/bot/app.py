import threading
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from .handlers import start, echo, handle_button, handle_document
from dotenv import load_dotenv
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
BOT_TOKEN = os.getenv("BOT_TOKEN")

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

def run_bot():
    telegram_app.run_polling(stop_signals=None)

def start_bot():
    # Добавляем хендлеры
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    # Запуск в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
