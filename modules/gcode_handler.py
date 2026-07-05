import os
import re
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class GCodeHandler(QObject):
    progress_changed = pyqtSignal(int)
    execution_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.file_path = None
        self.is_loaded = False
        self.is_running = False
        self.commands = []
        self.current_index = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.send_next_command)
        self.serial_manager = None

    def load_file(self, file_path):
        """Загрузка файла G-кода"""
        if not os.path.exists(file_path):
            return False

        self.file_path = file_path

        with open(file_path, 'r') as f:
            content = f.read()

        # Парсинг команд
        self.commands = self.parse_gcode(content)
        self.is_loaded = True
        self.current_index = 0

        return True

    def parse_gcode(self, content):
        """Парсинг G-кода в список команд"""
        commands = []
        lines = content.split('\n')

        for line in lines:
            # Удаляем комментарии
            line = line.split(';')[0].strip()

            if line:
                # Удаляем лишние пробелы
                line = re.sub(r'\s+', ' ', line)
                commands.append(line)

        return commands

    def execute(self, serial_manager):
        """Начало выполнения программы"""
        if not self.is_loaded or not self.commands:
            return False

        self.serial_manager = serial_manager
        self.is_running = True
        self.current_index = 0

        # Отправляем первую команду
        self.send_next_command()

        return True

    def send_next_command(self):
        """Отправка следующей команды"""
        if not self.is_running or not self.serial_manager:
            self.timer.stop()
            return

        if self.current_index < len(self.commands):
            command = self.commands[self.current_index]

            # Отправка команды
            success = self.serial_manager.send_command(command)

            if success:
                self.current_index += 1
                progress = int((self.current_index / len(self.commands)) * 100)
                self.progress_changed.emit(progress)

                # Запускаем таймер для следующей команды
                self.timer.start(100)  # Задержка между командами 100мс
            else:
                self.stop()
        else:
            self.stop()
            self.execution_finished.emit()

    def stop(self):
        """Остановка выполнения"""
        self.is_running = False
        self.timer.stop()