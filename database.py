import sqlite3
import os

# Подключение к базе данных
DB_FILE = "diary.db"
db_conn = sqlite3.connect(DB_FILE, check_same_thread=False)
db_cursor = db_conn.cursor()

# Создание таблицы, если её нет
def initialize_db():
    db_cursor.execute('''
    CREATE TABLE IF NOT EXISTS diary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        entry TEXT,
        image_path TEXT
    )
    ''')
    db_conn.commit()

# Добавление записи в базу данных
def add_entry_to_db(user_id, date, entry, image_path):
    db_cursor.execute(
        "INSERT INTO diary (user_id, date, entry, image_path) VALUES (?, ?, ?, ?)",
        (user_id, date, entry, image_path)
    )
    db_conn.commit()

# Получение записей по фильтру времени
def get_entries(user_id, start_date=None, end_date=None):
    if start_date and end_date:
        query = "SELECT date, entry, image_path FROM diary WHERE user_id = ? AND date >= ? AND date < ? ORDER BY date ASC"
        db_cursor.execute(query, (user_id, start_date, end_date))
    elif start_date:
        query = "SELECT date, entry, image_path FROM diary WHERE user_id = ? AND date >= ? ORDER BY date ASC"
        db_cursor.execute(query, (user_id, start_date))
    else:
        query = "SELECT date, entry, image_path FROM diary WHERE user_id = ? ORDER BY date ASC"
        db_cursor.execute(query, (user_id,))
    return db_cursor.fetchall()

# Инициализация базы данных
initialize_db()