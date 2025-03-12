from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout,
    QHBoxLayout, QSplitter, QStatusBar, QLabel
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon

from views.panels.map_panel import MapPanel
from views.panels.dashboard_panel import DashboardPanel
from views.panels.plot_panel import PlotPanel
from views.panels.command_panel import CommandPanel
from views.panels.console_panel import ConsolePanel

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, telemetry_model, connection_model, settings_model,
                 serial_controller, command_controller, map_controller):
        super().__init__()
        
        # Store controllers and models
        self.telemetry_model = telemetry_model
        self.connection_model = connection_model
        self.settings_model = settings_model
        self.serial_controller = serial_controller
        self.command_controller = command_controller
        self.map_controller = map_controller
        
        # Set window properties
        self.setWindowTitle("Flight Computer Ground Station")
        self.setMinimumSize(1200, 800)
        
        # Set up UI components
        self.setup_ui()
        
        # Set up status bar
        self.status_bar = QStatusBar()
        self.status_msg = QLabel("Ready")
        self.connection_status = QLabel("Not Connected")
        self.connection_status.setStyleSheet("color: #ff5500;")
        self.status_bar.addWidget(self.status_msg)
        self.status_bar.addPermanentWidget(self.connection_status)
        self.setStatusBar(self.status_bar)
        
        # Connect signals
        self.connection_model.connection_changed.connect(self.update_connection_status)
        self.serial_controller.connection_error.connect(self.show_error_message)
        self.command_controller.command_log.connect(self.show_status_message)
        
    def setup_ui(self):
        """Set up the main UI layout"""
        # Main central widget
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(central)
        
        # Create left-right splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left side - Tab widget
        self.tabs = QTabWidget()
        
        # Create tabs for different views
        self.dashboard_panel = DashboardPanel(self.telemetry_model, self.settings_model)
        self.plot_panel = PlotPanel(self.telemetry_model, self.settings_model)
        self.map_panel = MapPanel(self.map_controller, self.telemetry_model)
        self.console_panel = ConsolePanel(self.serial_controller, self.settings_model)
        
        # Add tabs
        self.tabs.addTab(self.dashboard_panel, "Dashboard")
        self.tabs.addTab(self.plot_panel, "Plots")
        self.tabs.addTab(self.map_panel, "Map")
        self.tabs.addTab(self.console_panel, "Console")
        
        # Right side - Command panel
        self.command_panel = CommandPanel(
            self.command_controller,
            self.serial_controller,
            self.connection_model,
            self.settings_model
        )
        
        # Add widgets to splitter
        splitter.addWidget(self.tabs)
        splitter.addWidget(self.command_panel)
        
        # Set splitter sizes (70% left, 30% right)
        splitter.setSizes([700, 300])
    
    def update_connection_status(self, connected):
        """Update the connection status indicator"""
        if connected:
            self.connection_status.setText(f"Connected to {self.connection_model.port}")
            self.connection_status.setStyleSheet("color: #00ff00;")
        else:
            self.connection_status.setText("Not Connected")
            self.connection_status.setStyleSheet("color: #ff5500;")
    
    def show_error_message(self, message):
        """Show an error message in the status bar"""
        self.status_msg.setText(message)
        self.status_msg.setStyleSheet("color: #ff5500;")
        
        # Reset status after 5 seconds
        QTimer.singleShot(5000, self.reset_status)
    
    def show_status_message(self, message):
        """Show a status message in the status bar"""
        self.status_msg.setText(message)
        self.status_msg.setStyleSheet("color: white;")
        
        # Reset status after 5 seconds
        QTimer.singleShot(5000, self.reset_status)
    
    def reset_status(self):
        """Reset the status message"""
        self.status_msg.setText("Ready")
        self.status_msg.setStyleSheet("color: white;")
    
    def auto_connect(self, port):
        """Auto-connect to specified port at startup"""
        # Find port in the command panel's combo box
        index = -1
        for i in range(self.command_panel.port_selector.count()):
            if self.command_panel.port_selector.itemText(i) == port:
                index = i
                break
        
        if index >= 0:
            self.command_panel.port_selector.setCurrentIndex(index)
            self.command_panel.toggle_connection()
        else:
            self.status_msg.setText(f"Port {port} not found")