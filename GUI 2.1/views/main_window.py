from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout,
    QHBoxLayout, QSplitter, QStatusBar, QLabel, QPushButton, QComboBox, QFrame, QAction, QMenuBar
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon

from views.panels.map_panel import MapPanel
from views.panels.dashboard_panel import DashboardPanel
from views.panels.plot_panel import PlotPanel
from views.panels.command_panel import CommandPanel
from views.panels.console_panel import ConsolePanel
from views.panels.tracking_panel import TrackingPanel
# from views.dialogs.settings_dialog import SettingsDialog # If you have a settings dialog

class MainWindow(QMainWindow):
    """Main application window, structured based on gui.py"""
    
    def __init__(self, telemetry_model, connection_model, settings_model,
                 serial_controller, command_controller, map_controller):
        super().__init__()
        
        self.telemetry_model = telemetry_model
        self.connection_model = connection_model
        self.settings_model = settings_model
        self.serial_controller = serial_controller
        self.command_controller = command_controller
        self.map_controller = map_controller
        
        self.setWindowTitle("HAB Ground Station") # Title from gui.py
        self.setMinimumSize(1200, 800) # Min size from gui.py
        # self.setGeometry(100, 100, 1200, 800) # Initial size and position

        # Set window icon (assuming icon is in 'resources' or root)
        icon_path = self.settings_model.get('app.icon', 'resources/balloon_icon.png')
        self.setWindowIcon(QIcon(icon_path))
        
        self.setup_ui()
        self.setup_status_bar() # Separate method for status bar
        self.setup_menu_bar() # Optional: Add a menu bar

        # Connect signals
        self.connection_model.connection_changed.connect(self.update_connection_status_display)
        self.serial_controller.connection_error.connect(self.show_error_message_in_statusbar)
        self.command_controller.command_log.connect(self.show_status_message_in_statusbar) # For command feedback
        
        # Telemetry updates to panels (already connected in original file, ensure they are correct)
        # self.telemetry_model.data_updated.connect(self.dashboard_panel.update_indicators_from_model) # dashboard handles its own connection
        # self.telemetry_model.data_updated.connect(self.plot_panel.update_plots_from_model) # plot_panel handles its own
        self.telemetry_model.position_updated.connect(self.dashboard_panel.vehicle_compass.setBearing) # Example: direct update if needed
        self.map_controller.bearing_calculated.connect(self.handle_bearing_updates)


    def setup_ui(self):
        """Set up the main UI layout based on gui.py."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget) # Main layout is Horizontal
        main_layout.setContentsMargins(5, 5, 5, 5) # Small margins
        main_layout.setSpacing(5)

        # Left side: Tab widget (Dashboard, Plots, Map, Console)
        left_v_layout = QVBoxLayout()
        
        # Tab widget for Dashboard, Plots, Map, Tracking, and Console
        self.tabs = QTabWidget()
        self.dashboard_panel = DashboardPanel(self.telemetry_model, self.connection_model, self)
        self.plot_panel = PlotPanel(self.telemetry_model, self.settings_model, self)
        self.map_panel = MapPanel(self.map_controller, self.telemetry_model, self.settings_model, self)
        self.tracking_panel = TrackingPanel(self.telemetry_model, self.map_controller, self)
        self.console_panel = ConsolePanel(self.serial_controller, self.settings_model, self)
        
        self.tabs.addTab(self.dashboard_panel, "Dashboard")
        self.tabs.addTab(self.plot_panel, "Plots")
        self.tabs.addTab(self.map_panel, "Map")
        self.tabs.addTab(self.tracking_panel, "Tracking")
        self.tabs.addTab(self.console_panel, "Console")  # Console is now its own tab
        left_v_layout.addWidget(self.tabs, 1) # Give full stretch to tabs

        # Right side: Command Panel
        self.command_panel = CommandPanel(
            self.command_controller, self.serial_controller,
            self.connection_model, self.settings_model, self
        )
        # Set a fixed width for the command panel as in gui.py
        self.command_panel.setFixedWidth(self.settings_model.get('panels.command_width', 300))

        # Splitter to manage left and right sections
        splitter = QSplitter(Qt.Horizontal)
        
        left_widget = QWidget() # Container for left_v_layout
        left_widget.setLayout(left_v_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(self.command_panel)
        
        # Set initial splitter sizes (e.g., 70% left, 30% right)
        # Adjust these values based on preference
        total_width = self.width()
        left_width = int(total_width * 0.7)
        right_width = total_width - left_width
        splitter.setSizes([left_width if left_width > 0 else 700, 
                           right_width if right_width > 0 else 300])


        main_layout.addWidget(splitter)

    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_msg_label = QLabel("Ready.")
        self.connection_status_label = QLabel("Not Connected")
        self.connection_status_label.setStyleSheet("color: #ff5500; font-weight: bold;")
        
        self.status_bar.addWidget(self.status_msg_label, 1) # Add with stretch factor
        self.status_bar.addPermanentWidget(self.connection_status_label)

    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu('&File')
        # settings_action = QAction('&Settings', self)
        # settings_action.triggered.connect(self.open_settings_dialog)
        # file_menu.addAction(settings_action)
        exit_action = QAction('&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View Menu (example)
        # view_menu = menubar.addMenu('&View')
        # toggle_command_panel_action = QAction('Toggle Command Panel', self, checkable=True)
        # toggle_command_panel_action.setChecked(True)
        # toggle_command_panel_action.triggered.connect(lambda checked: self.command_panel.setVisible(checked))
        # view_menu.addAction(toggle_command_panel_action)


    def update_connection_status_display(self, connected, port_name=""):
        if connected:
            self.connection_status_label.setText(f"Connected to {port_name}")
            self.connection_status_label.setStyleSheet("color: #00cc00; font-weight: bold;") # Bright Green
            self.show_status_message_in_statusbar(f"Successfully connected to {port_name}.")
        else:
            self.connection_status_label.setText("Not Connected")
            self.connection_status_label.setStyleSheet("color: #ff5500; font-weight: bold;") # Orange-Red
            if hasattr(self, '_last_port_name') and self._last_port_name: # Check if previously connected
                 self.show_status_message_in_statusbar(f"Disconnected from {self._last_port_name}.")
            else:
                 self.show_status_message_in_statusbar("Disconnected.")
        self._last_port_name = port_name if connected else ""


    def show_error_message_in_statusbar(self, message):
        self.status_msg_label.setText(f"Error: {message}")
        self.status_msg_label.setStyleSheet("color: #ff3333;") # Red for errors
        QTimer.singleShot(8000, self.reset_status_message) # Longer display for errors

    def show_status_message_in_statusbar(self, message):
        self.status_msg_label.setText(message)
        self.status_msg_label.setStyleSheet("color: white;") # Default color
        QTimer.singleShot(5000, self.reset_status_message)

    def reset_status_message(self):
        self.status_msg_label.setText("Ready.")
        self.status_msg_label.setStyleSheet("color: white;")
    
    def auto_connect(self, port_to_connect):
        """Auto-connect to specified port, similar to gui.py."""
        # CommandPanel's port_selector handles the list of ports
        # We need to tell CommandPanel to select and connect.
        if self.command_panel:
            ports = [self.command_panel.port_selector.itemText(i) for i in range(self.command_panel.port_selector.count())]
            if port_to_connect in ports:
                self.command_panel.port_selector.setCurrentText(port_to_connect)
                # Give a slight delay for UI to settle before auto-connecting
                QTimer.singleShot(200, self.command_panel.toggle_connection) 
                self.show_status_message_in_statusbar(f"Attempting auto-connect to {port_to_connect}...")
            else:
                self.show_error_message_in_statusbar(f"Auto-connect: Port {port_to_connect} not found.")
    
    # def open_settings_dialog(self):
    #     dialog = SettingsDialog(self.settings_model, self)
    #     dialog.exec_()

    def handle_bearing_updates(self, bearing_value, bearing_type):
        if bearing_type == "vehicle_heading": # Or whatever string MapController sends
            self.dashboard_panel.vehicle_compass.setBearing(bearing_value)
        elif bearing_type == "target_bearing":
            self.dashboard_panel.target_compass.setBearing(bearing_value)

    def closeEvent(self, event):
        # Ensure disconnection on close
        if self.serial_controller.is_connected():
            self.serial_controller.disconnect()
        # Add any other cleanup (e.g., stopping timers, threads)
        super().closeEvent(event)