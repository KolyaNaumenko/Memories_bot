import os
from PIL import Image
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import add_entry_to_db, get_entries,delete_entry_from_db
from database import add_goal_to_db, get_goals_from_db, update_goal_status_in_db, delete_goal_from_db
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from datetime import timedelta
import pytz



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
        "🎯 **Цели и напоминания**:\n"
        "   • /add_goal — Добавить новую цель с дедлайном.\n"
        "     Пример: `/add_goal Выучить Python 2024-12-20 18:00`\n"
        "   • /list_goals — Показать все цели.\n"
        "   • /mark_goal — Отметить цель как выполненную или проваленную.\n"
        "     Пример: `/mark_goal 1 completed`\n"
        "   • /delete_goal — Удалить цель по номеру.\n"
        "   • /goal_report — Отчет о выполненных и проваленных целях.\n\n"
        "🔔 Напоминания о целях автоматически отправляются перед дедлайном.\n\n"
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
        "🎯 **Цели и напоминания**:\n"
        "   • /add_goal — Добавить цель с дедлайном.\n"
        "     Формат: `/add_goal Цель 2024-12-20 18:00`\n"
        "   • /list_goals — Показать все цели (в процессе, выполненные и проваленные).\n"
        "   • /mark_goal — Изменить статус цели на выполненную или проваленную.\n"
        "     Формат: `/mark_goal <номер цели> completed/failed`\n"
        "   • /delete_goal — Удалить цель по номеру.\n"
        "   • /goal_report — Отчет о выполненных и проваленных целях.\n\n"
        "🔔 **Напоминания**:\n"
        "   Автоматически отправляются за несколько минут до дедлайна цели.\n\n"
        "💡 **Примеры использования**:\n"
        "   • `/add Успешный день!`\n"
        "   • `/add_goal Прочитать книгу 2024-12-31 20:00`\n"
        "   • `/mark_goal 1 completed`\n\n"
        "Если у вас есть вопросы или предложения, смело пишите! 😊"
    )

# Команда /add
# Команда /add
async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✏️ Пожалуйста, отправьте текст или изображение для записи!")
    return WAITING_FOR_ENTRY

# Сохранение записи
async def save_entry(update, context):
    try:
        user_id = update.effective_user.id
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = update.message

        entry_text = message.text or ""  # Текст сообщения, если он есть
        photos = message.photo  # Все фотографии из сообщения
        image_paths = []  # Список путей к сохранённым изображениям

        # Обработка фотографий, если они есть
        if photos:
            image_directory = "images"
            os.makedirs(image_directory, exist_ok=True)

            for photo in photos:
                # Берём наибольшую версию фотографии
                file = await context.bot.get_file(photo.file_id)
                image_path = os.path.join(image_directory, f"{user_id}_{photo.file_id}.jpg")
                await file.download_to_drive(image_path)
                image_paths.append(image_path)  # Добавляем путь в список

        # Формируем строку из путей к изображениям, разделяя их запятыми
        image_paths_str = ",".join(image_paths) if image_paths else None

        # Сохраняем запись в базу данных
        add_entry_to_db(user_id, date, entry_text, image_paths_str)

        # Формируем сообщение подтверждения
        confirmation_message = f"✅ Запись добавлена!\n📅 {date}\n"
        if image_paths:
            confirmation_message += f"🖼️ Добавлено изображений: {len(image_paths)}\n"
        if entry_text:
            confirmation_message += f"📝 {entry_text}"

        await update.message.reply_text(confirmation_message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("❌ Произошла ошибка при сохранении записи.")
        print(e)

def format_entry(date, entry_text, image_paths_str):
    formatted_entry = f"📅 {date}\n"
    if entry_text:
        formatted_entry += f"📝 {entry_text}\n"
    if image_paths_str:
        image_paths = image_paths_str.split(",")  # Преобразуем строку в список
        formatted_entry += f"🖼️ Изображений: {len(image_paths)}\n"
    return formatted_entry


# Отмена команды
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена. Вы можете попробовать снова, используя команду /add.")
    return ConversationHandler.END

# Функция для вывода записей
async def view_records(update: Update, context: ContextTypes.DEFAULT_TYPE, time_filter: str = None):
    user_id = update.effective_user.id
    now = datetime.now()
    start_date, end_date = None, None

    if time_filter == "day":
        start_date = now.strftime("%Y-%m-%d")
        end_date = f"{start_date} 23:59:59"
    elif time_filter == "week":
        start_date = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        end_date = (now + timedelta(days=(6 - now.weekday()))).strftime("%Y-%m-%d") + " 23:59:59"
    elif time_filter == "month":
        start_date = now.strftime("%Y-%m-01")
        next_month = now.replace(day=28) + timedelta(days=4)  # Переход на следующий месяц
        end_date = next_month.replace(day=1).strftime("%Y-%m-%d") + " 23:59:59"

    # Получаем записи из базы данных
    entries = get_entries(user_id, start_date, end_date)

    # Проверяем, есть ли записи
    if not entries:
        if time_filter == "day":
            response = "📭 У вас нет записей за сегодня."
        elif time_filter == "week":
            response = "📭 У вас нет записей за эту неделю."
        elif time_filter == "month":
            response = "📭 У вас нет записей за этот месяц."
        else:
            response = "📭 У вас ещё нет записей."
        await update.message.reply_text(response)
        return

    # Формируем ответ
    if time_filter == "day":
        response = f"📅 Записи за сегодня ({now.strftime('%Y-%m-%d')}):\n\n"
    elif time_filter == "week":
        response = f"📅 Записи за текущую неделю:\n\n"
    elif time_filter == "month":
        response = f"📅 Записи за {now.strftime('%B %Y')}:\n\n"
    else:
        response = "📔 Все записи:\n\n"

    for idx, (date, entry_text, image_paths_str) in enumerate(entries, start=1):
        formatted_entry = format_entry(date, entry_text, image_paths_str)
        response += f"{idx}. {formatted_entry}\n"

    await update.message.reply_text(response)

def format_entry(date, entry_text, image_paths_str):
    formatted_entry = f"📅 {date}\n"
    if entry_text:
        formatted_entry += f"📝 {entry_text}\n"
    if image_paths_str:
        image_paths = image_paths_str.split(",")  # Преобразуем строку в список
        formatted_entry += f"🖼️ Изображений: {len(image_paths)}\n"
    return formatted_entry


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

scheduler = BackgroundScheduler()
scheduler.start()

# Добавление новой цели
async def add_goal(update, context):
    try:
        user_id = update.effective_user.id
        message = update.message.text
        goal_data = message.replace("/add_goal", "").strip()  # Убираем команду

        # Проверяем, указаны ли цель и дедлайн
        if not goal_data:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите цель. Пример: `/add_goal Прочитать книгу 2024-12-30` или `/add_goal Прочитать книгу` для установки времени на 12:00.",
                parse_mode="Markdown"
            )
            return

        # Проверяем, есть ли в команде указанная дата (дедлайн)
        try:
            # Предполагаем, что последний элемент - это дедлайн
            *goal_parts, possible_deadline = goal_data.rsplit(maxsplit=1)
            goal_text = " ".join(goal_parts).strip()  # Цель - всё, кроме дедлайна

            # Проверяем, если последний элемент - это дата или дата с временем
            if len(possible_deadline) == 10:  # Формат YYYY-MM-DD
                deadline_str = f"{possible_deadline} 12:00"
            else:
                deadline_str = possible_deadline  # Формат YYYY-MM-DD HH:MM

            # Преобразуем строку дедлайна в datetime
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
        except (ValueError, IndexError):  # Если дедлайн не указан или указан неверно
            goal_text = goal_data  # Всё сообщение - цель
            deadline = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

        # Проверяем, есть ли текст цели
        if not goal_text:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите текст цели. Пример: `/add_goal Прочитать книгу 2024-12-30`.",
                parse_mode="Markdown"
            )
            return

        # Сохраняем цель в базу данных
        add_goal_to_db(user_id, goal_text, deadline)

        # Планируем напоминания
        await schedule_reminders(context, user_id, goal_text, deadline)

        # Отправляем подтверждение
        await update.message.reply_text(
            f"🎯 Цель добавлена: *{goal_text}*\n🕒 Дедлайн: {deadline.strftime('%Y-%m-%d %H:%M')}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ Ошибка! Проверьте формат: `/add_goal Цель YYYY-MM-DD HH:MM` или `/add_goal Цель` для установки времени на 12:00."
        )
        print(e)

async def schedule_reminders(context, user_id, goal_text, deadline):
    job_queue = context.job_queue

    # Расчёт временных точек для трёх напоминаний
    now = datetime.now()
    total_seconds = (deadline - now).total_seconds()

    if total_seconds <= 0:
        return  # Если дедлайн уже прошёл, напоминания не планируются

    reminder_intervals = [total_seconds / 4, total_seconds / 2, (3 * total_seconds) / 4]
    reminder_times = [now + timedelta(seconds=interval) for interval in reminder_intervals]

    for reminder_time in reminder_times:
        job_queue.run_once(
            reminder_callback,
            when=(reminder_time - now),
            data={"user_id": user_id, "goal_text": goal_text, "deadline": deadline},
        )

async def reminder_callback(job):
    data = job.data
    user_id = data["user_id"]
    goal_text = data["goal_text"]
    deadline = data["deadline"]

    # Отправляем напоминание
    await job.application.bot.send_message(
        chat_id=user_id,
        text=f"🔔 Напоминание!\nЦель: {goal_text}\n🕒 Дедлайн: {deadline.strftime('%Y-%m-%d %H:%M')}"
    )

# Показать все цели
async def list_goals(update, context):
    user_id = update.effective_user.id
    goals = get_goals_from_db(user_id)

    if not goals:
        await update.message.reply_text("📋 У вас пока нет целей.")
        return

    response = "🎯 Ваши цели:\n"
    for idx, (goal_id, goal_text, deadline, status) in enumerate(goals, start=1):
        response += f"{idx}. {goal_text} (до {deadline}) — {status.capitalize()}\n"
    await update.message.reply_text(response)

# Отметить цель как выполненную или проваленную
async def mark_goal(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Укажите номер цели и статус (completed/failed). Пример: /mark_goal 1 completed")
        return

    goal_id = int(context.args[0])
    status = context.args[1]

    if status not in ["completed", "failed"]:
        await update.message.reply_text("⚠️ Неверный статус. Используйте: completed или failed.")
        return

    update_goal_status_in_db(goal_id, status)
    await update.message.reply_text(f"✅ Статус цели #{goal_id} обновлён: {status.capitalize()}")

# Удаление цели
async def delete_goal(update, context):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Укажите номер цели для удаления. Например: /delete_goal 1")
        return

    goal_id = int(context.args[0])
    delete_goal_from_db(goal_id)
    await update.message.reply_text(f"✅ Цель #{goal_id} успешно удалена.")

# Отчет о целях
async def goal_report(update, context):
    user_id = update.effective_user.id
    goals = get_goals_from_db(user_id)

    completed = [g for g in goals if g[3] == "completed"]
    failed = [g for g in goals if g[3] == "failed"]

    response = "📊 Отчет о целях:\n"
    response += f"✅ Выполнено: {len(completed)}\n"
    response += f"❌ Провалено: {len(failed)}\n"

    if completed:
        response += "\n🎉 Выполненные цели:\n"
        for goal in completed:
            response += f"- {goal[1]} (до {goal[2]})\n"

    if failed:
        response += "\n😞 Проваленные цели:\n"
        for goal in failed:
            response += f"- {goal[1]} (до {goal[2]})\n"

    await update.message.reply_text(response)