import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from function import (
    start,
    help_command,
    add_entry,
    view_all,
    view_day,
    view_week,
    view_month
)
from dotenv import load_dotenv
import os

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Загрузка токена из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

def main():
    # Инициализация бота
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Роутинг команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view_all", view_all))
    app.add_handler(CommandHandler("view_day", view_day))
    app.add_handler(CommandHandler("view_week", view_week))
    app.add_handler(CommandHandler("view_month", view_month))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_entry))
    app.add_handler(MessageHandler(filters.PHOTO, add_entry))

    # Запуск бота
    app.run_polling()

if __name__ == "__main__":
    main()