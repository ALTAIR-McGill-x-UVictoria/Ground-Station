from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QComboBox, QGroupBox, QSlider, QSpinBox, 
    QCheckBox, QLineEdit, QFrame
)
from PyQt5.QtCore import Qt, QTimer

class CommandPanel(QWidget):
    """Panel for sending commands to the flight computer"""
    
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
    
    def setup_ui(self):
        """Set up the command panel UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Connection section
        self.create_connection_section(layout)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # LED control section
        self.create_led_control_section(layout)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Source LED control section
        self.create_source_control_section(layout)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # SD card control section
        self.create_sd_control_section(layout)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Other commands section
        self.create_other_commands_section(layout)
        
        # Stretch to fill remaining space
        layout.addStretch(1)
        
        # Set initial button states
        self.update_button_states(self.connection_model.connected)
    
    def create_connection_section(self, parent_layout):
        """Create connection control section"""
        group = QGroupBox("Connection")
        layout = QVBoxLayout(group)
        
        # Port selection row
        port_layout = QHBoxLayout()
        port_label = QLabel("Port:")
        self.port_selector = QComboBox()
        self.refresh_ports()
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_selector, 1)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_ports)
        port_layout.addWidget(refresh_button)
        layout.addLayout(port_layout)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_button)
        
        parent_layout.addWidget(group)
    
    def create_led_control_section(self, parent_layout):
        """Create LED control section"""
        group = QGroupBox("LED Control")
        layout = QVBoxLayout(group)
        
        # LED intensity slider
        intensity_layout = QHBoxLayout()
        intensity_label = QLabel("Intensity:")
        self.led_slider = QSlider(Qt.Horizontal)
        self.led_slider.setRange(0, 255)
        self.led_slider.setValue(0)
        
        self.led_value = QSpinBox()
        self.led_value.setRange(0, 255)
        self.led_value.setValue(0)
        
        # Connect slider and spin box
        self.led_slider.valueChanged.connect(self.led_value.setValue)
        self.led_value.valueChanged.connect(self.led_slider.setValue)
        
        intensity_layout.addWidget(intensity_label)
        intensity_layout.addWidget(self.led_slider, 1)
        intensity_layout.addWidget(self.led_value)
        layout.addLayout(intensity_layout)
        
        # LED set button
        self.led_set_button = QPushButton("Set LED Intensity")
        self.led_set_button.clicked.connect(self.set_led_intensity)
        layout.addWidget(self.led_set_button)
        
        # LED blink controls
        blink_layout = QHBoxLayout()
        blink_label = QLabel("Blink (ms):")
        self.led_blink_value = QSpinBox()
        self.led_blink_value.setRange(100, 2000)
        self.led_blink_value.setValue(500)
        self.led_blink_value.setSingleStep(100)
        
        blink_layout.addWidget(blink_label)
        blink_layout.addWidget(self.led_blink_value, 1)
        
        self.led_blink_button = QPushButton("Blink LED")
        self.led_blink_button.clicked.connect(self.set_led_blink)
        
        layout.addLayout(blink_layout)
        layout.addWidget(self.led_blink_button)
        
        parent_layout.addWidget(group)
    
    def create_source_control_section(self, parent_layout):
        """Create source LED control section"""
        group = QGroupBox("Source LED Control")
        layout = QVBoxLayout(group)
        
        # Source intensity slider
        intensity_layout = QHBoxLayout()
        intensity_label = QLabel("Intensity:")
        self.source_slider = QSlider(Qt.Horizontal)
        self.source_slider.setRange(0, 255)
        self.source_slider.setValue(0)
        
        self.source_value = QSpinBox()
        self.source_value.setRange(0, 255)
        self.source_value.setValue(0)
        
        # Connect slider and spin box
        self.source_slider.valueChanged.connect(self.source_value.setValue)
        self.source_value.valueChanged.connect(self.source_slider.setValue)
        
        intensity_layout.addWidget(intensity_label)
        intensity_layout.addWidget(self.source_slider, 1)
        intensity_layout.addWidget(self.source_value)
        layout.addLayout(intensity_layout)
        
        # Source set button
        self.source_set_button = QPushButton("Set Source LED")
        self.source_set_button.clicked.connect(self.set_source_intensity)
        layout.addWidget(self.source_set_button)
        
        # Source blink controls
        blink_layout = QHBoxLayout()
        blink_label = QLabel("Blink (ms):")
        self.source_blink_value = QSpinBox()
        self.source_blink_value.setRange(100, 2000)
        self.source_blink_value.setValue(500)
        self.source_blink_value.setSingleStep(100)
        
        blink_layout.addWidget(blink_label)
        blink_layout.addWidget(self.source_blink_value, 1)
        
        self.source_blink_button = QPushButton("Blink Source")
        self.source_blink_button.clicked.connect(self.set_source_blink)
        
        layout.addLayout(blink_layout)
        layout.addWidget(self.source_blink_button)
        
        parent_layout.addWidget(group)
    
    def create_sd_control_section(self, parent_layout):
        """Create SD card control section"""
        group = QGroupBox("SD Card Control")
        layout = QVBoxLayout(group)
        
        # SD card activate button
        self.sd_activate_button = QPushButton("Activate SD Logging")
        self.sd_activate_button.clicked.connect(self.activate_sd)
        layout.addWidget(self.sd_activate_button)
        
        parent_layout.addWidget(group)
    
    def create_other_commands_section(self, parent_layout):
        """Create other commands section"""
        group = QGroupBox("Other Commands")
        layout = QVBoxLayout(group)
        
        # Custom command
        command_layout = QHBoxLayout()
        self.custom_command = QLineEdit()
        self.custom_command.setPlaceholderText("Enter custom command...")
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_custom_command)
        
        command_layout.addWidget(self.custom_command, 1)
        command_layout.addWidget(self.send_button)
        layout.addLayout(command_layout)
        
        # Ping button
        self.ping_button = QPushButton("Ping Flight Computer")
        self.ping_button.clicked.connect(self.send_ping)
        layout.addWidget(self.ping_button)
        
        parent_layout.addWidget(group)
    
    def refresh_ports(self):
        """Refresh the list of available serial ports"""
        self.port_selector.clear()
        
        # Get available ports from the serial controller
        ports = self.serial_controller.get_available_ports()
        self.port_selector.addItems(ports)
        
        # Select previous port if it's still available
        if self.connection_model.port:
            index = self.port_selector.findText(self.connection_model.port)
            if index >= 0:
                self.port_selector.setCurrentIndex(index)
    
    def toggle_connection(self):
        """Toggle serial connection"""
        if not self.connection_model.connected:
            # Connect
            port = self.port_selector.currentText()
            if port:
                baud_rate = self.settings_model.get('serial.baud_rate', 115200)
                success = self.serial_controller.connect(port, baud_rate)
                if success:
                    self.connect_button.setText("Disconnect")
        else:
            # Disconnect
            self.serial_controller.disconnect()
            self.connect_button.setText("Connect")
    
    def update_button_states(self, connected):
        """Update button states based on connection status"""
        # Update connect button text
        self.connect_button.setText("Disconnect" if connected else "Connect")
        
        # Enable/disable command buttons
        self.led_set_button.setEnabled(connected)
        self.led_blink_button.setEnabled(connected)
        self.source_set_button.setEnabled(connected)
        self.source_blink_button.setEnabled(connected)
        self.sd_activate_button.setEnabled(connected)
        self.send_button.setEnabled(connected)
        self.ping_button.setEnabled(connected)
    
    def set_led_intensity(self):
        """Set LED intensity"""
        intensity = self.led_value.value()
        self.command_controller.send_led_command(intensity)
    
    def set_led_blink(self):
        """Set LED blink rate"""
        delay_ms = self.led_blink_value.value()
        self.command_controller.send_blink_command(delay_ms)
    
    def set_source_intensity(self):
        """Set source LED intensity"""
        intensity = self.source_value.value()
        self.command_controller.send_source_command(intensity)
    
    def set_source_blink(self):
        """Set source LED blink rate"""
        delay_ms = self.source_blink_value.value()
        self.command_controller.send_source_blink_command(delay_ms)
    
    def activate_sd(self):
        """Activate SD card logging"""
        self.command_controller.activate_sd()
    
    def send_custom_command(self):
        """Send custom command"""
        command = self.custom_command.text().strip()
        if command:
            self.command_controller.send_command(command)
            self.custom_command.clear()
    
    def send_ping(self):
        """Send ping command"""
        self.command_controller.send_ping()