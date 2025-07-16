# main.py
import sys
from PyQt5.QtWidgets import QApplication
from time_anchor import TimeOverlay
from utils import create_demo_data, get_data_folder_path, get_db_path

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Создание папок и демо-данных
    data_folder_path = get_data_folder_path()
    db_path = get_db_path()
    create_demo_data(db_path)

    # Создаем папку Task если её нет
    task_folder = data_folder_path / "Task"
    task_folder.mkdir(parents=True, exist_ok=True)

    # Запуск главного окна
    overlay = TimeOverlay()
    overlay.show()
    sys.exit(app.exec_())