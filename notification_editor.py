# notification_editor.py
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QMessageBox, QInputDialog, QApplication, QFrame, QMenu,
    QSpinBox, QLineEdit, QFileDialog, QStyle, QStyleOption, QGridLayout, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor


class NotificationEditor(QDialog):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.setWindowTitle("Редактор уведомлений")
        self.setGeometry(400, 300, 700, 500)

        self.data_folder = Path.home() / "Documents" / "TimeAnchor"
        self.before_file = self.data_folder / "before.txt"
        self.now_file = self.data_folder / "now.txt"

        # Загрузка данных
        self.before_items = self.load_items(self.before_file)
        self.now_items = self.load_items(self.now_file)

        self.init_ui()
        self.apply_theme()

    def paintEvent(self, event):
        """Для корректного применения стилей в QDialog"""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

    def load_items(self, file_path):
        """Загружает элементы из файла"""
        items = []
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip().strip('";')
                        if line:
                            items.append(line)
            except Exception as e:
                print(f"Ошибка чтения файла: {e}")
        return items

    def save_items(self, items, file_path):
        """Сохраняет элементы в файл"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for item in items:
                    f.write(f'"{item}";\n')
            return True
        except Exception as e:
            print(f"Ошибка сохранения файла: {e}")
            return False

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Текст уведомлений", alignment=Qt.AlignCenter))
        main_layout.addLayout(title_layout)

        # Две колонки с уведомлениями
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)

        # Колонка "Напоминание"
        before_frame = QFrame()
        before_frame.setFrameShape(QFrame.StyledPanel)
        before_layout = QVBoxLayout(before_frame)
        before_layout.setSpacing(8)

        before_label = QLabel("Напоминание (до начала)")
        before_label.setAlignment(Qt.AlignCenter)
        before_layout.addWidget(before_label)

        self.before_list = QListWidget()
        self.before_list.addItems(self.before_items)
        self.before_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.before_list.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, self.before_list, "before")
        )
        before_layout.addWidget(self.before_list)

        add_before_btn = QPushButton("+ Добавить")
        add_before_btn.clicked.connect(lambda: self.add_item(self.before_list, "before"))
        before_layout.addWidget(add_before_btn)

        columns_layout.addWidget(before_frame, 1)  # Равные пропорции

        # Колонка "Уведомление"
        now_frame = QFrame()
        now_frame.setFrameShape(QFrame.StyledPanel)
        now_layout = QVBoxLayout(now_frame)
        now_layout.setSpacing(8)

        now_label = QLabel("Уведомление (начало)")
        now_label.setAlignment(Qt.AlignCenter)
        now_layout.addWidget(now_label)

        self.now_list = QListWidget()
        self.now_list.addItems(self.now_items)
        self.now_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.now_list.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, self.now_list, "now")
        )
        now_layout.addWidget(self.now_list)

        add_now_btn = QPushButton("+ Добавить")
        add_now_btn.clicked.connect(lambda: self.add_item(self.now_list, "now"))
        now_layout.addWidget(add_now_btn)

        columns_layout.addWidget(now_frame, 1)  # Равные пропорции
        main_layout.addLayout(columns_layout, 1)  # Основная часть окна

        # Настройки уведомлений
        settings_frame = QFrame()
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setSpacing(10)

        # Чекбокс и поля ввода
        self.notif_check = QCheckBox("Включить уведомления")
        self.notif_check.setChecked(self.main_app.settings["notification_enabled"])
        settings_layout.addWidget(self.notif_check)

        # Сетка для числовых полей
        grid_layout = QGridLayout()

        grid_layout.addWidget(QLabel("Предупреждение за (мин):"), 0, 0)
        self.before_mins_edit = QSpinBox()
        self.before_mins_edit.setRange(1, 60)
        self.before_mins_edit.setValue(self.main_app.settings["notification_before_mins"])
        grid_layout.addWidget(self.before_mins_edit, 0, 1)

        grid_layout.addWidget(QLabel("Длительность (сек):"), 1, 0)
        self.duration_edit = QSpinBox()
        self.duration_edit.setRange(1, 60)
        self.duration_edit.setValue(self.main_app.settings["notification_duration_secs"])
        grid_layout.addWidget(self.duration_edit, 1, 1)

        settings_layout.addLayout(grid_layout)

        # Кнопки звуков
        sound_layout = QHBoxLayout()
        self.sound_before_btn = QPushButton("Звук предупреждения...")
        self.sound_before_btn.clicked.connect(lambda: self.choose_sound_file("before"))

        self.sound_now_btn = QPushButton("Звук начала...")
        self.sound_now_btn.clicked.connect(lambda: self.choose_sound_file("now"))

        sound_layout.addWidget(self.sound_before_btn)
        sound_layout.addWidget(self.sound_now_btn)
        settings_layout.addLayout(sound_layout)

        main_layout.addWidget(settings_frame)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        help_btn = QPushButton("?")
        help_btn.setFixedWidth(30)
        help_btn.clicked.connect(self.show_help)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_settings)

        cancel_btn = QPushButton("Закрыть")
        cancel_btn.clicked.connect(self.close)

        buttons_layout.addWidget(help_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def show_context_menu(self, pos, list_widget, list_type):
        """Показывает контекстное меню для списка"""
        item = list_widget.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        rename_action = menu.addAction("✏️ Переименовать")
        delete_action = menu.addAction("🗑️ Удалить")

        action = menu.exec_(list_widget.mapToGlobal(pos))

        if action == rename_action:
            self.rename_item(item, list_type)
        elif action == delete_action:
            self.delete_item(item, list_type)

    def rename_item(self, item, list_type):
        """Переименовывает выбранный элемент"""
        new_text, ok = QInputDialog.getText(
            self,
            "Переименовать",
            "Введите новый текст:",
            text=item.text()
        )

        if ok and new_text:
            item.setText(new_text)
            self.update_list_data(list_type)

    def delete_item(self, item, list_type):
        """Удаляет выбранный элемент"""
        row = self.before_list.row(item) if list_type == "before" else self.now_list.row(item)

        if list_type == "before":
            self.before_list.takeItem(row)
        else:
            self.now_list.takeItem(row)

        self.update_list_data(list_type)

    def add_item(self, list_widget, list_type):
        """Добавляет новый элемент в список"""
        default_text = "Скоро будет задача" if list_type == "before" else "Уже началось"
        new_item = QListWidgetItem(default_text)
        list_widget.addItem(new_item)
        self.update_list_data(list_type)

    def update_list_data(self, list_type):
        """Обновляет данные в соответствующем списке"""
        if list_type == "before":
            self.before_items = [self.before_list.item(i).text() for i in range(self.before_list.count())]
        else:
            self.now_items = [self.now_list.item(i).text() for i in range(self.now_list.count())]

    def choose_sound_file(self, sound_type):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите звуковой файл",
            "",
            "Аудио файлы (*.mp3 *.wav);;Все файлы (*)"
        )

        if file_name:
            if sound_type == "before":
                self.main_app.settings["sound_before_file"] = file_name
            else:
                self.main_app.settings["sound_now_file"] = file_name

    def save_settings(self):
        """Сохраняет все настройки"""
        # Сохраняем тексты уведомлений
        self.save_items(self.before_items, self.before_file)
        self.save_items(self.now_items, self.now_file)

        # Сохраняем настройки
        try:
            self.main_app.settings.update({
                "notification_enabled": self.notif_check.isChecked(),
                "notification_before_mins": self.before_mins_edit.value(),
                "notification_duration_secs": self.duration_edit.value()
            })
            self.main_app.save_settings()
            QMessageBox.information(self, "Сохранено", "Настройки успешно сохранены")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка сохранения: {str(e)}")

    def show_help(self):
        help_text = """
        <b>Инструкция по работе с редактором уведомлений</b>

        <p><b>Колонка "Напоминание":</b></p>
        <ul>
            <li>Содержит тексты, которые показываются за несколько минут до начала задачи</li>
            <li>Для добавления нового текста нажмите "+ Добавить"</li>
            <li>Для изменения текста кликните правой кнопкой мыши по элементу и выберите "Переименовать"</li>
            <li>Для удаления текста кликните правой кнопкой мыши по элементу и выберите "Удалить"</li>
        </ul>

        <p><b>Колонка "Уведомление":</b></p>
        <ul>
            <li>Содержит тексты, которые показываются в момент начала задачи</li>
            <li>Управление элементами аналогично колонке "Напоминание"</li>
        </ul>

        <p><b>Настройки:</b></p>
        <ul>
            <li><b>Включить уведомления:</b> активирует/деактивирует все уведомления</li>
            <li><b>Предупреждение за (мин):</b> за сколько минут до начала показывать напоминание</li>
            <li><b>Длительность (сек):</b> сколько секунд показывать уведомление</li>
            <li><b>Звук предупреждения:</b> звук для напоминания (до начала)</li>
            <li><b>Звук начала:</b> звук для уведомления о начале</li>
        </ul>

        <p>Не забудьте нажать <b>"Сохранить"</b> для применения изменений!</p>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("Справка")
        msg.setTextFormat(Qt.RichText)

        # Применяем стиль в зависимости от темы
        if self.main_app.settings["theme"] == "dark":
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #333;
                }
                QLabel {
                    color: white;
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
            """)
        else:
            msg.setStyleSheet("""
                QLabel {
                    color: black;
                }
            """)

        msg.setText(help_text)
        msg.exec_()

    def apply_theme(self):
        theme = self.main_app.settings["theme"]
        if theme == "dark":
            style = """
                QDialog {
                    background-color: #333;
                    color: #EEE;
                }
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 5px;
                }
                QLabel, QRadioButton, QListWidget, QSpinBox, QCheckBox {
                    color: #EEE;
                }
                QListWidget {
                    background-color: #222;
                    color: #EEE;
                    border: 1px solid #444;
                }
                QLineEdit, QSpinBox {
                    background-color: #333;
                    color: #EEE;
                    border: 1px solid #555;
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
            """
        else:
            style = """
                QDialog {
                    background-color: #f0f0f0;
                    color: #333;
                }
                QFrame {
                    background-color: #FFF;
                    border: 1px solid #CCC;
                    border-radius: 5px;
                }
                QListWidget {
                    background-color: #FFF;
                    color: #333;
                    border: 1px solid #CCC;
                }
                QLineEdit, QSpinBox {
                    background-color: #FFF;
                    color: #333;
                    border: 1px solid #CCC;
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
            """
        self.setStyleSheet(style)