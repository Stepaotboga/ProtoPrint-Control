import sys
import os
import json
from pathlib import Path
from PyQt5 import uic
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                             QWidget, QPushButton, QLabel, QComboBox,
                             QTabWidget, QFileDialog, QMessageBox,
                             QGridLayout, QGroupBox, QSlider, QSpinBox,
                             QDoubleSpinBox, QDialog, QFormLayout, QDialogButtonBox, QLineEdit, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont
import serial
import serial.tools.list_ports

# Импорт модулей
from modules.serial_manager import SerialManager
from modules.gcode_handler import GCodeHandler
from modules.manual_control import ManualControlWidget
from modules.sd_card_manager import SDCardManager

# Определяем базовую директорию для корректной работы с файлами
BASE_DIR = Path(__file__).resolve().parent


class TerminalWindow(QDialog):
    """Окно терминала для общения со станком"""

    def __init__(self, serial_manager, parent=None):
        super().__init__(parent)
        self.serial_manager = serial_manager
        self.setWindowTitle("Терминал станка")
        self.setGeometry(200, 200, 600, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Лог сообщений
        self.log_widget = QWidget()
        self.log_layout = QVBoxLayout(self.log_widget)
        self.log_label = QLabel("История команд:")
        self.log_text = QLabel()
        self.log_text.setWordWrap(True)
        self.log_text.setStyleSheet("background-color: black; color: #00FF00; padding: 10px;")
        self.log_text.setMinimumHeight(300)

        # Поле ввода команды
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Введите G-код команду...")
        self.command_input.returnPressed.connect(self.send_command)

        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_command)

        self.clear_button = QPushButton("Очистить лог")
        self.clear_button.clicked.connect(self.clear_log)

        layout.addWidget(self.log_label)
        layout.addWidget(self.log_text)
        layout.addWidget(self.command_input)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.clear_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Подключаем сигналы
        if self.serial_manager:
            self.serial_manager.data_received.connect(self.append_to_log)

    def send_command(self):
        command = self.command_input.text().strip()
        if command and self.serial_manager:
            self.serial_manager.send_command(command)
            self.append_to_log(f">>> {command}")
            self.command_input.clear()

    def append_to_log(self, text):
        current_text = self.log_text.text()
        self.log_text.setText(f"{current_text}\n{text}")

    def clear_log(self):
        self.log_text.clear()


class WorkAreaSettingsDialog(QDialog):
    """Диалог настройки рабочей области"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка рабочей области")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(100, 1000)
        self.width_spin.setValue(350)
        self.width_spin.setSuffix(" мм")

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(100, 1000)
        self.height_spin.setValue(400)
        self.height_spin.setSuffix(" мм")

        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(10, 200)
        self.depth_spin.setValue(70)
        self.depth_spin.setSuffix(" мм")

        layout.addRow("Ширина (X):", self.width_spin)
        layout.addRow("Высота (Y):", self.height_spin)
        layout.addRow("Глубина (Z):", self.depth_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)


class WorkAreaWidget(QWidget):
    """Виджет отображения рабочей области"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.width = 350
        self.height = 400
        self.depth = 70
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0
        self.grid_size = 20  # размер клетки в мм

    def set_dimensions(self, width, height, depth):
        self.width = width
        self.height = height
        self.depth = depth
        self.update()

    def set_position(self, x, y, z):
        self.current_x = x
        self.current_y = y
        self.current_z = z
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Отрисовка фона
        painter.fillRect(self.rect(), QColor(240, 240, 240))

        # Расчет масштаба
        scale_x = self.width / self.width
        scale_y = self.height / self.height

        # Отрисовка сетки
        pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)
        painter.setPen(pen)

        # Вертикальные линии
        for i in range(0, int(self.width), self.grid_size):
            x = i * scale_x
            painter.drawLine(int(x), 0, int(x), int(self.height * scale_y))

        # Горизонтальные линии
        for i in range(0, int(self.height), self.grid_size):
            y = i * scale_y
            painter.drawLine(0, int(y), int(self.width * scale_x), int(y))

        # Отрисовка осей
        axis_pen = QPen(Qt.black, 2)
        painter.setPen(axis_pen)

        # Ось X
        painter.drawLine(0, int(self.height * scale_y), int(self.width * scale_x), int(self.height * scale_y))
        painter.drawText(int(self.width * scale_x) - 20, int(self.height * scale_y) - 5, "X")

        # Ось Y
        painter.drawLine(0, int(self.height * scale_y), 0, 0)
        painter.drawText(10, 15, "Y")

        # Отрисовка текущей позиции
        if 0 <= self.current_x <= self.width and 0 <= self.current_y <= self.height:
            pos_x = self.current_x * scale_x
            pos_y = self.current_y * scale_y

            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.setPen(QPen(Qt.red, 2))
            painter.drawEllipse(int(pos_x) - 5, int(pos_y) - 5, 10, 10)

            # Подпись позиции
            painter.drawText(int(pos_x) + 10, int(pos_y) - 10,
                             f"X:{self.current_x:.1f} Y:{self.current_y:.1f} Z:{self.current_z:.1f}")


class CNCController(QMainWindow):
    def __init__(self):
        super().__init__()

        # Загрузка UI из файла
        ui_path = BASE_DIR / "ui" / "main_window.ui"
        if ui_path.exists():
            uic.loadUi(str(ui_path), self)
            if not hasattr(self, 'width'):
                self.resize(1200, 800)
        else:
            print("UI файл не найден, используется программное создание интерфейса")
            self.setWindowTitle("CNC Controller - Marlin 2.1.2.5")
            self.setGeometry(100, 100, 1200, 800)

        # Инициализация модулей
        self.serial_manager = SerialManager()
        self.gcode_handler = GCodeHandler()
        self.sd_manager = SDCardManager(self.serial_manager)

        # Загрузка настроек
        self.load_settings()

        # Инициализация пользовательских виджетов
        self.init_custom_widgets()

        # Инициализация рабочей области
        self.init_work_area()

        # Подключение сигналов
        self.connect_signals()

        # Таймер для обновления позиции
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.update_position)
        self.position_timer.start(100)


    def load_settings(self):
        """Загрузка настроек из JSON файлов"""
        config_dir = BASE_DIR / "config"
        config_dir.mkdir(exist_ok=True)

        # Настройки станка
        machine_config_path = config_dir / "machine.json"
        if machine_config_path.exists():
            with open(machine_config_path, 'r') as f:
                self.machine_config = json.load(f)
        else:
            self.machine_config = {
                "work_area": {"width": 350, "height": 400, "depth": 70},
                "default_speed": 1000,
                "steps_per_mm": {"x": 80, "y": 80, "z": 400}
            }
            with open(machine_config_path, 'w') as f:
                json.dump(self.machine_config, f, indent=4)

        # Карта высот
        height_map_path = config_dir / "height_map.json"
        if not height_map_path.exists():
            with open(height_map_path, 'w') as f:
                json.dump({"points": []}, f, indent=4)

    def init_custom_widgets(self):
        """Инициализация кастомных виджетов, которых нет в UI файле"""
        # Создаем виджет рабочей области
        self.work_area = WorkAreaWidget(self.workAreaWidget)
        work_area_layout = QVBoxLayout(self.workAreaWidget)
        work_area_layout.setContentsMargins(0, 0, 0, 0)
        work_area_layout.addWidget(self.work_area)

        # Устанавливаем размеры из конфигурации
        wa = self.machine_config["work_area"]
        self.work_area.set_dimensions(wa["width"], wa["height"], wa["depth"])

    def connect_signals(self):
        """Подключение всех сигналов к элементам интерфейса"""
        # Верхняя панель
        self.connectButton.clicked.connect(self.toggle_connection)
        self.refreshPortsButton.clicked.connect(self.refresh_ports)
        self.emergencyStopButton.clicked.connect(self.emergency_stop)
        self.terminalButton.clicked.connect(self.open_terminal)

        # Ручное управление
        self.xPlusButton.clicked.connect(lambda: self.manual_control.move_axis('X', 1))
        self.xMinusButton.clicked.connect(lambda: self.manual_control.move_axis('X', -1))
        self.yPlusButton.clicked.connect(lambda: self.manual_control.move_axis('Y', 1))
        self.yMinusButton.clicked.connect(lambda: self.manual_control.move_axis('Y', -1))
        self.zPlusButton.clicked.connect(lambda: self.manual_control.move_axis('Z', 1))
        self.zMinusButton.clicked.connect(lambda: self.manual_control.move_axis('Z', -1))

        self.g90Button.clicked.connect(lambda: self.serial_manager.send_command("G90"))
        self.g91Button.clicked.connect(lambda: self.serial_manager.send_command("G91"))
        self.g92Button.clicked.connect(lambda: self.serial_manager.send_command("G92 X0 Y0 Z0"))
        self.parkButton.clicked.connect(self.manual_control.park_machine)
        self.homeButton.clicked.connect(lambda: self.serial_manager.send_command("G28"))

        # Управление программами
        self.selectFileButton.clicked.connect(self.select_gcode_file)
        self.runButton.clicked.connect(self.run_gcode)
        self.stopButton.clicked.connect(self.stop_gcode)
        self.uploadToSDButton.clicked.connect(self.upload_to_sd)
        self.printFromSDButton.clicked.connect(self.print_from_sd)

        # Настройки
        self.workAreaSettingsButton.clicked.connect(self.open_work_area_settings)
        self.actionWorkAreaSettings.triggered.connect(self.open_work_area_settings)

        # Меню
        self.actionExit.triggered.connect(self.close)
        self.actionAbout.triggered.connect(self.show_about)

    def init_work_area(self):
        """Инициализация виджета рабочей области"""
        # Создаем ManualControlWidget и передаем ему нужные элементы
        self.manual_control = ManualControlWidget(self.serial_manager, self)

    def show_about(self):
        """Показать окно о программе"""
        QMessageBox.about(self, "О программе",
                          "CNC Controller v1.0\n\n"
                          "Программа для управления ЧПУ станком\n"
                          "с прошивкой Marlin 2.1.2.5\n\n"
                          "© 2024")

    def init_ui(self):
        # Главный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout(central_widget)

        # ==================== ВЕРХНЯЯ ПАНЕЛЬ ====================
        top_panel = QWidget()
        top_layout = QGridLayout(top_panel)

        # Кнопка подключения
        self.connect_button = QPushButton("Подключить")
        self.connect_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px; }")
        self.connect_button.clicked.connect(self.toggle_connection)

        # Выбор порта
        self.port_combo = QComboBox()
        self.refresh_ports()
        refresh_ports_btn = QPushButton("↻")
        refresh_ports_btn.setMaximumWidth(30)
        refresh_ports_btn.clicked.connect(self.refresh_ports)

        # Кнопка аварийной остановки
        self.emergency_stop_btn = QPushButton("АВАРИЙНАЯ\nОСТАНОВКА")
        self.emergency_stop_btn.setStyleSheet("""
            QPushButton { 
                background-color: #FF0000; 
                color: white; 
                font-weight: bold; 
                padding: 10px;
                border: 3px solid #CC0000;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        self.emergency_stop_btn.clicked.connect(self.emergency_stop)

        # Кнопка терминала
        self.terminal_btn = QPushButton("Терминал")
        self.terminal_btn.clicked.connect(self.open_terminal)

        # Размещение элементов верхней панели
        port_widget = QWidget()
        port_layout = QGridLayout(port_widget)
        port_layout.addWidget(QLabel("Порт:"), 0, 0)
        port_layout.addWidget(self.port_combo, 0, 1)
        port_layout.addWidget(refresh_ports_btn, 0, 2)

        top_layout.addWidget(self.connect_button, 0, 0, 2, 1)
        top_layout.addWidget(port_widget, 0, 1, 2, 2)
        top_layout.addWidget(self.emergency_stop_btn, 0, 3, 2, 2)
        top_layout.addWidget(self.terminal_btn, 0, 5, 2, 1)

        # ==================== ЛЕВАЯ ПАНЕЛЬ (РАБОЧАЯ ОБЛАСТЬ) ====================
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.work_area = WorkAreaWidget()
        self.work_area.setMinimumSize(400, 450)

        # Кнопка настройки рабочей области
        settings_btn = QPushButton("Настройка рабочей области")
        settings_btn.clicked.connect(self.open_work_area_settings)

        left_layout.addWidget(self.work_area)
        left_layout.addWidget(settings_btn)

        # ==================== ПРАВАЯ ПАНЕЛЬ (УПРАВЛЕНИЕ) ====================
        right_panel = QTabWidget()

        # Вкладка ручного управления
        self.manual_control = ManualControlWidget(self.serial_manager)
        right_panel.addTab(self.manual_control, "Ручное управление")

        # Вкладка управления программами
        self.program_control = QWidget()
        program_layout = QVBoxLayout(self.program_control)

        # Группа загрузки G-кода
        gcode_group = QGroupBox("G-код программа")
        gcode_layout = QVBoxLayout()

        self.file_path_label = QLabel("Файл не выбран")
        select_file_btn = QPushButton("Выбрать файл G-кода")
        select_file_btn.clicked.connect(self.select_gcode_file)

        self.run_button = QPushButton("▶ ЗАПУСК")
        self.run_button.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-size: 14px;
                font-weight: bold; 
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.run_button.clicked.connect(self.run_gcode)
        self.run_button.setEnabled(False)

        self.stop_button = QPushButton("■ СТОП")
        self.stop_button.setStyleSheet("""
            QPushButton { 
                background-color: #f44336; 
                color: white; 
                font-size: 14px;
                font-weight: bold; 
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.stop_button.clicked.connect(self.stop_gcode)
        self.stop_button.setEnabled(False)

        gcode_layout.addWidget(self.file_path_label)
        gcode_layout.addWidget(select_file_btn)
        gcode_layout.addWidget(self.run_button)
        gcode_layout.addWidget(self.stop_button)
        gcode_group.setLayout(gcode_layout)

        # Группа SD карты
        sd_group = QGroupBox("SD карта")
        sd_layout = QVBoxLayout()

        upload_to_sd_btn = QPushButton("Загрузить на SD карту")
        upload_to_sd_btn.clicked.connect(self.upload_to_sd)

        print_from_sd_btn = QPushButton("Печать с SD карты")
        print_from_sd_btn.clicked.connect(self.print_from_sd)

        sd_layout.addWidget(upload_to_sd_btn)
        sd_layout.addWidget(print_from_sd_btn)
        sd_group.setLayout(sd_layout)

        program_layout.addWidget(gcode_group)
        program_layout.addWidget(sd_group)
        program_layout.addStretch()

        right_panel.addTab(self.program_control, "Управление программами")

        # Размещение панелей в главном layout
        main_layout.addWidget(top_panel, 0, 0, 1, 2)
        main_layout.addWidget(left_panel, 1, 0)
        main_layout.addWidget(right_panel, 1, 1)

        # Настройка размеров колонок
        main_layout.setColumnStretch(0, 3)
        main_layout.setColumnStretch(1, 1)

        # Установка начальных размеров рабочей области
        wa = self.machine_config["work_area"]
        self.work_area.set_dimensions(wa["width"], wa["height"], wa["depth"])

    def toggle_connection(self):
        """Подключение/отключение от станка"""
        if not self.serial_manager.is_connected:
            port = self.portComboBox.currentText()
            if port:
                if self.serial_manager.connect(port):
                    self.connectButton.setText("Отключить")
                    self.connectButton.setStyleSheet("""
                        QPushButton { 
                            background-color: #f44336; 
                            color: white; 
                            font-weight: bold;
                            border-radius: 5px;
                        }
                        QPushButton:hover {
                            background-color: #da190b;
                        }
                    """)
                    self.runButton.setEnabled(True)
                    self.statusbar.showMessage(f"Подключено к {port}")
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к порту")
        else:
            self.serial_manager.disconnect()
            self.connectButton.setText("Подключить")
            self.connectButton.setStyleSheet("""
                QPushButton { 
                    background-color: #4CAF50; 
                    color: white; 
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.runButton.setEnabled(False)
            self.stopButton.setEnabled(False)
            self.statusbar.showMessage("Отключено")

    def refresh_ports(self):
        """Обновление списка доступных портов"""
        self.portComboBox.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.portComboBox.addItem(f"{port.device} - {port.description}")

    def emergency_stop(self):
        """Аварийная остановка"""
        self.serial_manager.send_emergency_stop()
        self.stop_gcode()
        QMessageBox.warning(self, "Аварийная остановка", "Станок остановлен!")

    def open_terminal(self):
        """Открытие окна терминала"""
        self.terminal_window = TerminalWindow(self.serial_manager, self)
        self.terminal_window.show()

    def open_work_area_settings(self):
        """Открытие диалога настройки рабочей области"""
        dialog = WorkAreaSettingsDialog(self)
        if dialog.exec_():
            width = dialog.width_spin.value()
            height = dialog.height_spin.value()
            depth = dialog.depth_spin.value()

            self.work_area.set_dimensions(width, height, depth)

            # Сохранение настроек
            self.machine_config["work_area"] = {
                "width": width,
                "height": height,
                "depth": depth
            }
            config_path = BASE_DIR / "config" / "machine.json"
            with open(config_path, 'w') as f:
                json.dump(self.machine_config, f, indent=4)

    def select_gcode_file(self):
        """Выбор файла G-кода"""
        gcode_dir = BASE_DIR / "resources" / "gcode"
        gcode_dir.mkdir(parents=True, exist_ok=True)

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл G-кода",
            str(gcode_dir),
            "G-code files (*.gcode *.nc *.ngc);;All files (*.*)"
        )

        if file_path:
            self.gcode_handler.load_file(file_path)
            self.file_path_label.setText(os.path.basename(file_path))

    def run_gcode(self):
        """Запуск выполнения G-кода"""
        if self.gcode_handler.is_loaded and self.serial_manager.is_connected:
            self.run_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.gcode_handler.execute(self.serial_manager)

    def stop_gcode(self):
        """Остановка выполнения G-кода"""
        self.gcode_handler.stop()
        self.serial_manager.send_command("M0")  # Остановка программы
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def upload_to_sd(self):
        """Загрузка файла на SD карту"""
        if not self.gcode_handler.is_loaded:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите файл G-кода")
            return

        file_name = os.path.basename(self.gcode_handler.file_path)
        self.sd_manager.upload_file(self.gcode_handler.file_path, file_name)

    def print_from_sd(self):
        """Запуск печати с SD карты"""
        file_name, ok = QInputDialog.getText(self, "Печать с SD", "Имя файла на SD карте:")
        if ok and file_name:
            self.sd_manager.start_print_from_sd(file_name)

    def update_position(self):
        """Обновление отображения позиции"""
        if self.serial_manager.is_connected:
            self.serial_manager.send_command("M114")  # Запрос текущей позиции
            # Позиция будет обновлена через сигнал data_received

    def closeEvent(self, event):
        """Закрытие приложения"""
        if self.serial_manager.is_connected:
            reply = QMessageBox.question(self, 'Подтверждение',
                                         'Отключиться от станка?',
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.serial_manager.disconnect()

        # Остановка выполнения перед закрытием
        self.gcode_handler.stop()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Установка стиля приложения
    app.setStyle('Fusion')

    # Загрузка и применение стилей из QSS если есть
    style_path = BASE_DIR / "resources" / "style.qss"
    if style_path.exists():
        with open(style_path, 'r') as f:
            app.setStyleSheet(f.read())

    window = CNCController()
    window.show()
    sys.exit(app.exec_())