# timetable_editor.py
import os
import sqlite3
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QGroupBox, QLabel, QRadioButton, QButtonGroup, QCheckBox, QMessageBox,
    QInputDialog, QFileDialog, QMenu, QGridLayout, QColorDialog, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from shared import db_lock
from notification_editor import NotificationEditor
from utils import normalize_time, get_data_folder_path, get_db_path


class TimetableEditor(QMainWindow):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.setWindowTitle("Редактор расписания")
        self.setGeometry(200, 200, 800, 650)

        # Определение путей
        self.data_folder_path = Path.home() / "Documents" / "TimeAnchor"
        self.db_path = self.data_folder_path / "timetable.db"

        # Подключение к БД
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.create_database()

        # Инициализация данных
        self.current_timetable = OrderedDict()
        self.timetable_names = self.get_timetable_names()
        self.selected_timetable = self.main_app.settings["active_timetable"]
        self.load_data()

        # Инициализация интерфейса
        self.init_ui()
        self.apply_theme()

        self.add_bottom_buttons()

    def add_bottom_buttons(self):
        """Добавляет кнопки в нижнюю часть окна"""
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Кнопка помощи
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(25, 25)
        self.help_button.clicked.connect(self.show_help)

        # Кнопка уведомлений
        self.notif_button = QPushButton("Уведомления")
        self.notif_button.clicked.connect(self.open_notification_editor)

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.close_editor)

        bottom_layout.addWidget(self.help_button)
        bottom_layout.addWidget(self.notif_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_button, alignment=Qt.AlignCenter)

        # Добавляем в главный layout
        self.centralWidget().layout().addWidget(bottom_widget)

    def show_help(self):
        """Показывает инструкцию по использованию"""
        help_text = """
        <b>Инструкция по работе с редактором расписания</b>
        <p>1. Для добавления новой задачи:</p>
        <ul>
            <li>Выберите время с помощью кнопок часов и минут</li>
            <li>Введите описание задачи</li>
            <li>Нажмите "Добавить"</li>
        </ul>
        <p>2. Для редактирования существующей задачи:</p>
        <ul>
            <li>Выберите задачу в списке</li>
            <li>Внесите изменения в поля</li>
            <li>Нажмите "Обновить"</li>
        </ul>
        <p>3. Для удаления задачи:</p>
        <ul>
            <li>Выберите задачу в списке</li>
            <li>Нажмите "Удалить"</li>
        </ul>
        <p>4. Управление расписаниями:</p>
        <ul>
            <li>Используйте вкладки для переключения между расписаниями</li>
            <li>Кнопка "+" создает новое расписание</li>
            <li>ПКМ на вкладке - переименовать/удалить</li>
        </ul>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("Справка")
        msg.setTextFormat(Qt.RichText)
        msg.setText(help_text)
        msg.exec_()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)

        # Панель вкладок расписаний
        self.tab_frame = QWidget()
        tab_layout = QHBoxLayout(self.tab_frame)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        self.add_tab_button = QPushButton("+")
        self.add_tab_button.setFixedSize(30, 30)
        self.add_tab_button.clicked.connect(self.add_timetable)
        tab_layout.addWidget(self.add_tab_button)

        self.tab_buttons = {}
        self.render_timetable_tabs()

        # Таблица с расписанием
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Время", "Задача", "Цвет", "Расписание"])
        self.tree.setColumnWidth(0, 80)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 100)
        self.tree.itemClicked.connect(self.select_item)

        # Панель редактирования
        edit_frame = QGroupBox("Редактирование задачи")
        edit_layout = QHBoxLayout(edit_frame)

        # Инициализируем time_edit перед вызовом create_time_selector
        self.time_edit = QWidget()  # Заглушка для избежания ошибки
        self.create_time_selector(edit_frame)

        self.task_edit = QLineEdit()
        self.task_edit.setPlaceholderText("Описание задачи")

        # Палитра цветов
        color_container = QWidget()
        color_layout = QHBoxLayout(color_container)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(5)

        self.color_edit = QLineEdit("#FFFFFF")
        self.color_edit.setPlaceholderText("Цвет в формате #RRGGBB")
        self.color_edit.textChanged.connect(self.update_color_display)

        self.color_picker_btn = QPushButton("🎨")
        self.color_picker_btn.setFixedSize(30, 30)
        self.color_picker_btn.setStyleSheet("font-size: 16px;")
        self.color_picker_btn.clicked.connect(self.open_color_dialog)
        self.color_picker_btn.setToolTip("Выбрать цвет")

        self.color_display = QLabel()
        self.color_display.setFixedSize(24, 24)
        self.color_display.setStyleSheet("background-color: #FFFFFF; border: 1px solid black;")

        color_layout.addWidget(self.color_edit)
        color_layout.addWidget(self.color_picker_btn)
        color_layout.addWidget(self.color_display)

        # Кнопки управления
        self.add_button = QPushButton("Добавить")
        self.add_button.clicked.connect(self.add_new_item)

        self.update_button = QPushButton("Обновить")
        self.update_button.setEnabled(False)
        self.update_button.clicked.connect(self.update_item)

        self.delete_button = QPushButton("Удалить")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.remove_item)

        # Сборка панели редактирования
        edit_layout.addWidget(QLabel("Время:"))
        edit_layout.addWidget(self.time_edit)  # Используем созданный виджет
        edit_layout.addWidget(QLabel("Задача:"))
        edit_layout.addWidget(self.task_edit)
        edit_layout.addWidget(QLabel("Цвет:"))
        edit_layout.addWidget(color_container)
        edit_layout.addWidget(self.add_button)
        edit_layout.addWidget(self.update_button)
        edit_layout.addWidget(self.delete_button)

        # Выбор активного расписания
        self.active_frame = QGroupBox("Активное расписание")
        active_layout = QHBoxLayout(self.active_frame)

        self.active_buttons = QButtonGroup()
        self.render_active_timetable_radio()

        # Сборка основного интерфейса
        main_layout.addWidget(self.tab_frame)
        main_layout.addWidget(self.tree)
        main_layout.addWidget(edit_frame)
        main_layout.addWidget(self.active_frame)

        self.setCentralWidget(main_widget)

        # Уменьшаем количество запросов к БД
        self.load_data()
        self.render_timetable()

    def create_time_selector(self, parent):
        """Создает виджет для выбора времени"""
        time_selector = QWidget(parent)
        time_layout = QHBoxLayout(time_selector)
        time_layout.setContentsMargins(0, 0, 0, 0)

        # Выбор часов
        self.hour_combo = QComboBox()
        self.hour_combo.addItems([f"{i:02d}" for i in range(24)])

        # Выбор минут
        self.minute_combo = QComboBox()
        self.minute_combo.addItems([f"{i:02d}" for i in range(0, 60, 5)])  # С шагом 5 минут

        # Метки
        hour_label = QLabel("Часы:")
        minute_label = QLabel("Минуты:")
        colon_label = QLabel(":")

        time_layout.addWidget(hour_label)
        time_layout.addWidget(self.hour_combo)
        time_layout.addWidget(colon_label)
        time_layout.addWidget(minute_label)
        time_layout.addWidget(self.minute_combo)

        # Сохраняем виджет как time_edit
        self.time_edit = time_selector

    def select_item(self, item, column):
        """Обработка выбора элемента с новым виджетом времени"""
        time_str = item.text(0)
        if ':' in time_str:
            hours, minutes = time_str.split(':')
            self.hour_combo.setCurrentText(hours)
            self.minute_combo.setCurrentText(minutes)

        task = item.text(1)
        color = item.text(2)

        self.task_edit.setText(task)
        self.color_edit.setText(color)
        self.update_color_display()  # обновляем индикатор цвета

        self.update_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def update_item(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        old_time = item.text(0)

        # Получаем новое время из комбобоксов
        hours = self.hour_combo.currentText()
        minutes = self.minute_combo.currentText()
        new_time = f"{hours}:{minutes}"

        new_task = self.task_edit.text()
        new_color = self.color_edit.text()

        if not new_task:
            QMessageBox.warning(self, "Ошибка", "Задача обязательна для заполнения")
            return

        # Проверка на конфликт времени (если время изменилось)
        if old_time != new_time and new_time in self.current_timetable:
            QMessageBox.warning(self, "Ошибка", "Время уже существует в текущем расписании")
            return

        # Если изменилось время
        if old_time != new_time:
            # Перемещаем запись
            task, color = self.current_timetable[old_time]
            self.current_timetable[new_time] = (new_task, new_color)
            del self.current_timetable[old_time]
        else:
            # Обновляем существующую запись
            self.current_timetable[old_time] = (new_task, new_color)

        if not QColor(new_color).isValid():
            QMessageBox.warning(self, "Ошибка", "Неверный формат цвета. Используйте #RRGGBB")
            return

        self.save_data()
        self.render_timetable()

        # Сбрасываем выделение
        self.tree.clearSelection()
        self.update_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def apply_theme(self):
        theme = self.main_app.settings["theme"]
        if theme == "dark":
            style = """
                QMainWindow {
                background-color: rgba(45, 45, 45, 220);
                border: none;
                }
                QWidget {
                    background-color: #2d2d2d;
                    color: #EEE;
                }
                QTreeWidget {
                    background-color: #333;
                    color: #EEE;
                    alternate-background-color: #3a3a3a;
                }
                QHeaderView::section {
                    background-color: #444;
                    color: #EEE;
                    padding: 4px;
                    border: 1px solid #555;
                }
                QGroupBox {
                    border: 1px solid #555;
                    border-radius: 5px;
                    margin-top: 1ex;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                    background-color: transparent;
                    color: #EEE;
                }
                QLineEdit, QComboBox {
                    background-color: #333;
                    color: #EEE;
                    border: 1px solid #555;
                    padding: 3px;
                    border-radius: 3px;
                }
                QPushButton {
                    background-color: #444;
                    color: #EEE;
                    border: 1px solid #555;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #555;
                }
                QPushButton:pressed {
                    background-color: #666;
                }
            """
        else:
            style = """
                QMainWindow {
                background-color: rgba(240, 240, 240, 220);
                border: none;
                }
                QWidget {
                    background-color: #f0f0f0;
                    color: #333;
                }
                QTreeWidget {
                    background-color: #FFF;
                    color: #333;
                    alternate-background-color: #f8f8f8;
                }
                QHeaderView::section {
                    background-color: #e0e0e0;
                    color: #333;
                    padding: 4px;
                    border: 1px solid #CCC;
                }
                QGroupBox {
                    border: 1px solid #CCC;
                    border-radius: 5px;
                    margin-top: 1ex;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                    background-color: transparent;
                    color: #333;
                }
                QLineEdit, QComboBox {
                    background-color: #FFF;
                    color: #333;
                    border: 1px solid #CCC;
                    padding: 3px;
                    border-radius: 3px;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    color: #333;
                    border: 1px solid #CCC;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:pressed {
                    background-color: #c0c0c0;
                }
            """

        self.setStyleSheet(style)

    def load_data(self):
        self.current_timetable = OrderedDict()
        try:
            with db_lock:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT time, task, color, timetable_name FROM timetable WHERE timetable_name = ? ORDER BY time",
                    (self.selected_timetable,))

                for time_str, task, color, timetable_name in cursor.fetchall():
                    self.current_timetable[time_str] = (task, color)
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            # Создаем пустое расписание если возникла ошибка
            self.current_timetable = OrderedDict()

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

    def get_timetable_names(self):
        with db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT timetable_name FROM timetable")
            return [row[0] for row in cursor.fetchall()]

    def render_timetable_tabs(self):
        # Очистка старых кнопок
        for i in range(self.tab_frame.layout().count() - 1, 0, -1):
            widget = self.tab_frame.layout().itemAt(i).widget()
            if widget and widget != self.add_tab_button:
                widget.deleteLater()

        # Создание кнопок для каждого расписания
        for name in self.timetable_names:
            if name == self.selected_timetable:
                style = "font-weight: bold; border-bottom: 2px solid #3498db;"
            else:
                style = ""

            tab_button = QPushButton(name)
            tab_button.setStyleSheet(style)
            tab_button.clicked.connect(lambda _, n=name: self.switch_timetable(n))

            # Редактирование по двойному клику
            tab_button.setContextMenuPolicy(Qt.CustomContextMenu)
            tab_button.customContextMenuRequested.connect(
                lambda pos, n=name: self.show_timetable_context_menu(pos, n))

            self.tab_frame.layout().addWidget(tab_button)
            self.tab_buttons[name] = tab_button

    def show_timetable_context_menu(self, pos, name):
        menu = QMenu(self)
        edit_action = menu.addAction("Переименовать")
        delete_action = menu.addAction("Удалить")

        action = menu.exec_(self.sender().mapToGlobal(pos))

        if action == edit_action:
            self.edit_timetable_name(name)
        elif action == delete_action:
            self.delete_timetable(name)

    def render_active_timetable_radio(self):
        # Удаляем все дочерние элементы из active_frame
        while self.active_frame.layout().count():
            child = self.active_frame.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Создаем новые радиокнопки
        for name in self.timetable_names:
            radio = QRadioButton(name)
            radio.setChecked(name == self.main_app.settings["active_timetable"])
            radio.toggled.connect(lambda checked, n=name: self.set_active_timetable(n) if checked else None)
            self.active_frame.layout().addWidget(radio)

    def save_data(self):
        try:
            with db_lock:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM timetable WHERE timetable_name = ?", (self.selected_timetable,))

                for time_str, (task, color) in self.current_timetable.items():
                    cursor.execute(
                        "INSERT INTO timetable (time, task, color, timetable_name) VALUES (?, ?, ?, ?)",
                        (time_str, task, color, self.selected_timetable)
                    )

                self.conn.commit()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Произошла ошибка при сохранении данных: {str(e)}")
            print(f"Ошибка сохранения данных: {e}")

    def render_timetable(self):
        self.tree.clear()

        # Сортировка времени
        sorted_times = sorted(self.current_timetable.keys(), key=lambda x: self.time_str_to_minutes(x))

        # Заполнение таблицы
        for time_str in sorted_times:
            task, color = self.current_timetable[time_str]
            item = QTreeWidgetItem([time_str, task, color, self.selected_timetable])
            item.setBackground(2, QColor(color))
            item.setForeground(2, QColor("#000" if QColor(color).lightness() > 150 else "#FFF"))
            self.tree.addTopLevelItem(item)

    def time_str_to_minutes(self, time_str):
        t = datetime.strptime(time_str, "%H:%M").time()
        return t.hour * 60 + t.minute

    def add_new_item(self):
        """Добавление новой задачи с новым виджетом времени"""
        hours = self.hour_combo.currentText()
        minutes = self.minute_combo.currentText()
        time_str = f"{hours}:{minutes}"
        # Проверка валидности времени
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Неверный формат времени")
            return

        task = self.task_edit.text()
        if not task:
            QMessageBox.warning(self, "Ошибка", "Задача обязательна для заполнения")
            return

        # Проверка на конфликт времени
        if time_str in self.current_timetable:
            QMessageBox.warning(self, "Ошибка", "Время уже существует в текущем расписании")
            return

        color = self.color_edit.text()
        if not QColor(color).isValid():
            QMessageBox.warning(self, "Ошибка", "Неверный формат цвета. Используйте #RRGGBB")
            return

        self.current_timetable[time_str] = (task, color)
        self.save_data()
        self.render_timetable()

        # Сброс полей
        self.reset_time_selection()
        self.task_edit.clear()
        self.color_edit.setText("#FFFFFF")
        self.update_color_display()

    def reset_time_selection(self):
        """Сбрасывает выбор времени на значения по умолчанию"""
        self.hour_combo.setCurrentIndex(0)
        self.minute_combo.setCurrentIndex(0)

    def open_color_dialog(self):
        """Открывает диалог выбора цвета"""
        color = QColorDialog.getColor(QColor(self.color_edit.text()))
        if color.isValid():
            self.set_color(color.name())

    def set_color(self, color_code):
        """Устанавливает цвет и обновляет отображение"""
        self.color_edit.setText(color_code)
        self.update_color_display()

    def update_color_display(self):
        """Обновляет цветной индикатор"""
        color_str = self.color_edit.text()
        color = QColor(color_str)
        if color.isValid():
            self.color_display.setStyleSheet(f"background-color: {color_str}; border: 1px solid black;")
        else:
            self.color_display.setStyleSheet("background-color: #FFFFFF; border: 1px solid red;")

    def remove_item(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        time_str = item.text(0)

        if time_str in self.current_timetable:
            del self.current_timetable[time_str]
            self.save_data()
            self.render_timetable()

        # Сброс полей и кнопок
        self.save_data()
        self.render_timetable()
        self.tree.clearSelection()

    def switch_timetable(self, name):
        self.selected_timetable = name
        self.load_data()
        self.render_timetable()
        self.render_timetable_tabs()

    def set_active_timetable(self, name):
        self.main_app.settings["active_timetable"] = name
        self.main_app.save_settings()
        self.main_app.load_timetable()
        self.render_active_timetable_radio()

    def add_timetable(self):
        name, ok = QInputDialog.getText(self, "Новое расписание", "Введите название расписания:")
        if ok and name:
            if name in self.timetable_names:
                QMessageBox.warning(self, "Ошибка", "Расписание с таким именем уже существует")
                return

            # Сохраняем пустое расписание в БД
            with db_lock:
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO timetable (time, task, color, timetable_name) VALUES (?, ?, ?, ?)",
                    ("00:00", "Новая задача", "#FFFFFF", name)
                )
                self.conn.commit()

            self.timetable_names.append(name)
            self.selected_timetable = name
            self.load_data()
            self.render_timetable()
            self.render_timetable_tabs()
            self.render_active_timetable_radio()

    def edit_timetable_name(self, old_name):
        new_name, ok = QInputDialog.getText(self, "Переименование", "Введите новое название:", text=old_name)
        if ok and new_name and new_name != old_name:
            if new_name in self.timetable_names:
                QMessageBox.warning(self, "Ошибка", "Расписание с таким именем уже существует")
                return

            # Обновление в базе данных
            with db_lock:
                cursor = self.conn.cursor()
                cursor.execute("UPDATE timetable SET timetable_name = ? WHERE timetable_name = ?", (new_name, old_name))
                self.conn.commit()

            # Обновление в интерфейсе
            index = self.timetable_names.index(old_name)
            self.timetable_names[index] = new_name

            if self.selected_timetable == old_name:
                self.selected_timetable = new_name

            if self.main_app.settings["active_timetable"] == old_name:
                self.main_app.settings["active_timetable"] = new_name
                self.main_app.save_settings()

            self.render_timetable_tabs()
            self.render_active_timetable_radio()

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

            if self.selected_timetable == name:
                self.selected_timetable = "Основное"
                self.load_data()

            self.render_timetable_tabs()
            self.render_active_timetable_radio()

    def open_notification_editor(self):
        """Открывает редактор уведомлений"""
        self.notif_editor = NotificationEditor(self.main_app)
        self.notif_editor.exec_()

    def close_editor(self):
        self.save_data()
        self.main_app.load_timetable()
        self.main_app.show()
        self.close()

    def closeEvent(self, event):
        # Сохраняем данные и показываем главное окно
        self.save_data()
        self.main_app.load_timetable()
        self.main_app.show()
        event.accept()
