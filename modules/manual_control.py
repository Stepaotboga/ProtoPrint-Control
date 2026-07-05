from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QGroupBox,
                             QGridLayout, QLabel, QDoubleSpinBox, QComboBox)
from PyQt5.QtCore import Qt


class ManualControlWidget(QWidget):
    def __init__(self, serial_manager, parent=None):
        super().__init__(parent)
        self.serial_manager = serial_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Группа движения по осям
        movement_group = QGroupBox("Движение по осям")
        movement_layout = QGridLayout()

        # Настройка шага перемещения
        step_label = QLabel("Шаг:")
        self.step_combo = QComboBox()
        self.step_combo.addItems(["0.1", "1", "10", "100"])
        self.step_combo.setCurrentText("1")

        movement_layout.addWidget(step_label, 0, 0)
        movement_layout.addWidget(self.step_combo, 0, 1)

        # Кнопки управления осями
        # XY кнопки
        self.btn_y_plus = QPushButton("Y+ ▲")
        self.btn_y_minus = QPushButton("Y- ▼")
        self.btn_x_minus = QPushButton("X- ◄")
        self.btn_x_plus = QPushButton("X+ ►")

        # Z кнопки
        self.btn_z_plus = QPushButton("Z+ ▲")
        self.btn_z_minus = QPushButton("Z- ▼")

        # Размещение XY кнопок
        movement_layout.addWidget(self.btn_y_plus, 1, 1)
        movement_layout.addWidget(self.btn_x_minus, 2, 0)
        movement_layout.addWidget(self.btn_x_plus, 2, 2)
        movement_layout.addWidget(self.btn_y_minus, 3, 1)

        # Размещение Z кнопок
        movement_layout.addWidget(QLabel("Z ось:"), 4, 0)
        movement_layout.addWidget(self.btn_z_plus, 4, 1)
        movement_layout.addWidget(self.btn_z_minus, 4, 2)

        # Подключение сигналов
        self.btn_x_plus.clicked.connect(lambda: self.move_axis('X', 1))
        self.btn_x_minus.clicked.connect(lambda: self.move_axis('X', -1))
        self.btn_y_plus.clicked.connect(lambda: self.move_axis('Y', 1))
        self.btn_y_minus.clicked.connect(lambda: self.move_axis('Y', -1))
        self.btn_z_plus.clicked.connect(lambda: self.move_axis('Z', 1))
        self.btn_z_minus.clicked.connect(lambda: self.move_axis('Z', -1))

        movement_group.setLayout(movement_layout)

        # Группа специальных команд
        commands_group = QGroupBox("Команды")
        commands_layout = QVBoxLayout()

        # Кнопки G-кодов
        self.btn_g90 = QPushButton("G90 (Абсолютное позиционирование)")
        self.btn_g91 = QPushButton("G91 (Относительное позиционирование)")
        self.btn_g92 = QPushButton("G92 (Установить текущую позицию)")
        self.btn_park = QPushButton("Парковка")
        self.btn_home = QPushButton("Домой (G28)")

        self.btn_g90.clicked.connect(lambda: self.send_command("G90"))
        self.btn_g91.clicked.connect(lambda: self.send_command("G91"))
        self.btn_g92.clicked.connect(lambda: self.send_command("G92 X0 Y0 Z0"))
        self.btn_park.clicked.connect(self.park_machine)
        self.btn_home.clicked.connect(lambda: self.send_command("G28"))

        commands_layout.addWidget(self.btn_g90)
        commands_layout.addWidget(self.btn_g91)
        commands_layout.addWidget(self.btn_g92)
        commands_layout.addWidget(self.btn_park)
        commands_layout.addWidget(self.btn_home)

        commands_group.setLayout(commands_layout)

        # Добавление групп в основной layout
        layout.addWidget(movement_group)
        layout.addWidget(commands_group)
        layout.addStretch()

        self.setLayout(layout)

    def move_axis(self, axis, direction):
        """Перемещение по оси"""
        step = float(self.step_combo.currentText())
        distance = step * direction

        if axis == 'X':
            command = f"G91\nG0 X{distance}\nG90"
        elif axis == 'Y':
            command = f"G91\nG0 Y{distance}\nG90"
        elif axis == 'Z':
            command = f"G91\nG0 Z{distance}\nG90"

        self.serial_manager.send_command(command)

    def park_machine(self):
        """Парковка станка"""
        # Перемещение в безопасную позицию
        commands = [
            "G91",  # Относительное позиционирование
            "G0 Z10",  # Поднять ось Z на 10мм
            "G90",  # Абсолютное позиционирование
            "G0 X0 Y0",  # Переместиться в начало координат
        ]
        for cmd in commands:
            self.serial_manager.send_command(cmd)

    def send_command(self, command):
        """Отправка команды на станок"""
        self.serial_manager.send_command(command)