# notification.py
import os
import random
from pathlib import Path
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QFont, QColor, QPalette


class NotificationWindow(QDialog):
    def __init__(self, text_file, duration, task_name, theme="dark"):
        super().__init__()
        # Настройка окна
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.ToolTip
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        # Основной контейнер
        self.container = QWidget()
        self.container.setMinimumWidth(400)
        self.container.setMaximumWidth(600)

        # Применение темы
        self.apply_theme(theme)

        # Основной лейаут
        layout = QVBoxLayout(self.container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.add_task_name(task_name, layout)
        self.add_notification_text(text_file, layout)

        # Главный лейаут окна
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Позиционирование и показ
        self.adjustSize()
        self.center_on_screen()

        # Автозакрытие
        QTimer.singleShot(duration * 1000, self.close)

        self.init_ui(text_file, duration, task_name, theme)

    def init_ui(self, text_file, duration, task_name, theme):
        """Инициализация интерфейса без изображений"""
        # Убираем загрузку изображений
        layout = QVBoxLayout(self.container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)  # Увеличиваем отступы

        # Добавляем только текст
        self.add_task_name(task_name, layout)
        self.add_notification_text(text_file, layout)

    def apply_theme(self, theme):
        """Применяет цветовую тему без изображений"""
        if theme == "dark":
            bg_color = QColor(20, 20, 20, 220)  # Более непрозрачный
            text_color = "#FFFFFF"
        else:
            bg_color = QColor(240, 240, 240, 220)
            text_color = "#333333"

        # Устанавливаем цвета через палитру
        palette = self.container.palette()
        palette.setColor(QPalette.Window, bg_color)
        self.container.setPalette(palette)
        self.container.setAutoFillBackground(True)

        # Убираем границу и закругления
        self.container.setStyleSheet("""
            border-radius: 0;
            border: none;
        """)

        self.text_color = text_color

    def add_task_name(self, task_name, layout):
        """Добавляет название задачи с улучшенным оформлением"""
        task_label = QLabel(task_name)
        task_label.setStyleSheet(f"""
                    color: {self.text_color};
                    font-weight: bold;
                    font-size: 16px;
                    padding: 10px;
                    background-color: rgba(0, 0, 0, 50);
                    border-radius: 5px;
                """)
        task_label.setAlignment(Qt.AlignCenter)
        task_label.setFont(QFont("Arial", 12, QFont.Bold))
        task_label.setWordWrap(True)
        layout.addWidget(task_label)

    def add_notification_text(self, text_file, layout):
        """Добавляет текст уведомления с улучшенным оформлением"""
        content = self.get_notification_text(text_file)
        text_label = QLabel(content)
        text_label.setStyleSheet(f"""
            color: {self.text_color};
            font-size: 14px;
            padding: 15px;
            background-color: rgba(0, 0, 0, 30);
            border-radius: 5px;
            line-height: 1.5;
        """)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

    def get_notification_text(self, text_file):
        """Возвращает случайную строку из файла"""
        if not text_file or not Path(text_file).is_file():
            return "Напоминание"

        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                lines = [line.strip().strip('";') for line in f.readlines() if line.strip()]
                return random.choice(lines) if lines else "Напоминание"
        except Exception as e:
            print(f"Ошибка чтения текста: {e}")
            return "Напоминание"

    def center_on_screen(self):
        """Центрирует окно на активном экране"""
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 3  # Смещение к верхней трети
        self.move(QPoint(x, y))

    def mousePressEvent(self, event):
        """Закрывает окно по клику"""
        if event.button() == Qt.LeftButton:
            self.close()

    def show(self):
        """Активирует окно при показе"""
        super().show()
        self.activateWindow()
        self.raise_()  # Гарантированное отображение поверх всех окон