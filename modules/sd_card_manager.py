import os
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt


class SDCardManager(QObject):
    def __init__(self, serial_manager):
        super().__init__()
        self.serial_manager = serial_manager

    def upload_file(self, local_file_path, file_name):
        """Загрузка файла на SD карту станка"""
        if not os.path.exists(local_file_path):
            QMessageBox.critical(None, "Ошибка", "Файл не найден")
            return False

        # Создаем диалог прогресса
        progress = QProgressDialog("Загрузка файла на SD карту...", "Отмена", 0, 100)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        try:
            with open(local_file_path, 'r') as f:
                lines = f.readlines()

            # Команда начала записи на SD карту
            self.serial_manager.send_command(f"M28 {file_name}")

            total_lines = len(lines)
            for i, line in enumerate(lines):
                if progress.wasCanceled():
                    self.serial_manager.send_command("M29")  # Отмена записи
                    return False

                line = line.strip()
                if line:
                    self.serial_manager.send_command(line)

                progress.setValue(int((i / total_lines) * 100))

            # Команда завершения записи
            self.serial_manager.send_command("M29")

            QMessageBox.information(None, "Успех", f"Файл {file_name} загружен на SD карту")
            return True

        except Exception as e:
            QMessageBox.critical(None, "Ошибка", f"Ошибка загрузки файла: {str(e)}")
            return False

    def start_print_from_sd(self, file_name):
        """Запуск печати с SD карты"""
        if not file_name:
            return False

        # Команда запуска печати с SD карты
        self.serial_manager.send_command(f"M23 {file_name}")
        self.serial_manager.send_command("M24")

        return True

    def list_sd_files(self):
        """Получение списка файлов на SD карте"""
        self.serial_manager.send_command("M20")
        # Ответ будет получен через сигнал data_received