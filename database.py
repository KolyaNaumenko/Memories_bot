import sqlite3
import os

# Подключение к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'diary.db')
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
    )''')
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
        q = ("SELECT id, date, entry, image_path FROM diary "
             "WHERE user_id=? AND date>=? AND date<? ORDER BY date ASC")
        db_cursor.execute(q, (user_id, start_date, end_date))
    elif start_date:
        q = ("SELECT id, date, entry, image_path FROM diary "
             "WHERE user_id=? AND date>=? ORDER BY date ASC")
        db_cursor.execute(q, (user_id, start_date))
    else:
        q = ("SELECT id, date, entry, image_path FROM diary "
             "WHERE user_id=? ORDER BY date ASC")
        db_cursor.execute(q, (user_id,))
    return db_cursor.fetchall()

# Удаление записи из базы данных
def delete_entry_from_db(entry_id):
    db_cursor.execute("DELETE FROM diary WHERE id=?", (entry_id,))
    db_conn.commit()

def update_entry_in_db(entry_id, new_text):
    db_cursor.execute("UPDATE diary SET entry=? WHERE id=?", (new_text, entry_id))
    db_conn.commit()

# Создание таблицы для целей
def initialize_goals_table():
    db_cursor.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        goal_text TEXT,
        deadline TEXT,
        status TEXT DEFAULT 'in_progress',
        created_at DATETIME DEFAULT (datetime('now'))
    )
    ''')
    db_conn.commit()

# Добавление цели
def add_goal_to_db(user_id, goal_text, deadline):
    db_cursor.execute(
        "INSERT INTO goals (user_id, goal_text, deadline, created_at) VALUES (?, ?, ?, datetime('now'))",
        (user_id, goal_text, deadline)
    )
    db_conn.commit()

# Получение всех целей пользователя
def get_goals_from_db(user_id, status=None):
    if status:
        db_cursor.execute(
            "SELECT id, goal_text, deadline, status FROM goals WHERE user_id = ? AND status = ? ORDER BY deadline ASC",
            (user_id, status)
        )
    else:
        db_cursor.execute(
            "SELECT id, goal_text, deadline, status FROM goals WHERE user_id = ? ORDER BY deadline ASC",
            (user_id,)
        )
    return db_cursor.fetchall()

# Обновление статуса цели
def update_goal_status_in_db(goal_id, status):
    db_cursor.execute(
        "UPDATE goals SET status = ? WHERE id = ?",
        (status, goal_id)
    )
    db_conn.commit()

# Удаление цели
def delete_goal_from_db(goal_id):
    db_cursor.execute(
        "DELETE FROM goals WHERE id = ?",
        (goal_id,)
    )
    db_conn.commit()

def get_random_entry(user_id):
    """
    Возвращает кортеж (date, entry, image_path) одной случайной записи пользователя
    или None, если записей нет.
    """
    db_cursor.execute(
        "SELECT date, entry, image_path FROM diary "
        "WHERE user_id = ? ORDER BY RANDOM() LIMIT 1",
        (user_id,)
    )
    return db_cursor.fetchone()

def search_entries(user_id, keyword):
    """
    Ищет в тексте записей пользователя все, где entry LIKE %keyword%
    """
    pattern = f"%{keyword}%"
    db_cursor.execute(
        "SELECT date, entry, image_path FROM diary "
        "WHERE user_id = ? AND entry LIKE ? "
        "ORDER BY date ASC",
        (user_id, pattern)
    )
    return db_cursor.fetchall()
# Инициализация таблиц
initialize_db()
initialize_goals_table()
