import os
import sys
import random
import json
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QMenu, QInputDialog, QMessageBox, QSizePolicy,
    QColorDialog
)
from PyQt5.QtCore import Qt, QStandardPaths
from PyQt5.QtGui import QFont, QColor


class TimeAnchorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Generation")
        self.setGeometry(800, 400, 500, 350)

        # Определение путей
        self.documents_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        self.base_folder = os.path.join(self.documents_path, "TimeAnchor")
        self.task_folder = os.path.join(self.base_folder, "Task")
        self.config_file = os.path.join(self.task_folder, "button_colors.json")

        # Создание папок при первом запуске
        self.setup_folders()

        # Загрузка конфигурации цветов
        self.button_colors = self.load_button_colors()

        # Инициализация интерфейса
        self.init_ui()

        # Загрузка кнопок
        self.load_buttons()

    def setup_folders(self):
        """Создает необходимые папки и тестовый файл"""
        os.makedirs(self.task_folder, exist_ok=True)

        # Создание тестового файла, если его нет
        test_file = os.path.join(self.task_folder, "Тест.txt")
        if not os.path.exists(test_file):
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('"Тест прошёл успешно";\n')

        # Создание файла конфигурации цветов, если его нет
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def load_button_colors(self):
        """Загружает конфигурацию цветов кнопок"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def save_button_colors(self):
        """Сохраняет конфигурацию цветов кнопок"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.button_colors, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.show_error(f"Ошибка сохранения цветов: {str(e)}")
            return False

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()

        # Верхняя панель с кнопками управления
        control_layout = QHBoxLayout()

        self.btn_add = QPushButton("+ Добавить")
        self.btn_add.clicked.connect(self.add_new_button)
        self.btn_add.setStyleSheet("background-color: #4a86e8; color: white;")

        self.btn_refresh = QPushButton("🔄 Обновить")
        self.btn_refresh.clicked.connect(self.refresh_buttons)
        self.btn_refresh.setStyleSheet("background-color: #4a86e8; color: white;")

        self.btn_random = QPushButton("🎲 Рандом")
        self.btn_random.clicked.connect(self.execute_random_action)
        self.btn_random.setStyleSheet("background-color: #4a86e8; color: white;")

        self.btn_help = QPushButton("?")
        self.btn_help.setFixedSize(20, 20)
        self.btn_help.setToolTip("Помощь")
        self.btn_help.setStyleSheet("background-color: #4a86e8; color: white;")
        self.btn_help.clicked.connect(self.show_help)

        control_layout.addWidget(self.btn_add)
        control_layout.addWidget(self.btn_refresh)
        control_layout.addStretch()
        control_layout.addWidget(self.btn_random)
        control_layout.addWidget(self.btn_help)

        # Область для кнопок категорий
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.buttons_layout = QHBoxLayout(self.scroll_content)
        self.buttons_layout.setAlignment(Qt.AlignLeft)
        self.scroll_area.setWidget(self.scroll_content)

        # Область вывода сообщений
        self.output_label = QLabel("Нажмите на кнопку для выполнения действия")
        self.output_label.setAlignment(Qt.AlignCenter)
        self.output_label.setWordWrap(True)
        self.output_label.setMinimumHeight(60)
        self.output_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)

        # Сборка главного интерфейса
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.scroll_area, 1)
        main_layout.addWidget(self.output_label)

        self.setLayout(main_layout)

        # Стилизация
        self.setStyleSheet("""
            QScrollArea {
                border: 1px solid #d0d0d0;
                border-radius: 5px;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QPushButton:pressed {
                opacity: 0.8;
            }
        """)

    def load_buttons(self):
        """Загружает кнопки из папки Task"""
        # Очистка текущих кнопок
        while self.buttons_layout.count():
            item = self.buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Создание новых кнопок
        for file_name in os.listdir(self.task_folder):
            if file_name.endswith('.txt') and file_name != "button_colors.json":
                name = os.path.splitext(file_name)[0]
                self.create_button(name)

    def create_button(self, name):
        """Создает кнопку с заданным именем"""
        btn = QPushButton(name)
        btn.setMinimumSize(120, 40)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Установка цвета кнопки
        if name in self.button_colors:
            color = self.button_colors[name]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                    font-size: 14px;
                }}
            """)
        else:
            # Цвет по умолчанию
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4a86e8;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                    font-size: 14px;
                }
            """)

        # Контекстное меню
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, b=btn: self.show_context_menu(pos, b)
        )

        # Обработчик клика
        btn.clicked.connect(
            lambda checked, n=name: self.execute_action(n)
        )

        self.buttons_layout.addWidget(btn)

    def show_context_menu(self, pos, button):
        """Показывает контекстное меню для кнопки"""
        menu = QMenu(self)

        rename_action = menu.addAction("✏️ Переименовать")
        delete_action = menu.addAction("🗑️ Удалить")
        color_action = menu.addAction("🎨 Изменить цвет")

        action = menu.exec_(button.mapToGlobal(pos))

        if action == rename_action:
            self.rename_button(button)
        elif action == delete_action:
            self.delete_button(button)
        elif action == color_action:
            self.change_button_color(button)

    def show_help(self):
        help_text = """
        <b>Инструкция по работе с задачами</b>
        <p>1. <b>Добавление новой категории:</b> нажмите "+ Добавить", введите название.</p>
        <p>2. <b>Добавление действий:</b> в папке Документы/TimeAnchor/Task создайте текстовый файл с именем категории. В каждой строке укажите одно действие в кавычках с точкой с запятой в конце. Вписание ссылки означает открытие в браузере по умолчанию</p>
        <p>3. <b>Выполнение действия:</b> нажмите на кнопку категории, чтобы выполнить случайное действие из нее.</p>
        <p>4. <b>Рандомное действие:</b> кнопка "🎲 Рандом" выполняет случайное действие из любой категории.</p>
        <p>5. <b>Контекстное меню:</b> нажмите правой кнопкой мыши на кнопке категории для переименования, удаления или смены цвета.</p>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("Справка")
        msg.setTextFormat(Qt.RichText)
        msg.setText(help_text)
        msg.exec_()

    def change_button_color(self, button):
        """Изменяет цвет кнопки"""
        name = button.text()
        current_color = self.button_colors.get(name, "#4a86e8")

        # Диалог выбора цвета
        color = QColorDialog.getColor(QColor(current_color), self, "Выберите цвет кнопки")
        if color.isValid():
            hex_color = color.name()

            # Обновляем стиль кнопки
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                    font-size: 14px;
                }}
            """)

            # Сохраняем в конфигурацию
            self.button_colors[name] = hex_color
            self.save_button_colors()

    def rename_button(self, button):
        """Переименовывает кнопку"""
        old_name = button.text()
        new_name, ok = QInputDialog.getText(
            self,
            "Переименовать кнопку",
            "Введите новое название:",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            # Обновляем цвет в конфигурации
            if old_name in self.button_colors:
                self.button_colors[new_name] = self.button_colors.pop(old_name)
                self.save_button_colors()

            button.setText(new_name)

    def delete_button(self, button):
        """Удаляет кнопку из интерфейса"""
        # Удаляем цвет из конфигурации
        name = button.text()
        if name in self.button_colors:
            del self.button_colors[name]
            self.save_button_colors()

        button.deleteLater()

    def add_new_button(self):
        """Добавляет новую кнопку"""
        name, ok = QInputDialog.getText(
            self,
            "Новая кнопка",
            "Введите название кнопки:"
        )

        if ok and name:
            # Создаем связанный файл
            file_path = os.path.join(self.task_folder, f"{name}.txt")
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('"Пример действия";\n')

            # Создаем кнопку
            self.create_button(name)

    def refresh_buttons(self):
        """Обновляет список кнопок"""
        self.load_buttons()
        self.show_message("Кнопки обновлены")

    def parse_action_file(self, file_name):
        """Читает и парсит файл с действиями"""
        file_path = os.path.join(self.task_folder, f"{file_name}.txt")

        if not os.path.exists(file_path):
            return None, f"Файл не найден: {file_name}.txt"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            return None, f"Ошибка чтения файла: {str(e)}"

        if not lines:
            return None, f"Файл пуст: {file_name}.txt"

        return lines, None

    def execute_action(self, button_name):
        """Выполняет случайное действие из файла"""
        try:
            lines, error = self.parse_action_file(button_name)

            if error:
                self.show_error(error)
                return

            # Выбираем случайное действие
            action_line = random.choice(lines)

            # Парсим действие
            if action_line.startswith('"') and action_line.endswith('";'):
                action = action_line[1:-2]
            else:
                action = action_line

            # Выполняем действие
            if action.startswith('http://') or action.startswith('https://'):
                try:
                    webbrowser.open(action)
                    self.show_message(f"Открыто: {action}")
                except Exception as e:
                    self.show_error(f"Ошибка открытия ссылки: {str(e)}")
            else:
                self.show_message(action)
        except Exception as e:
            self.show_error(f"Ошибка: {str(e)}")

    def execute_random_action(self):
        """Выполняет случайное действие из всех файлов"""
        all_actions = []

        # Собираем все действия из всех файлов
        for file_name in os.listdir(self.task_folder):
            if file_name.endswith('.txt') and file_name != "button_colors.json":
                lines, error = self.parse_action_file(os.path.splitext(file_name)[0])
                if error or not lines:
                    continue

                for line in lines:
                    if line.startswith('"') and line.endswith('";'):
                        action = line[1:-2]
                    else:
                        action = line
                    all_actions.append(action)

        if not all_actions:
            self.show_error("Нет доступных действий")
            return

        # Выбираем и выполняем случайное действие
        random_action = random.choice(all_actions)

        if random_action.startswith('http://') or random_action.startswith('https://'):
            try:
                webbrowser.open(random_action)
                self.show_message(f"Случайная ссылка: {random_action}")
            except Exception as e:
                self.show_error(f"Ошибка открытия ссылки: {str(e)}")
        else:
            self.show_message(f"Случайное действие: {random_action}")

    def show_message(self, text):
        """Отображает информационное сообщение"""
        self.output_label.setStyleSheet("color: black;")
        self.output_label.setText(text)

    def show_error(self, text):
        """Отображает сообщение об ошибке"""
        self.output_label.setStyleSheet("color: red;")
        self.output_label.setText(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Устанавливаем глобальный шрифт
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = TimeAnchorApp()
    window.show()
    sys.exit(app.exec_())