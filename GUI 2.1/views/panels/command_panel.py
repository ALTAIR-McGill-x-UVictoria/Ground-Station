from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QComboBox, QGroupBox, QSlider, QSpinBox, 
    QLineEdit, QFrame # Removed QCheckBox
)
from PyQt5.QtCore import Qt # Removed QTimer

class CommandPanel(QWidget):
    """Panel for sending commands, structured like gui.py"""
    
    def __init__(self, command_controller, serial_controller, 
                 connection_model, settings_model, parent=None):
        super().__init__(parent)
        self.command_controller = command_controller
        self.serial_controller = serial_controller
        self.connection_model = connection_model
        self.settings_model = settings_model
        
        # Set up UI
        self.setup_ui()
        
        # Connect signals
        self.connection_model.connection_changed.connect(self.update_button_states)
        # Initialize button states
        self.update_button_states(self.connection_model.is_connected())

    def setup_ui(self):
        """Set up the command panel UI based on gui.py."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Connection section
        self.create_connection_section(layout)
        layout.addWidget(self.create_separator())
        
        # SD card control section
        self.create_sd_control_section(layout)
        layout.addWidget(self.create_separator())
        
        # LED control section
        self.create_led_control_section(layout, "LED Control", "LED", 
                                        self.send_led_intensity_command, self.send_led_blink_command)
        layout.addWidget(self.create_separator())
        
        # Source LED control section
        self.create_led_control_section(layout, "Source Control", "Source",
                                        self.send_source_intensity_command, self.send_source_blink_command)
        layout.addWidget(self.create_separator())

        # System control section (Ping)
        self.create_system_control_section(layout)
        layout.addWidget(self.create_separator())

        # Manual command section
        self.create_manual_command_section(layout)
        
        layout.addStretch(1) # Push all groups to the top
        
        self.update_button_states(self.connection_model.is_connected())

    def create_separator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        return separator

    def create_connection_section(self, parent_layout):
        group = QGroupBox("Connection")
        layout = QVBoxLayout(group)
        
        # Serial port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Serial Port:"))
        self.port_selector = QComboBox()
        self.refresh_ports()
        port_layout.addWidget(self.port_selector, 1)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_ports)
        port_layout.addWidget(refresh_button)
        layout.addLayout(port_layout)
        
        # Mount COM port selection
        mount_layout = QHBoxLayout()
        mount_layout.addWidget(QLabel("Mount COM:"))
        self.mount_port_selector = QComboBox()
        self.refresh_mount_ports()
        mount_layout.addWidget(self.mount_port_selector, 1)
        
        mount_refresh_button = QPushButton("Refresh")
        mount_refresh_button.clicked.connect(self.refresh_mount_ports)
        mount_layout.addWidget(mount_refresh_button)
        layout.addLayout(mount_layout)
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_button)
        
        parent_layout.addWidget(group)

    def create_sd_control_section(self, parent_layout):
        group = QGroupBox("SD Card Control")
        layout = QVBoxLayout(group)
        
        self.sd_activate_button = QPushButton("Activate SD Logging")
        self.sd_activate_button.clicked.connect(self.activate_sd_logging)
        layout.addWidget(self.sd_activate_button)
        
        parent_layout.addWidget(group)

    def create_led_control_section(self, parent_layout, group_title, led_prefix, intensity_cmd_func, blink_cmd_func):
        group = QGroupBox(group_title)
        layout = QVBoxLayout(group)
        
        # Intensity Control
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(QLabel("Intensity:"))
        
        led_intensity_spinbox = QSpinBox()
        led_intensity_spinbox.setRange(0, 255)
        setattr(self, f"{led_prefix.lower()}_intensity_spinbox", led_intensity_spinbox) # e.g., self.led_intensity_spinbox
        intensity_layout.addWidget(led_intensity_spinbox)
        
        set_intensity_button = QPushButton(f"Set {led_prefix} Intensity")
        set_intensity_button.clicked.connect(intensity_cmd_func)
        setattr(self, f"{led_prefix.lower()}_set_intensity_button", set_intensity_button)
        intensity_layout.addWidget(set_intensity_button)
        layout.addLayout(intensity_layout)
        
        # Blink Control
        blink_layout = QHBoxLayout()
        blink_layout.addWidget(QLabel("Delay (ms):"))
        
        blink_delay_spinbox = QSpinBox()
        blink_delay_spinbox.setRange(100, 2000)
        blink_delay_spinbox.setSingleStep(100)
        blink_delay_spinbox.setValue(500)
        setattr(self, f"{led_prefix.lower()}_blink_delay_spinbox", blink_delay_spinbox)
        blink_layout.addWidget(blink_delay_spinbox)
        
        blink_led_button = QPushButton(f"Blink {led_prefix}")
        blink_led_button.clicked.connect(blink_cmd_func)
        setattr(self, f"{led_prefix.lower()}_blink_button", blink_led_button)
        blink_layout.addWidget(blink_led_button)
        layout.addLayout(blink_layout)
        
        parent_layout.addWidget(group)

    def create_system_control_section(self, parent_layout):
        group = QGroupBox("System Control")
        layout = QVBoxLayout(group)
        
        self.ping_button = QPushButton("Ping Flight Computer")
        self.ping_button.clicked.connect(self.send_ping_command)
        layout.addWidget(self.ping_button)
        
        parent_layout.addWidget(group)

    def create_manual_command_section(self, parent_layout):
        group = QGroupBox("Manual Command")
        layout = QVBoxLayout(group)
        
        manual_input_layout = QHBoxLayout()
        self.manual_command_input = QLineEdit()
        self.manual_command_input.setPlaceholderText("Enter command...")
        self.manual_command_input.returnPressed.connect(self.send_manual_command_text) # Send on Enter
        manual_input_layout.addWidget(self.manual_command_input)
        
        self.send_manual_button = QPushButton("Send")
        self.send_manual_button.clicked.connect(self.send_manual_command_text)
        manual_input_layout.addWidget(self.send_manual_button)
        layout.addLayout(manual_input_layout)
        
        parent_layout.addWidget(group)

    def refresh_ports(self):
        self.port_selector.clear()
        ports = self.serial_controller.get_available_ports()
        self.port_selector.addItems(ports)
        if self.connection_model.get_port():
            index = self.port_selector.findText(self.connection_model.get_port())
            if index >= 0:
                self.port_selector.setCurrentIndex(index)

    def refresh_mount_ports(self):
        """Refresh the mount COM port selector"""
        current_port = self.mount_port_selector.currentText()
        self.mount_port_selector.clear()
        
        # Get available ports
        ports = self.serial_controller.get_available_ports()
        self.mount_port_selector.addItems(ports)
        
        # Set default to COM10 if available, otherwise restore previous selection
        if "COM10" in ports:
            index = self.mount_port_selector.findText("COM10")
            self.mount_port_selector.setCurrentIndex(index)
        elif current_port and current_port in ports:
            index = self.mount_port_selector.findText(current_port)
            self.mount_port_selector.setCurrentIndex(index)
        
    def get_selected_mount_port(self):
        """Get the currently selected mount COM port"""
        return self.mount_port_selector.currentText() if hasattr(self, 'mount_port_selector') else "COM10"

    def toggle_connection(self):
        if not self.connection_model.is_connected():
            port = self.port_selector.currentText()
            if port:
                baud_rate = self.settings_model.get('serial.baud_rate', 115200) # Default from gui.py
                self.serial_controller.connect(port, baud_rate)
        else:
            self.serial_controller.disconnect()

    def update_button_states(self, connected):
        self.connect_button.setText("Disconnect" if connected else "Connect")
        self.port_selector.setEnabled(not connected)

        # Enable/disable all command buttons based on connection
        self.sd_activate_button.setEnabled(connected)
        
        self.led_set_intensity_button.setEnabled(connected)
        self.led_blink_button.setEnabled(connected)
        self.source_set_intensity_button.setEnabled(connected)
        self.source_blink_button.setEnabled(connected)
        
        self.ping_button.setEnabled(connected)
        self.send_manual_button.setEnabled(connected)
        self.manual_command_input.setEnabled(connected)

    def activate_sd_logging(self):
        self.command_controller.activate_sd()

    def send_led_intensity_command(self):
        intensity = self.led_intensity_spinbox.value()
        self.command_controller.send_led_command(intensity)

    def send_led_blink_command(self):
        delay = self.led_blink_delay_spinbox.value()
        self.command_controller.send_blink_command(delay)

    def send_source_intensity_command(self):
        intensity = self.source_intensity_spinbox.value()
        self.command_controller.send_source_command(intensity)

    def send_source_blink_command(self):
        delay = self.source_blink_delay_spinbox.value()
        self.command_controller.send_source_blink_command(delay)

    def send_ping_command(self):
        self.command_controller.send_ping()

    def send_manual_command_text(self):
        command = self.manual_command_input.text().strip()
        if command:
            self.command_controller.send_command(command)
            # self.manual_command_input.clear() # Optional: clear after sending