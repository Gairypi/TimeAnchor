# timer_window.py
import time
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QLCDNumber, QLabel, QPushButton, QMessageBox, QWidget, QLineEdit, QFileDialog
from PyQt5.QtCore import Qt
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, QTimer

class TimerWindow(QDialog):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.setWindowTitle("Секундомер/Таймер")
        self.setGeometry(1550, 200, 250, 250)

        # Состояние таймера
        self.running = False
        self.start_time = None
        self.paused_time = 0
        self.mode = "stopwatch"  # stopwatch|timer
        self.target_time = 0

        # Инициализация интерфейса
        self.init_ui()
        self.apply_theme()

        # Устанавливаем флаги окна
        self.setAttribute(Qt.WA_DeleteOnClose, False)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Выбор режима
        mode_frame = QWidget()
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(0, 0, 0, 0)

        self.stopwatch_rb = QRadioButton("Секундомер")
        self.stopwatch_rb.setChecked(True)
        self.stopwatch_rb.toggled.connect(lambda: self.set_mode("stopwatch"))

        self.timer_rb = QRadioButton("Таймер")
        self.timer_rb.toggled.connect(lambda: self.set_mode("timer"))

        mode_layout.addWidget(self.stopwatch_rb)
        mode_layout.addWidget(self.timer_rb)

        # Дисплей времени
        self.time_display = QLCDNumber()
        self.time_display.setDigitCount(8)  # Формат ММ:СС.ссс
        self.time_display.setSegmentStyle(QLCDNumber.Filled)
        self.time_display.display("00:00.000")

        # Поле ввода для таймера
        self.timer_frame = QWidget()
        timer_layout = QHBoxLayout(self.timer_frame)
        timer_layout.setContentsMargins(0, 0, 0, 0)

        self.timer_label = QLabel("Время (ММ:СС):")
        self.timer_edit = QLineEdit("05:00")
        self.timer_edit.setFixedWidth(60)

        timer_layout.addWidget(self.timer_label)
        timer_layout.addWidget(self.timer_edit)
        timer_layout.addStretch()
        self.timer_frame.setVisible(False)

        # Кнопки управления
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.start_button = QPushButton("Старт")
        self.start_button.clicked.connect(self.start_stop)

        self.reset_button = QPushButton("Сброс")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.reset_button)

        self.sound_button = QPushButton("🔊 Звук")
        self.sound_button.clicked.connect(self.choose_sound_file)
        layout.addWidget(self.sound_button)

        # Сборка интерфейса
        layout.addWidget(mode_frame)
        layout.addWidget(self.time_display)
        layout.addWidget(self.timer_frame)
        layout.addWidget(button_frame)

        self.setLayout(layout)

        # Таймер обновления
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_time)

    def apply_theme(self):
        theme = self.main_app.settings["theme"]
        if theme == "dark":
            style = """
                QDialog {
                    background-color: rgba(45, 45, 45, 200);
                    border: none;
                }
                QLabel, QRadioButton {
                    color: #EEE;
                }
                QLineEdit {
                    background-color: #333;
                    color: #EEE;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 3px;
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
                QPushButton:disabled {
                    background-color: #333;
                    color: #777;
                }
                QLCDNumber {
                    background-color: #222;
                    color: #0F0;
                    border: 1px solid #444;
                    border-radius: 5px;
                }
            """
        else:
            style = """
                QDialog {
                background-color: rgba(240, 240, 240, 200);
                border: none;
                }
                QLabel, QRadioButton {
                    color: #333;
                }
                QLineEdit {
                    background-color: #FFF;
                    color: #333;
                    border: 1px solid #CCC;
                    border-radius: 3px;
                    padding: 3px;
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
                QPushButton:disabled {
                    background-color: #f8f8f8;
                    color: #999;
                }
                QLCDNumber {
                    background-color: #222;
                    color: #0F0;
                    border: 1px solid #444;
                    border-radius: 5px;
                }
            """

        self.setStyleSheet(style)

    def set_mode(self, mode):
        self.mode = mode
        self.reset()
        self.timer_frame.setVisible(mode == "timer")

    def start_stop(self):
        if not self.running:
            # Старт таймера
            if self.mode == "timer":
                try:
                    time_str = self.timer_edit.text()
                    if ':' in time_str:
                        mins, secs = map(int, time_str.split(":"))
                    else:
                        mins = int(time_str)
                        secs = 0

                    self.target_time = mins * 60 + secs
                    if self.target_time <= 0:
                        raise ValueError
                except:
                    QMessageBox.warning(self, "Ошибка", "Неверный формат времени. Используйте ММ:СС")
                    return

            self.running = True
            self.start_button.setText("Пауза")
            self.reset_button.setEnabled(False)

            if self.start_time is None:
                self.start_time = time.time()
            else:
                self.start_time = time.time() - self.paused_time

            self.update_timer.start(10)  # Обновление каждые 10 мс
        else:
            # Пауза таймера
            self.running = False
            self.start_button.setText("Старт")
            self.reset_button.setEnabled(True)
            self.update_timer.stop()

            if self.start_time:
                elapsed = time.time() - self.start_time
                self.paused_time = elapsed

    def reset(self):
        self.running = False
        self.start_time = None
        self.paused_time = 0
        self.update_timer.stop()

        if self.mode == "stopwatch":
            self.time_display.display("00:00.000")
        else:
            self.time_display.display("00:00.000")

        self.start_button.setText("Старт")
        self.reset_button.setEnabled(False)

    def update_time(self):
        if not self.running:
            return

        current_time = time.time()
        elapsed = current_time - self.start_time

        if self.mode == "stopwatch":
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            milliseconds = int((elapsed * 1000) % 1000)
            time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.time_display.display(time_str)
        else:
            remaining = max(0, self.target_time - elapsed)

            if remaining <= 0:
                self.time_display.display("00:00.000")
                self.reset()

                # Воспроизведение звука
                sound_file = self.main_app.settings.get("timer_sound_file", self.main_app.settings["sound_file"])
                if sound_file:
                    try:
                        if self.main_app.timer_player.state() == QMediaPlayer.PlayingState:
                            self.main_app.timer_player.stop()

                        media_content = QMediaContent(QUrl.fromLocalFile(sound_file))
                        self.main_app.timer_player.setMedia(media_content)
                        self.main_app.timer_player.play()
                    except Exception as e:
                        print(f"Ошибка воспроизведения звука: {e}")
                return

            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            milliseconds = int((remaining * 1000) % 1000)
            time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.time_display.display(time_str)

    def choose_sound_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите звуковой файл",
            "",
            "Аудио файлы (*.mp3 *.wav);;Все файлы (*)"
        )

        if file_name:
            self.main_app.settings["timer_sound_file"] = file_name
            self.main_app.save_settings()

    def closeEvent(self, event):
        # Скрыть окно вместо закрытия
        self.hide()
        event.ignore()
