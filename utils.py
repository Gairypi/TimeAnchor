# utils.py
import sqlite3
from pathlib import Path


def normalize_time(time_str):
    """Улучшенная нормализация времени"""
    try:
        # Поддержка форматов: "H:M", "HH:MM", "H.M", "H M"
        if ':' in time_str:
            parts = time_str.split(':')
        elif '.' in time_str:
            parts = time_str.split('.')
        elif ' ' in time_str:
            parts = time_str.split()
        else:
            # Попробуем разбить по последним 2 цифрам
            if len(time_str) > 2:
                parts = [time_str[:-2], time_str[-2:]]
            else:
                return None

        # Обработка часов и минут
        hours = int(parts[0].strip())
        minutes = int(parts[1].strip()) if len(parts) > 1 else 0

        # Коррекция значений
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            return None

        return f"{hours:02d}:{minutes:02d}"
    except:
        return None


def get_data_folder_path():
    """Возвращает путь к папке данных приложения"""
    path = Path.home() / "Documents" / "TimeAnchor"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path():
    """Возвращает путь к базе данных"""
    return get_data_folder_path() / "timetable.db"


def create_demo_data(db_path):
    """Создает демо-данные, если база пуста"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS timetable (id INTEGER PRIMARY KEY, time TEXT NOT NULL, task TEXT, color TEXT, timetable_name TEXT, UNIQUE(time, timetable_name))")

    cursor.execute("SELECT COUNT(*) FROM timetable")
    if cursor.fetchone()[0] == 0:
        demo_data = [("06:00", "Подъем", "#3498db", "Основное")]
        cursor.executemany(
            "INSERT INTO timetable (time, task, color, timetable_name) VALUES (?, ?, ?, ?)",
            demo_data
        )
        conn.commit()
    conn.close()