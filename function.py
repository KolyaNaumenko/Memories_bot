import os
import re
import asyncio
from datetime import datetime, timedelta, time as dtime
from dateutil.relativedelta import relativedelta
from apscheduler.schedulers.background import BackgroundScheduler
import matplotlib.pyplot as plt
import yake
from telegram.constants import ParseMode
from snownlp import SnowNLP
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CommandHandler,
)

from database import (
    add_entry_to_db,
    get_entries,
    delete_entry_from_db,
    add_goal_to_db,
    get_goals_from_db,
    update_goal_status_in_db,
    delete_goal_from_db,
    update_entry_in_db,
    get_random_entry,
    search_entries
)
# глобальный анализатор настроений
analyzer = SentimentIntensityAnalyzer()
_vader = SentimentIntensityAnalyzer()

IMAGE_FOLDER = "images"
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)
# Статус для команды /add
WAITING_FOR_ENTRY = 12
# Состояние для ConversationHandler
WAITING_EDIT = 1
# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # 2) Приветственное сообщение с HTML-разметкой
    text = (
        "<b>👋 Добро пожаловать в ваш Личный Дневник!</b>\n\n"
        "<i>Вот что я умею:</i>\n"
        "📝 <b>/add</b> — добавить запись (текст или фото)\n"
        "📖 <b>/view_all</b> — все записи\n"
        "📅 <b>/view_day</b> — за сегодня\n"
        "🗓️ <b>/view_week</b> — за неделю\n"
        "📆 <b>/view_month</b> — за месяц\n\n"
        "🔍 <b>/search</b> — поиск по записям\n"
        "💬 <b>/random</b> — случайная запись\n"
        "📊 <b>/stats</b> — график числа записей за 30 дней\n"
        "😊 <b>/sentiment_days</b> — тренд настроения по дням\n"
        "😊 <b>/sentiment_weeks</b> — тренд настроения по неделям\n"
        "😊 <b>/sentiment_months</b> — тренд настроения по месяцам\n"
        "📄 <b>/summary_week</b> — краткое резюме за неделю\n"
        "📄 <b>/summary_month</b> — краткое резюме за месяц\n\n"
        "🎯 <b>/add_goal</b> — добавить цель с дедлайном\n"
        "📋 <b>/list_goals</b> — список целей\n"
        "✅ <b>/mark_goal</b> — отметить цель\n"
        "❌ <b>/delete_goal</b> — удалить цель\n"
        "📈 <b>/goal_report</b> — отчет по целям\n\n"
        "🔔 Я буду напоминать:\n"
        "• Каждый вечер в <b>20:00</b> — сделать запись\n"
        "• Каждое воскресенье в <b>09:00</b> — еженедельный дайджест\n\n"
        "<i>Чтобы увидеть это сообщение снова — /start</i>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    # 3) Планируем задачи
    context.job_queue.run_daily(
        daily_entry_prompt,
        time=dtime(hour=20, minute=0),
        context=update.effective_user.id,
    )
    context.job_queue.run_daily(
        weekly_digest,
        time=dtime(hour=9, minute=0),
        days=(6,),
        context=update.effective_user.id,
    )


# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>💡 Помощь по командам:</b>\n\n"
        "📝 <b>/add</b> — добавить запись (текст или фото)\n"
        "📖 <b>/view_all</b> — показать все записи\n"
        "📅 <b>/view_day</b> — за сегодня\n"
        "🗓️ <b>/view_week</b> — за неделю\n"
        "📆 <b>/view_month</b> — за месяц\n\n"
        "🔍 <b>/search</b> — поиск по записям\n"
        "💬 <b>/random</b> — случайная запись\n"
        "📊 <b>/stats</b> — график числа записей за 30 дней\n"
        "😊 <b>/sentiment_days</b> — тренд по дням\n"
        "😊 <b>/sentiment_weeks</b> — тренд по неделям\n"
        "😊 <b>/sentiment_months</b> — тренд по месяцам\n"
        "📄 <b>/summary_week</b> — резюме за неделю\n"
        "📄 <b>/summary_month</b> — резюме за месяц\n\n"
        "🎯 <b>/add_goal</b> — добавить цель с дедлайном\n"
        "📋 <b>/list_goals</b> — список целей\n"
        "✅ <b>/mark_goal</b> — отметить цель\n"
        "❌ <b>/delete_goal</b> — удалить цель\n"
        "📈 <b>/goal_report</b> — отчет по целям\n\n"
        "Чтобы вернуть это сообщение — /start"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# Команда /add
async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✏️ Пожалуйста, отправьте текст или изображение для записи!")
    return WAITING_FOR_ENTRY

# Модифицированная версия функции save_entry
async def save_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = update.message

        # 1) Получаем текст и фото
        entry_text = message.text.strip() if message.text else ""
        photos = message.photo or []
        image_paths = []

        # 2) Сохраняем фото
        if photos:
            os.makedirs(IMAGE_FOLDER, exist_ok=True)
            largest = photos[-1]
            file = await context.bot.get_file(largest.file_id)
            name = f"{user_id}_{re.sub(r'[^a-zA-Z0-9]', '_', largest.file_id)}.jpg"
            path = os.path.join(IMAGE_FOLDER, name)
            await file.download_to_drive(path)
            image_paths.append(path)

        if not entry_text and not image_paths:
            return await update.message.reply_text("❌ Пожалуйста, отправьте текст или фото для записи.")

        image_paths_str = ",".join(image_paths) if image_paths else None

        # 3) Сохраняем в базу
        add_entry_to_db(user_id, date, entry_text, image_paths_str)

        # 4) Подтверждение
        resp = f"✅ Запись добавлена!\n📅 {date}\n"
        if entry_text:
            resp += f"📝 {entry_text}\n"
        if image_paths:
            resp += f"🖼️ Изображений: {len(image_paths)}"
        await update.message.reply_text(resp, parse_mode="Markdown")

        # 5) Автоматически — «Вспомните, как это было» каждые 10 записей
        all_entries = get_entries(user_id)
        if len(all_entries) % 10 == 0:
            old = get_random_entry(user_id)
            if old:
                r_date, r_text, r_imgs = old
                reminder = f"💭 Вспомните, как это было:\n📅 {r_date}"
                if r_text:
                    reminder += f"\n📝 {r_text}"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=reminder)
                if r_imgs:
                    for p in r_imgs.split(","):
                        if os.path.exists(p):
                            with open(p, "rb") as img_f:
                                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_f)

    except Exception as e:
        await update.message.reply_text("❌ Ошибка при сохранении записи.")
        print(f"save_entry error: {e}")

async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /random — выбросить случайную запись из архива
    """
    user_id = update.effective_user.id
    entry = get_random_entry(user_id)
    if not entry:
        return await update.message.reply_text("📭 У вас нет записей для случайной цитаты.")
    r_date, r_text, r_imgs = entry

    msg = f"💬 Случайная запись:\n📅 {r_date}"
    if r_text:
        msg += f"\n📝 {r_text}"
    await update.message.reply_text(msg)

    if r_imgs:
        for p in r_imgs.split(","):
            if os.path.exists(p):
                with open(p, "rb") as img_f:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_f)

# Форматирование записи для вывода
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
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    import asyncio
    import os

    user_id = update.effective_user.id
    now = datetime.now()
    start_date = end_date = None

    # Определяем диапазон по фильтру
    if time_filter == "day":
        start_date = now.strftime("%Y-%m-%d 00:00:00")
        end_date   = now.strftime("%Y-%m-%d 23:59:59")
    elif time_filter == "week":
        start_date = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d 00:00:00")
        end_date   = (now + timedelta(days=6 - now.weekday())).strftime("%Y-%m-%d 23:59:59")
    elif time_filter == "month":
        start_date = now.strftime("%Y-%m-01 00:00:00")
        nxt = now.replace(day=28) + timedelta(days=4)
        end_date   = nxt.replace(day=1).strftime("%Y-%m-%d 00:00:00")

    # Получаем записи с id
    entries = get_entries(user_id, start_date, end_date)
    if not entries:
        text = "📭 У вас ещё нет записей." if time_filter is None else "📭 Нет записей за этот период."
        await update.message.reply_text(text)
        return

    for idx, (entry_id, date_str, entry_text, image_paths_str) in enumerate(entries, start=1):
        # Анализ тональности
        if entry_text:
            compound = get_sentiment_score(entry_text)
            if compound > 0.05:
                label = "✅ Позитивный"
            elif compound < -0.05:
                label = "⚠️ Негативный"
            else:
                label = "ℹ️ Нейтральный"
        else:
            label = "ℹ️ Нет текста"

        # Формируем текст сообщения
        msg = f"{idx}. 📅 {date_str}\n{label}"
        if entry_text:
            msg += f"\n📝 {entry_text}"
        if image_paths_str:
            count = len(image_paths_str.split(","))
            msg += f"\n🖼️ Изображений: {count}"

        # Inline-кнопки для редактирования и удаления
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit:{entry_id}"),
            InlineKeyboardButton("❌ Удалить",        callback_data=f"delete:{entry_id}")
        ]])

        # Отправляем сообщение с кнопками
        await update.message.reply_text(msg, reply_markup=keyboard)

        # Отправка изображений
        if image_paths_str:
            for path in image_paths_str.split(","):
                if os.path.exists(path):
                    with open(path, "rb") as img:
                        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img)
                else:
                    await update.message.reply_text(f"⚠️ Изображение не найдено: {path}")

        # Пауза, чтобы избежать Flood 429
        await asyncio.sleep(0.3)

    # Инструкция по удалению
    await update.message.reply_text(
        "✅ Все записи отправлены.\n"
        "❌ Чтобы удалить запись, нажмите «❌ Удалить» под нужным сообщением.\n"
        "✏️ Чтобы отредактировать — «✏️ Редактировать»."
    )

async def delete_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Проверяем, передан ли номер записи
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Пожалуйста, укажите номер записи для удаления. Например: /delete 1")
        return

    # Получаем номер записи
    record_number = int(context.args[0])

    # Определяем временной фильтр (если указан)
    time_filter = context.chat_data.get("time_filter", None)
    now = datetime.now()
    start_date, end_date = None, None

    if time_filter == "day":
        start_date = now.strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 23:59:59")
    elif time_filter == "week":
        start_date = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d 00:00:00")
        end_date = (now + timedelta(days=(6 - now.weekday()))).strftime("%Y-%m-%d 23:59:59")
    elif time_filter == "month":
        start_date = now.strftime("%Y-%m-01 00:00:00")
        next_month = now.replace(day=28) + timedelta(days=4)
        end_date = next_month.replace(day=1).strftime("%Y-%m-%d 00:00:00")

    # Получаем записи с учётом фильтра
    entries = get_entries(user_id, start_date, end_date)

    # Проверяем корректность номера записи
    if record_number < 1 or record_number > len(entries):
        await update.message.reply_text("⚠️ Запись с таким номером не найдена. Проверьте номер и попробуйте снова.")
        return

    # Получаем запись для удаления
    entry = entries[record_number - 1]
    date, text, image_paths_str = entry

    # Удаляем запись из базы
    delete_entry_from_db(user_id, date)

    # Удаляем изображения, если они есть
    if image_paths_str:
        image_paths = image_paths_str.split(",")
        for image_path in image_paths:
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
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /search ключевое_слово — ищет в тексте всех записей
    """
    user_id = update.effective_user.id

    # Собираем ключевое слово
    if not context.args:
        return await update.message.reply_text(
            "❌ Пожалуйста, укажите слово для поиска. Пример: /search важное"
        )
    keyword = " ".join(context.args).strip()

    # Ищем в БД
    entries = search_entries(user_id, keyword)
    if not entries:
        return await update.message.reply_text(f"🔎 По запросу «{keyword}» ничего не найдено.")

    # Отправляем результаты
    for idx, (date_str, text, image_paths_str) in enumerate(entries, start=1):
        # Формируем сообщение
        msg = f"{idx}. 📅 {date_str}\n📝 {text}"
        await update.message.reply_text(msg)

        # Фото (если есть)
        if image_paths_str:
            for path in image_paths_str.split(","):
                try:
                    with open(path, "rb") as img:
                        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img)
                except FileNotFoundError:
                    await update.message.reply_text(f"⚠️ Изображение не найдено: {path}")

        # Пауза, чтобы не получить Flood-файлт
        await asyncio.sleep(0.2)


scheduler = BackgroundScheduler()
scheduler.start()

async def daily_entry_prompt(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data
    await context.bot.send_message(
        chat_id=user_id,
        text="✍️ Не забудьте сегодня сделать запись в дневник!"
    )

# Еженедельный дайджест за последние 7 дней
async def weekly_digest(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data
    now = datetime.now()
    # Берём записи за последние 7 дней
    start_dt = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0)
    start_date = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_date   = now.strftime("%Y-%m-%d %H:%M:%S")

    entries = get_entries(user_id, start_date, end_date)
    total = len(entries)

    # Считаем среднее настроение
    sentiments = [
        get_sentiment_score(text)
        for _, text, _ in entries
        if text
    ]
    avg = sum(sentiments) / len(sentiments) if sentiments else 0
    if avg > 0.05:
        mood = 'позитивное'
    elif avg < -0.05:
        mood = 'негативное'
    else:
        mood = 'нейтральное'

    # Формируем и отправляем дайджест
    message = (
        f"📅 Еженедельный дайджест ({start_dt.strftime('%Y-%m-%d')} — {now.strftime('%Y-%m-%d')}):\n"
        f"✏️ Записей: {total}\n"
        f"😊 Среднее настроение: {avg:.2f} ({mood})"
    )
    await context.bot.send_message(chat_id=user_id, text=message)


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



def build_sentiment_plot(dates, scores, period: str, user_id: int) -> str:
    # Агрегация compound-скоров по неделям или месяцам
    groups = {}
    for dt, sc in zip(dates, scores):
        if period == 'week':
            key = f"W{dt.isocalendar()[1]}-{dt.year}"  # Неделя-год
        else:
            key = dt.strftime('%Y-%m')  # Месяц-год
        groups.setdefault(key, []).append(sc)

    labels = sorted(groups.keys())
    means = [sum(groups[k]) / len(groups[k]) for k in labels]

    # Рисуем график
    plt.figure()
    plt.plot(labels, means)
    plt.title(f"Настроение ({period.capitalize()})")
    plt.xlabel(period.capitalize())
    plt.ylabel("Средний Compound Score")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Сохраняем
    img_fname = os.path.join('images', f'sentiment_{user_id}_{period}.png')
    plt.savefig(img_fname)
    plt.close()
    return img_fname


def get_sentiment_score(text: str) -> float:
    from snownlp import SnowNLP
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
    if re.search(r"[А-Яа-яЁё]", text):
        s = SnowNLP(text)
        return (s.sentiments - 0.5) * 2
    else:
        return _vader.polarity_scores(text)["compound"]


async def sentiment_trend(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          period_type: str, period_count: int):
    """
    period_type: 'days', 'weeks' или 'months'
    period_count: сколько точек на графике
    """
    user_id = update.effective_user.id
    now = datetime.now()

    # 1. Вычисляем границы периода
    if period_type == 'days':
        start_dt = (now - timedelta(days=period_count - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt   = now
    elif period_type == 'weeks':
        monday = now - timedelta(days=now.weekday())
        start_dt = (monday - timedelta(weeks=period_count - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt   = now
    else:  # months
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_dt = first_of_month - relativedelta(months=period_count - 1)
        end_dt   = first_of_month + relativedelta(months=1)

    start_date = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_date   = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 2. Забираем все записи
    entries = get_entries(user_id, start_date, end_date)
    if not entries:
        return await update.message.reply_text("📊 Нет записей для анализа.")

    # 3. Группируем compound-скоры по бинам
    buckets = {}
    for entry in entries:
        # entry = (id, date_str, text, image_paths_str)
        _, date_str, text, _ = entry
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        if period_type == 'days':
            key = dt.strftime("%Y-%m-%d")
        elif period_type == 'weeks':
            iso = dt.isocalendar()  # (year, week_num, weekday)
            key = f"W{iso[1]}-{iso[0]}"
        else:  # months
            key = dt.strftime("%Y-%m")
        score = get_sentiment_score(text or "")
        buckets.setdefault(key, []).append(score)

    # 4. Подготавливаем метки и средние значения
    labels = []
    means  = []
    if period_type == 'days':
        for i in range(period_count):
            day_dt = start_dt + timedelta(days=i)
            lbl = day_dt.strftime("%Y-%m-%d")
            labels.append(day_dt.strftime("%d.%m"))
            vals = buckets.get(lbl, [])
            means.append(sum(vals)/len(vals) if vals else 0)
    elif period_type == 'weeks':
        curr = start_dt
        for _ in range(period_count):
            iso = curr.isocalendar()
            lbl = f"W{iso[1]}-{iso[0]}"
            labels.append(lbl)
            vals = buckets.get(lbl, [])
            means.append(sum(vals)/len(vals) if vals else 0)
            curr += timedelta(weeks=1)
    else:  # months
        curr = start_dt
        for _ in range(period_count):
            lbl = curr.strftime("%Y-%m")
            labels.append(lbl)
            vals = buckets.get(lbl, [])
            means.append(sum(vals)/len(vals) if vals else 0)
            curr += relativedelta(months=1)

    # 5. Строим график
    plt.figure()
    plt.plot(labels, means, marker='o')
    title_map = {'days': '12 дней', 'weeks': '10 недель', 'months': '6 месяцев'}
    plt.title(f"Настроение ({title_map[period_type]})")
    plt.xlabel({'days':'Дата','weeks':'Неделя-Год','months':'Месяц'}[period_type])
    plt.ylabel("Avg Compound Score")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 6. Сохраняем и отправляем
    os.makedirs("images", exist_ok=True)
    img_path = os.path.join("images", f"sentiment_{user_id}_{period_type}.png")
    plt.savefig(img_path)
    plt.close()
    with open(img_path, "rb") as img:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img)

# Обёртки
async def sentiment_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await sentiment_trend(update, context, period_type='days',   period_count=12)

async def sentiment_weeks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await sentiment_trend(update, context, period_type='weeks',  period_count=10)

async def sentiment_months(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await sentiment_trend(update, context, period_type='months', period_count=6)


async def summary_period(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str):
    user_id = update.effective_user.id
    now = datetime.now()

    # 1) Границы периода
    if period == 'week':
        start_dt = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
        end_dt   = (start_dt + timedelta(days=6)).replace(hour=23, minute=59, second=59)
        period_name = 'неделю'
    else:  # 'month'
        start_dt = now.replace(day=1, hour=0, minute=0, second=0)
        nxt = start_dt.replace(day=28) + timedelta(days=4)
        end_dt   = (nxt.replace(day=1) - timedelta(seconds=1)).replace(hour=23, minute=59, second=59)
        period_name = 'месяц'

    start_date = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_date   = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 2) Получаем записи
    entries = get_entries(user_id, start_date, end_date)
    if not entries:
        await update.message.reply_text(f"📄 Нет записей за {period_name}.")
        return

    # 3) Считываем тексты и считаем вероятности настроения
    probs = []
    texts = []
    for _id, _date, entry_text, _imgs in entries:
        if not entry_text:
            continue
        score = get_sentiment_score(entry_text)   # ∈[-1;1]
        prob = (score + 1) / 2                    # ∈[0;1]
        probs.append(prob)
        texts.append(entry_text)

    total = len(probs)
    pos = sum(1 for p in probs if p > 0.6)
    neg = sum(1 for p in probs if p < 0.4)
    neu = total - pos - neg

    # 4) Общее настроение
    if pos > neg:
        mood_label = 'позитивное'
    elif neg > pos:
        mood_label = 'негативное'
    else:
        mood_label = 'нейтральное'

    # 5) Ключевые фразы через YAKE
    full_text = " ".join(texts)
    kw = yake.KeywordExtractor(lan="ru", n=3, top=5)
    keywords = kw.extract_keywords(full_text)
    top_phrases = [phrase for phrase, _ in keywords][:3]

    # 6) Формируем и отправляем резюме
    summary = (
        f"📄 Резюме за {period_name}:\n"
        f"📌 Записей: {total}\n"
        f"✅ Позитивных: {pos}\n"
        f"⚠️ Негативных: {neg}\n"
        f"ℹ️ Нейтральных: {neu}\n"
        f"🔍 Общее настроение: {mood_label}"
    )
    if top_phrases:
        summary += f"\n🔑 Основные темы: {', '.join(top_phrases)}"

    await update.message.reply_text(summary)

# Обёртки для команд
async def summary_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await summary_period(update, context, period='week')

async def summary_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await summary_period(update, context, period='month')

async def callback_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    entry_id = int(query.data.split(":")[1])
    delete_entry_from_db(entry_id)
    # можно дополнительно удалить файлы изображений из images/
    await query.edit_message_text("✅ Запись удалена.")

# Обработчик начала редактирования
async def callback_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    entry_id = int(query.data.split(":")[1])
    context.user_data["edit_id"] = entry_id
    await query.message.reply_text("✏️ Введите новый текст для этой записи (или /cancel для отмены).")
    return WAITING_EDIT

# Приём отредактированного текста
async def receive_edited_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_text = update.message.text.strip()
    entry_id = context.user_data.get("edit_id")
    update_entry_in_db(entry_id, new_text)
    await update.message.reply_text("✅ Текст записи обновлён.")
    return ConversationHandler.END

# Отмена редактирования
async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Редактирование отменено.")
    return ConversationHandler.END

async def stats_daily_trend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import os
    import matplotlib.pyplot as plt
    from datetime import datetime, timedelta
    from database import get_entries

    user_id = update.effective_user.id
    now = datetime.now()

    # 1) Собираем записи за последние 60 дней (чтобы сравнить 30 vs предыдущие 30)
    start_60 = (now - timedelta(days=59)).replace(hour=0, minute=0, second=0, microsecond=0)
    entries = get_entries(
        user_id,
        start_60.strftime("%Y-%m-%d %H:%M:%S"),
        now.strftime("%Y-%m-%d %H:%M:%S")
    )

    # 2) Группируем по дате (только дата YYYY-MM-DD)
    counts_map = {}
    for entry in entries:
        # unpack: entry is (id, date, text, image_paths)
        _, date_str, _, _ = entry
        day = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        counts_map[day] = counts_map.get(day, 0) + 1

    # 3) Готовим списки для последних 30 дней
    labels = []
    values = []
    for i in range(29, -1, -1):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append((now - timedelta(days=i)).strftime("%d.%m"))
        values.append(counts_map.get(d, 0))

    # 4) Считаем общее за текущие и предыдущие 30 дней
    total_current = sum(values)
    total_prev = sum(
        counts_map.get((now - timedelta(days=i)).strftime("%Y-%m-%d"), 0)
        for i in range(30, 60)
    )
    if total_prev:
        change = (total_current - total_prev) / total_prev * 100
        sign = "+" if change >= 0 else ""
        change_str = f"{sign}{change:.0f}%"
    else:
        change_str = "н/д"

    # 5) Отправляем текстовую сводку
    summary = (
        f"📊 Тренд записей за 30 дней:\n"
        f"✏️ Всего: {total_current}\n"
        f"📈 Изменение к предыдущим 30 дням: {change_str}"
    )
    await update.message.reply_text(summary)

    # 6) Строим линейный график
    plt.figure()
    plt.plot(labels, values, marker='o')
    plt.title("Записи за последние 30 дней")
    plt.xlabel("Дата")
    plt.ylabel("Число записей")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 7) Сохраняем и отправляем картинку
    os.makedirs("images", exist_ok=True)
    img_path = f"images/stats_30days_{user_id}.png"
    plt.savefig(img_path)
    plt.close()

    with open(img_path, "rb") as img:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img)