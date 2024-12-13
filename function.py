import os
from PIL import Image
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import add_entry_to_db, get_entries,delete_entry_from_db


# Папка для изображений
IMAGE_FOLDER = "images"
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# Статус для команды /add
WAITING_FOR_ENTRY = 1

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Добро пожаловать в ваш личный дневник! 📔\n"
        "Вы можете записывать мысли, события или прикреплять изображения.\n\n"
        "Вот, что я могу:\n"
        "✏️ /add — добавить запись (текст или фото)\n"
        "📖 /view_all — показать все записи\n"
        "📅 /view_day — записи за сегодня\n"
        "🗓️ /view_week — записи за неделю\n"
        "📆 /view_month — записи за месяц\n"
        "🔍 Введите месяц и год (например, november2024), чтобы увидеть записи за период.\n"
        "❓ /help — узнать подробнее о командах.\n"
    )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💡 Помощь по командам:\n\n"
        "✏️ /add — добавить запись (вы можете отправить текст или изображение).\n"
        "📖 /view_all — показать все записи.\n"
        "📅 /view_day — показать записи за сегодня.\n"
        "🗓️ /view_week — показать записи за последние 7 дней.\n"
        "📆 /view_month — показать записи за текущий месяц.\n"
        "🔍 Месяц и год (например, *november2024*) — записи за указанный период.\n"
    )

# Команда /add
# Команда /add
async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✏️ Пожалуйста, отправьте текст или изображение для записи!")
    return WAITING_FOR_ENTRY

# Сохранение записи
async def save_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = update.message.caption if update.message.caption else update.message.text  # Текст или подпись
    image_path = None

    # Если пользователь отправил изображение
    if update.message.photo:
        photo = update.message.photo[-1]  # Изображение в наилучшем качестве
        image_file = await photo.get_file()
        temp_path = os.path.join(IMAGE_FOLDER, f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")

        # Скачиваем файл на диск
        await image_file.download_to_drive(temp_path)

        # Конвертация изображения в допустимый формат (JPEG)
        try:
            with Image.open(temp_path) as img:
                img = img.convert("RGB")  # Преобразуем в RGB для сохранения в JPEG
                image_path = temp_path.replace(".jpg", "_converted.jpg")
                img.save(image_path, "JPEG")
                os.remove(temp_path)  # Удаляем временный файл
        except Exception as e:
            await update.message.reply_text("❌ Ошибка при обработке изображения. Пожалуйста, попробуйте снова.")
            print(f"Ошибка обработки изображения: {e}")
            return ConversationHandler.END

    # Сохранение записи в базе данных
    add_entry_to_db(user_id, date, entry, image_path)

    # Подтверждение
    await update.message.reply_text(
        "✅ Запись успешно добавлена!\n\n"
        f"📅 Дата: {date}\n"
        f"✏️ Текст: {entry if entry else 'Нет текста'}\n"
        f"🖼️ Изображение: {'Да' if image_path else 'Нет'}"
    )
    return ConversationHandler.END


# Отмена команды
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена. Вы можете попробовать снова, используя команду /add.")
    return ConversationHandler.END

# Функция для вывода записей
async def view_records(update: Update, context: ContextTypes.DEFAULT_TYPE, time_filter=None):
    user_id = update.effective_user.id
    now = datetime.now()

    # Выбор периода фильтрации
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
        entries = get_entries(user_id)  # Все записи

    if entries:
        all_entries = get_entries(user_id)  # Получаем все записи для единой нумерации
        for idx, entry in enumerate(entries, start=1 + len(all_entries) - len(entries)):  # Нумерация с учётом общего порядка
            date, text, image_path = entry
            message = f"📝 Запись #{idx}:\n📅 {date}\n"
            if text:
                message += f"✏️ {text}\n"
            if image_path:
                message += "🖼️ [Изображение]"
            await update.message.reply_text(message)

            # Отправляем изображение, если оно есть
            if image_path:
                with open(image_path, "rb") as img:
                    await update.message.reply_photo(photo=img)

        await update.message.reply_text(
            "✅ Все записи за выбранный период были отправлены.\n"
            "❌ Чтобы удалить запись, используйте команду /delete и укажите номер записи, например: /delete 1"
        )
    else:
        await update.message.reply_text("⚠️ В указанный период записей не найдено.")

async def delete_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Пожалуйста, укажите номер записи для удаления. Например: /delete 1")
        return

    record_number = int(context.args[0])
    entries = get_entries(user_id)  # Получаем все записи для нумерации

    if record_number < 1 or record_number > len(entries):
        await update.message.reply_text("⚠️ Запись с таким номером не найдена. Проверьте номер и попробуйте снова.")
        return

    entry = entries[record_number - 1]
    date, text, image_path = entry

    delete_entry_from_db(user_id, date)

    # Удаление изображения, если оно есть
    if image_path:
        try:
            os.remove(image_path)
        except FileNotFoundError:
            pass

    await update.message.reply_text(f"✅ Запись #{record_number} успешно удалена!")

# Обработчики просмотра записей
async def view_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_records(update, context, time_filter=None)

async def view_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_records(update, context, time_filter="day")

async def view_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_records(update, context, time_filter="week")

async def view_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_records(update, context, time_filter="month")