import os
from datetime import datetime, timedelta
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from database import add_entry_to_db, get_entries

# Папка для хранения изображений
IMAGE_FOLDER = "images"
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Это ваш дневник в Telegram. Вы можете:\n"
        "/add - добавить запись (текст или изображение)\n"
        "/view_all - показать все записи\n"
        "/view_day - показать записи за сегодня\n"
        "/view_week - показать записи за неделю\n"
        "/view_month - показать записи за месяц\n"
        "Введите месяц и год (например, november2024), чтобы посмотреть записи за конкретный период.\n"
        "/help - справка"
    )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/add - добавить запись (текст или изображение)\n"
        "/view_all - показать все записи\n"
        "/view_day - показать записи за сегодня\n"
        "/view_week - показать записи за неделю\n"
        "/view_month - показать записи за месяц\n"
        "Введите месяц и год (например, november2024), чтобы посмотреть записи за конкретный период.\n"
        "/help - справка"
    )

# Добавление записи
async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = update.message.text if update.message.text else None
    image_path = None

    # Если пользователь отправил изображение
    if update.message.photo:
        photo = update.message.photo[-1]  # Изображение в наилучшем качестве
        image_file = await photo.get_file()
        image_path = os.path.join(IMAGE_FOLDER, f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
        await image_file.download(image_path)

    # Сохранение записи в базе данных
    add_entry_to_db(user_id, date, entry, image_path)
    await update.message.reply_text("Запись добавлена!")

# Вывод записей
async def view_records(update: Update, context: ContextTypes.DEFAULT_TYPE, time_filter=None):
    user_id = update.effective_user.id
    now = datetime.now()

    if time_filter == "day":
        start_date = now.strftime("%Y-%m-%d 00:00:00")
        entries = get_entries(user_id, start_date=start_date)
    elif time_filter == "week":
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
        entries = get_entries(user_id, start_date=start_date)
    elif time_filter == "month":
        start_date = now.replace(day=1).strftime("%Y-%m-%d 00:00:00")
        entries = get_entries(user_id, start_date=start_date)
    else:
        entries = get_entries(user_id)

    if entries:
        for entry in entries:
            date, text, image_path = entry
            message = f"📅 {date}:\n✏️ {text}" if text else f"📅 {date}:\n[Изображение]"
            await update.message.reply_text(message)

            # Отправляем изображение, если оно есть
            if image_path:
                with open(image_path, "rb") as img:
                    await update.message.reply_photo(photo=img)
    else:
        await update.message.reply_text("Записей не найдено.")

# Обработчики вывода записей
async def view_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_records(update, context, time_filter=None)

async def view_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_records(update, context, time_filter="day")

async def view_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_records(update, context, time_filter="week")

async def view_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_records(update, context, time_filter="month")