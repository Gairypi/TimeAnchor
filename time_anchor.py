# time_anchor.py
import sys
import os
import time
import sqlite3
import json
import random
import threading
from collections import OrderedDict
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QDialog, QTreeWidget, QTreeWidgetItem, QLineEdit, QComboBox,
    QRadioButton, QButtonGroup, QCheckBox, QFileDialog, QMessageBox, QGroupBox,
    QScrollArea, QFrame, QSizePolicy, QInputDialog, QTabWidget, QLCDNumber, QGridLayout, QMenu, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QTime, QSize, QRect, QPoint, QUrl
from PyQt5.QtGui import (
    QColor, QPalette, QFont, QPixmap, QMovie, QPainter, QBrush, QPen,
    QIcon, QFontDatabase
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

from utils import normalize_time, get_data_folder_path, get_db_path
from notification import NotificationWindow
from timetable_editor import TimetableEditor
from timer_window import TimerWindow

# Глобальная блокировка для работы с БД
db_lock = threading.Lock()


class TimeOverlay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TimeAnchor PRO")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Определение путей
        self.data_folder_path = Path.home() / "Documents" / "TimeAnchor"
        self.data_folder_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_folder_path / "timetable.db"
        self.settings_path = self.data_folder_path / "settings.json"

        # Настройки по умолчанию
        self.settings = {
            "sound_file": None,
            "active_timetable": "Основное",
            "notification_enabled": True,
            "notification_before_mins": 3,
            "notification_duration_secs": 10,
            "sound_before_file": None,
            "sound_now_file": None,
            "timer_sound_file": None,
            "theme": "dark",
            "opacity": 0.6  # Изменено на 60% прозрачность
        }

        # Загрузка настроек
        self.load_settings()
        self.create_notification_resources()

        # Инициализация БД
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.create_database()
        self.load_timetable()

        # Медиаплееры для звуков
        self.media_player = QMediaPlayer()  # Для основного звука
        self.notification_player = QMediaPlayer()  # Для уведомлений
        self.timer_player = QMediaPlayer()  # Для таймера

        # Основной интерфейс
        self.init_ui()
        self.setup_hotkeys()

        self.adjustSize()
        self.move_to_corner()

        # Таймер для проверки расписания
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_timetable_loop)
        self.timer.start(2000)  # Каждые 2 секунды

        # Переменные для уведомлений
        self.last_notified_before = None
        self.last_notified_now = None
        self.current_day = datetime.now().day  # Для отслеживания смены дня

        # Позиционирование будет в showEvent

        # Добавляем переменные для дочерних окон
        self.editor = None
        self.timer_win = None
        self.task_window = None

    def move_to_corner(self):
        """Позиционирует окно в правом верхнем углу активного экрана"""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geometry.width() - self.width() - 20, 20)

    def showEvent(self, event):
        """Позиционирование окна при показе"""
        super().showEvent(event)
        screen_geometry = QApplication.desktop().availableGeometry()
        self.move(screen_geometry.width() - self.width() - 20, 50)

    def init_ui(self):
        """Инициализация пользовательского интерфейса с подложкой"""
        # Создаем главный контейнер
        main_container = QWidget(self)
        main_container.setObjectName("MainContainer")
        main_container.setGeometry(0, 0, 500, 350)

        # Создаем полупрозрачную подложку
        self.background = QWidget(main_container)
        self.background.setObjectName("Background")
        self.background.setGeometry(0, 0, main_container.width(), main_container.height())

        # Создаем интерфейс поверх подложки
        self.create_overlay_ui(main_container)

        # Применяем стили
        self.apply_styles()
        self.setCentralWidget(main_container)

        # Устанавливаем обработчик изменения размера
        main_container.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Обработка изменения размера окна"""
        if event.type() == event.Resize:
            # Обновляем размер подложки при изменении размера окна
            self.background.setGeometry(0, 0, obj.width(), obj.height())
        return super().eventFilter(obj, event)

    def create_overlay_ui(self, parent):
        """Создает элементы интерфейса поверх подложки"""
        # Главный вертикальный лейаут
        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # Область для перетаскивания окна
        self.drag_widget = QWidget()
        self.drag_widget.setFixedHeight(5)
        self.drag_widget.setStyleSheet("background-color: transparent;")

        # Верхняя панель с кнопками управления
        top_button_frame = QWidget()
        top_button_layout = QHBoxLayout(top_button_frame)
        top_button_layout.setAlignment(Qt.AlignRight)
        top_button_layout.setContentsMargins(0, 0, 0, 0)

        # Кнопка таймера
        self.timer_button = QPushButton("⏱")
        self.timer_button.setFixedSize(30, 30)
        self.timer_button.setStyleSheet(self.get_button_style())
        self.timer_button.clicked.connect(self.open_timer_window)

        # Кнопка задач
        self.task_button = QPushButton("📋")
        self.task_button.setFixedSize(30, 30)
        self.task_button.setStyleSheet(self.get_button_style())
        self.task_button.clicked.connect(self.open_task_window)

        # Кнопка настроек
        self.settings_button = QPushButton("⚙")
        self.settings_button.setFixedSize(30, 30)
        self.settings_button.setStyleSheet(self.get_button_style())
        self.settings_button.clicked.connect(self.open_timetable_editor)

        # Добавляем кнопки на панель
        top_button_layout.addStretch()
        top_button_layout.addWidget(self.timer_button)
        top_button_layout.addWidget(self.task_button)
        top_button_layout.addWidget(self.settings_button)

        # Основной лейбл с задачей
        self.task_label = QLabel("← Инициализация →")
        self.task_label.setAlignment(Qt.AlignCenter)
        self.task_label.setFont(QFont("Consolas", 18))
        self.task_label.setStyleSheet("color: #00FF00; background-color: transparent;")

        # Время начала и окончания
        time_frame = QWidget()
        time_layout = QHBoxLayout(time_frame)
        time_layout.setContentsMargins(0, 0, 0, 0)

        self.time_start_label = QLabel("")
        self.time_start_label.setFont(QFont("Consolas", 10))
        self.time_start_label.setStyleSheet("color: gray;")

        self.time_end_label = QLabel("")
        self.time_end_label.setFont(QFont("Consolas", 10))
        self.time_end_label.setStyleSheet("color: gray;")
        self.time_end_label.setAlignment(Qt.AlignRight)

        time_layout.addWidget(self.time_start_label)
        time_layout.addStretch()
        time_layout.addWidget(self.time_end_label)

        # Следующая задача
        self.next_task_label = QLabel("")
        self.next_task_label.setFont(QFont("Consolas", 10))
        self.next_task_label.setStyleSheet("color: gray;")
        self.next_task_label.setAlignment(Qt.AlignRight)
        self.next_task_label.setWordWrap(True)

        # Сборка основного интерфейса
        main_layout.addWidget(self.drag_widget)
        main_layout.addWidget(top_button_frame)
        main_layout.addWidget(self.task_label)
        main_layout.addWidget(time_frame)
        main_layout.addWidget(self.next_task_label)

        # Устанавливаем минимальные размеры
        self.setMinimumSize(200, 130)

    def apply_styles(self):
        """Применяет стили к элементам интерфейса"""
        # Определяем цвета в зависимости от темы
        if self.settings["theme"] == "dark":
            bg_color = f"rgba(20, 20, 20, {int(self.settings['opacity'] * 255)})"
            text_color = "#EEE"
            button_hover = "#555"
            button_pressed = "#666"
        else:
            bg_color = f"rgba(240, 240, 240, {int(self.settings['opacity'] * 255)})"
            text_color = "#333"
            button_hover = "#d0d0d0"
            button_pressed = "#c0c0c0"

        # Устанавливаем стили
        self.setStyleSheet(f"""
            #Background {{
                background-color: {bg_color};
                border-radius: 10px;
                border: 1px solid #444;
            }}
            #MainContainer {{
                background: transparent;
            }}
            QPushButton {{
                background-color: #444;
                color: {text_color};
                border: none;
                border-radius: 15px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:pressed {{
                background-color: {button_pressed};
            }}
            #CloseButton {{
                background-color: #ff5555;
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 16px;
            }}
            #CloseButton:hover {{
                background-color: #ff7777;
            }}
            #CloseButton:pressed {{
                background-color: #ff3333;
            }}
            QLabel {{
                color: {text_color};
                background-color: transparent;
            }}
        """)

        # Дополнительные стили для светлой темы
        if self.settings["theme"] == "light":
            self.time_start_label.setStyleSheet("color: #333;")
            self.time_end_label.setStyleSheet("color: #333;")
            self.next_task_label.setStyleSheet("color: #333;")

    def get_button_style(self):
        if self.settings["theme"] == "dark":
            return """
                QPushButton {
                    background-color: #333;
                    color: #AAA;
                    border: none;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background-color: #444;
                    color: #FFF;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #EEE;
                    color: #555;
                    border: none;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background-color: #DDD;
                    color: #000;
                }
            """

    def apply_theme(self):
        # Установка цвета текста для светлой темы
        if self.settings["theme"] == "light":
            self.time_start_label.setStyleSheet("color: #333;")
            self.time_end_label.setStyleSheet("color: #333;")
            self.next_task_label.setStyleSheet("color: #333;")

    def create_database(self):
        with db_lock:
            cursor = self.conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS timetable (
                                id INTEGER PRIMARY KEY,
                                time TEXT NOT NULL,
                                task TEXT,
                                color TEXT,
                                timetable_name TEXT,
                                UNIQUE(time, timetable_name))''')
            self.conn.commit()

    def load_settings(self):
        try:
            if self.settings_path.exists():
                with open(self.settings_path, "r") as f:
                    self.settings.update(json.load(f))
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")

    def save_settings(self):
        try:
            with open(self.settings_path, "w") as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def create_notification_resources(self):
        # Создание папок для изображений
        images_before = self.data_folder_path / "images" / "before"
        images_now = self.data_folder_path / "images" / "now"
        images_before.mkdir(parents=True, exist_ok=True)
        images_now.mkdir(parents=True, exist_ok=True)

        # Создание текстовых файлов
        before_txt = self.data_folder_path / "before.txt"
        now_txt = self.data_folder_path / "now.txt"

        if not before_txt.exists():
            with open(before_txt, 'w', encoding='utf-8') as f:
                f.write('"3 минутыыыы ^^";\n"Пару минут осталось!";')

        if not now_txt.exists():
            with open(now_txt, 'w', encoding='utf-8') as f:
                f.write('"Уже началось!";\n"Действуй! :)";')

    def load_timetable(self):
        self.timetable = OrderedDict()
        with db_lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT time, task, color, timetable_name FROM timetable WHERE timetable_name = ? ORDER BY time",
                (self.settings["active_timetable"],))

            for time_str, task, color, timetable_name in cursor.fetchall():
                self.timetable[time_str] = (task, color)

    def setup_hotkeys(self):
        # В PyQt5 глобальные горячие клавиши сложнее реализовать
        # Для простоты оставим обработку внутри приложения
        pass

    def time_str_to_minutes(self, time_str):
        t = datetime.strptime(time_str, "%H:%M").time()
        return t.hour * 60 + t.minute

    def get_current_task(self):
        try:
            """Полностью переработанный метод для поддержки задач после полуночи"""
            now = datetime.now()
            current_time = now.time()
            current_min = current_time.hour * 60 + current_time.minute

            # Если расписание пустое
            if not self.timetable:
                return ("Фокус на сводных целях", "#FFFFFF"), None, None, None

            # Получим список временных меток и преобразуем в минуты
            times = list(self.timetable.keys())
            sorted_times = sorted(times, key=self.time_str_to_minutes)

            # Проверим, есть ли задачи после полуночи
            has_midnight_task = any(self.time_str_to_minutes(t) < 360 for t in sorted_times)

            # Если есть задачи после полуночи и текущее время после полуночи
            if has_midnight_task and current_time.hour < 6:
                # Добавим 24 часа к задачам после полуночи
                adjusted_times = [
                    (t, self.time_str_to_minutes(t) + (1440 if self.time_str_to_minutes(t) < 360 else 0))
                    for t in sorted_times
                ]
            else:
                adjusted_times = [(t, self.time_str_to_minutes(t)) for t in sorted_times]

            # Сортируем по скорректированному времени
            adjusted_times.sort(key=lambda x: x[1])
            sorted_times = [t[0] for t in adjusted_times]

            # Определим текущую задачу
            for i in range(len(sorted_times)):
                start_time = sorted_times[i]
                start_min = self.time_str_to_minutes(start_time)

                # Корректировка для задач после полуночи
                if has_midnight_task and start_min < 360 and current_time.hour < 6:
                    start_min += 1440

                if i == len(sorted_times) - 1:
                    # Последняя задача в расписании
                    task_data = self.timetable[start_time]
                    return task_data, start_time, None, None

                next_time = sorted_times[i + 1]
                next_min = self.time_str_to_minutes(next_time)

                # Корректировка для задач после полуночи
                if has_midnight_task and next_min < 360 and current_time.hour < 6:
                    next_min += 1440

                if start_min <= current_min < next_min:
                    task_data = self.timetable[start_time]
                    next_task_data = self.timetable[next_time]
                    return task_data, start_time, next_time, next_task_data

            # Если не нашли подходящей задачи (текущее время раньше первой задачи)
            first_time = sorted_times[0]
            task_data = self.timetable[first_time]


            for time_str, (task, color) in self.timetable.items():
                print(f"  {time_str}: {task}")

            return (task, color), start_time, next_time

        except Exception as e:
            print(f"Ошибка в get_current_task: {e}")
        return ("Ошибка", "#FF0000"), None, None, None

    def get_notification_text(self, text_file):
        """Возвращает случайную строку из файла (обновленная версия)"""
        if not text_file or not Path(text_file).is_file():
            return "Напоминание"

        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                # Убираем обработку кавычек - теперь файлы хранятся без них
                return random.choice(lines) if lines else "Напоминание"
        except Exception as e:
            print(f"Ошибка чтения текста: {e}")
            return "Напоминание"

    def delete_timetable(self, name):
        if name == "Основное":
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить основное расписание")
            return

        if QMessageBox.question(self, "Подтверждение",
                                f"Вы уверены, что хотите удалить расписание '{name}'?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:

            # Удаление из базы данных
            with db_lock:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM timetable WHERE timetable_name = ?", (name,))
                self.conn.commit()

            # Обновление интерфейса
            self.timetable_names.remove(name)

            # Если удаляем активное расписание, переключаемся на первое доступное
            if self.selected_timetable == name:
                self.selected_timetable = self.timetable_names[0] if self.timetable_names else "Основное"
                self.main_app.settings["active_timetable"] = self.selected_timetable
                self.main_app.save_settings()
                self.load_data()

            self.render_timetable_tabs()
            self.render_active_timetable_radio()

    def update_overlay(self, task, color, start_time=None, end_time=None, next_task_data=None, play_sound=False):
        if task:
            self.task_label.setText(f"← {task} →")
            self.task_label.setStyleSheet(f"color: {color}; background-color: transparent;")
        else:
            self.task_label.setText("← До начала дня →")
            self.task_label.setStyleSheet("color: #AAAAAA; background-color: transparent;")

        self.time_start_label.setText(start_time if start_time else "")
        self.time_end_label.setText(end_time if end_time else "")

        if next_task_data:
            next_task, _ = next_task_data
            self.next_task_label.setText(next_task)
        else:
            self.next_task_label.setText("")

        self.adjustSize()

        if play_sound and self.settings["sound_file"]:
            try:
                # Остановить предыдущий звук
                if self.media_player.state() == QMediaPlayer.PlayingState:
                    self.media_player.stop()

                media_content = QMediaContent(QUrl.fromLocalFile(self.settings["sound_file"]))
                self.media_player.setMedia(media_content)
                self.media_player.play()
            except Exception as e:
                print(f"Ошибка воспроизведения звука: {e}")

    def check_timetable_loop(self):
        try:
            now = datetime.now()
            # Сброс уведомлений при смене дня
            if now.day != self.current_day:
                self.last_notified_before = None
                self.last_notified_now = None
                self.current_day = now.day

            current_time = now.time()
            now_minutes = current_time.hour * 60 + current_time.minute

            # Получаем текущую задачу
            (task, color), start_time, next_time, next_task_data = self.get_current_task()

            # Проверка для уведомлений
            if self.settings["notification_enabled"]:
                # Для before-уведомления (за N минут)
                if next_time:
                    next_time_obj = datetime.strptime(next_time, "%H:%M").time()
                    next_minutes = next_time_obj.hour * 60 + next_time_obj.minute

                    # Коррекция для событий после полуночи
                    if current_time.hour >= 18 and next_time_obj.hour < 6:
                        next_minutes += 1440  # Добавляем сутки в минутах

                    time_diff = next_minutes - now_minutes

                    # Проверка на интервал времени до события
                    if 0 <= time_diff <= self.settings["notification_before_mins"]:
                        if next_time != self.last_notified_before:
                            task_name = next_task_data[0] if next_task_data else "Следующее событие"
                            self.show_notification("before", task_name)
                            self.last_notified_before = next_time

                # Для now-уведомления (точное время начала)
                if start_time:
                    task_time = datetime.strptime(start_time, "%H:%M").time()
                    if (task_time.hour == current_time.hour and
                            task_time.minute == current_time.minute and
                            start_time != self.last_notified_now):
                        self.show_notification("now", task)
                        self.last_notified_now = start_time

            # Обновляем интерфейс
            play_sound = self.time_start_label.text() != (start_time if start_time else "")
            self.update_overlay(task, color, start_time, next_time, next_task_data, play_sound)

        except Exception as e:
            print(f"Ошибка в check_timetable_loop: {e}")

    def show_notification(self, notif_type, task_name):
        if notif_type == "before":
            text_file = self.data_folder_path / "before.txt"
            sound_file = self.settings["sound_before_file"]
        else:
            text_file = self.data_folder_path / "now.txt"
            sound_file = self.settings["sound_now_file"]

        duration = self.settings["notification_duration_secs"]

        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: сохраняем ссылку на уведомление
        self.notification = NotificationWindow(
            text_file,
            duration,
            task_name,
            self.settings["theme"]
        )
        self.notification.show()

        # Воспроизведение звука
        if sound_file:
            try:
                # Остановить предыдущий звук
                if self.notification_player.state() == QMediaPlayer.PlayingState:
                    self.notification_player.stop()

                media_content = QMediaContent(QUrl.fromLocalFile(sound_file))
                self.notification_player.setMedia(media_content)
                self.notification_player.play()
            except Exception as e:
                print(f"Ошибка воспроизведения звука: {e}")

    def open_task_window(self):
        """Открывает окно задач с корректным позиционированием"""
        from task import TimeAnchorApp as TaskApp
        if self.task_window is None or not self.task_window.isVisible():
            self.task_window = TaskApp()

        # Позиционируем рядом с главным окном
        main_pos = self.mapToGlobal(QPoint(0, 0))
        self.task_window.move(main_pos.x() - self.task_window.width() - 10, main_pos.y())

        self.task_window.show()
        self.task_window.raise_()
        self.task_window.activateWindow()

    def open_timetable_editor(self):
        # Если окно уже создано, просто показываем его
        if self.editor is None:
            self.editor = TimetableEditor(self)
            self.editor.show()
            self.hide()
        else:
            self.editor.show()
            self.editor.activateWindow()

    def open_timer_window(self):
        # Если окно уже создано, просто показываем его
        if self.timer_win is None:
            self.timer_win = TimerWindow(self)
            self.timer_win.show()
        else:
            self.timer_win.show()
            self.timer_win.activateWindow()

    def closeEvent(self, event):
        """Закрывает все дочерние окна при закрытии"""
        if self.editor and self.editor.isVisible():
            self.editor.close()
        if self.timer_win and self.timer_win.isVisible():
            self.timer_win.close()
        if self.task_window and self.task_window.isVisible():
            self.task_window.close()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.drag_widget.geometry().contains(event.pos()):
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'old_pos'):
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()
