import serial
import serial.tools.list_ports
import time
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import re


class SerialManager(QObject):
    data_received = pyqtSignal(str)
    connection_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.serial = None
        self.is_connected = False
        self.read_thread = None

    def connect(self, port, baudrate=115200):
        """Подключение к станку через USB"""
        try:
            self.serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1,
                write_timeout=1
            )

            # Очистка буфера
            time.sleep(2)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            # Проверка связи
            self.serial.write(b'M115\n')
            time.sleep(0.5)
            response = self.serial.readline().decode('utf-8', errors='ignore')

            if 'Marlin' in response:
                self.is_connected = True
                self.connection_changed.emit(True)

                # Запуск потока чтения
                self.read_thread = ReadThread(self.serial)
                self.read_thread.data_received.connect(self.data_received.emit)
                self.read_thread.start()

                return True
            else:
                self.serial.close()
                return False

        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False

    def disconnect(self):
        """Отключение от станка"""
        if self.read_thread:
            self.read_thread.stop()
            self.read_thread.wait()

        if self.serial and self.serial.is_open:
            self.serial.close()

        self.is_connected = False
        self.connection_changed.emit(False)

    def send_command(self, command):
        """Отправка команды на станок"""
        if self.is_connected and self.serial:
            try:
                # Добавляем перевод строки если его нет
                if not command.endswith('\n'):
                    command += '\n'
                self.serial.write(command.encode('utf-8'))
                return True
            except Exception as e:
                print(f"Ошибка отправки команды: {e}")
                return False
        return False

    def send_emergency_stop(self):
        """Аварийная остановка"""
        self.send_command('M112')
        self.send_command('M410')


class ReadThread(QThread):
    data_received = pyqtSignal(str)

    def __init__(self, serial):
        super().__init__()
        self.serial = serial
        self.running = True

    def run(self):
        while self.running:
            try:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.data_received.emit(line)
            except Exception as e:
                if self.running:  # Не выводим ошибку если поток останавливается
                    print(f"Ошибка чтения: {e}")
                break

    def stop(self):
        self.running = False