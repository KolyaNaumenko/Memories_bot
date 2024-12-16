import logging
from dotenv import load_dotenv
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.ext import Application, CommandHandler
from function import add_goal, list_goals, mark_goal, delete_goal, goal_report

from function import (
    start,
    help_command,
    add_entry,
    save_entry,
    view_all,
    view_day,
    view_week,
    view_month,
    delete_entry,
    add_goal,
    list_goals,
    mark_goal,
    delete_goal,
    goal_report
)

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Загрузка токена из .env
load_dotenv("BOT_TOKEN.env")
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
    app.add_handler(CommandHandler("delete",  delete_entry))
    app.add_handler(CommandHandler("add", add_entry))
    app.add_handler(CommandHandler("add_goal", add_goal))
    app.add_handler(CommandHandler("list_goals", list_goals))
    app.add_handler(CommandHandler("mark_goal", mark_goal))
    app.add_handler(CommandHandler("delete_goal", delete_goal))
    app.add_handler(CommandHandler("goal_report", goal_report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_entry))
    app.add_handler(MessageHandler(filters.PHOTO, save_entry))
    # Запуск бота
    app.run_polling()

if __name__ == "__main__":
    main()