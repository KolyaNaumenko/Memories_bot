import logging
from dotenv import load_dotenv
import os
from telegram.ext import ApplicationBuilder,MessageHandler, filters, CommandHandler, CallbackQueryHandler,ConversationHandler, MessageHandler, filters
from telegram import BotCommand
from telegram.ext import ApplicationBuilder
from datetime import time as dtime
from telegram import Update, BotCommand
from telegram.ext import ContextTypes




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
    goal_report,
    sentiment_days,
    sentiment_weeks,
    sentiment_months,
    summary_week,
    summary_month,
    search_command,
    view_records,
    callback_delete,
    callback_edit,
    receive_edited_text,
    cancel_edit,
    WAITING_EDIT,
    random_command,
    stats_daily_trend
)
# функция для установки меню команд
async def set_bot_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start",             "Начать работу с ботом"),
        BotCommand("view_all",          "Показать все записи"),
        BotCommand("view_day",          "Показать записи за сегодня"),
        BotCommand("view_week",         "Показать записи за неделю"),
        BotCommand("view_month",        "Показать записи за месяц"),
        BotCommand("help",              "Справка по командам"),
        BotCommand("add",               "Добавить запись (текст или фото)"),
        BotCommand("delete",            "Удалить запись по номеру"),
        BotCommand("search",            "Поиск по тексту записей"),
        BotCommand("random",            "Показать случайную запись"),
        BotCommand("add_goal",          "Добавить цель с дедлайном"),
        BotCommand("list_goals",        "Показать все цели"),
        BotCommand("mark_goal",         "Отметить цель как completed/failed"),
        BotCommand("delete_goal",       "Удалить цель по номеру"),
        BotCommand("goal_report",       "Отчет о целях"),
        BotCommand("sentiment_days",    "Тренд настроения (дни)"),
        BotCommand("sentiment_weeks",   "Тренд настроения (недели)"),
        BotCommand("sentiment_months",  "Тренд настроения (месяцы)"),
        BotCommand("summary_week",      "Краткое резюме за неделю"),
        BotCommand("summary_month",     "Краткое резюме за месяц"),
        BotCommand("stats_daily_trend", "График числа записей за 30 дней"),
    ])


# Настройка логов
logging.basicConfig(level=logging.INFO)

# Загрузка токена из .env
load_dotenv("BOT_TOKEN.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")

def main():
    # Инициализация бота
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(callback_edit, pattern=r"^edit:\d+$")],
        states={
            WAITING_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edited_text)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
        allow_reentry=True
    )
    # Роутинг команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view_all",  lambda u,c: view_records(u,c,None)))
    app.add_handler(CommandHandler("view_day",  lambda u,c: view_records(u,c,"day")))
    app.add_handler(CommandHandler("view_week", lambda u,c: view_records(u,c,"week")))
    app.add_handler(CommandHandler("view_month",lambda u,c: view_records(u,c,"month")))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("delete",  delete_entry))
    app.add_handler(CommandHandler("add", add_entry))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("random", random_command))
    app.add_handler(CommandHandler("add_goal", add_goal))
    app.add_handler(CommandHandler("list_goals", list_goals))
    app.add_handler(CommandHandler("mark_goal", mark_goal))
    app.add_handler(CommandHandler("delete_goal", delete_goal))
    app.add_handler(CommandHandler("goal_report", goal_report))
    app.add_handler(CommandHandler("sentiment_days",  sentiment_days))
    app.add_handler(CommandHandler("sentiment_weeks",  sentiment_weeks))
    app.add_handler(CommandHandler("sentiment_months", sentiment_months))
    app.add_handler(CommandHandler("summary_week", summary_week))
    app.add_handler(CommandHandler("summary_month", summary_month))
    app.add_handler(CommandHandler("stats_daily_trend", stats_daily_trend))
    app.add_handler(edit_conv)
    app.add_handler(CallbackQueryHandler(callback_delete, pattern=r"^delete:\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_entry))
    app.add_handler(MessageHandler(filters.PHOTO, save_entry))

    # Запуск бота
    app.run_polling()

if __name__ == "__main__":
    main()
