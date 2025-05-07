import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtCore import Qt

from views.main_window import MainWindow
from models.telemetry_model import TelemetryModel
from models.connection_model import ConnectionModel
from models.settings_model import SettingsModel
from controllers.serial_controller import SerialController
from controllers.telemetry_controller import TelemetryController
from controllers.map_controller import MapController
from controllers.command_controller import CommandController
from controllers.radio_controller import RadioController
from views.panels.dashboard_panel import DashboardPanel
from utils.config import load_config

def setup_dark_theme(app):
    """Set up dark theme for the application"""
    # Set dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, Qt.black)
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, Qt.darkGray)
    palette.setColor(QPalette.AlternateBase, Qt.black)
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, Qt.darkGray)
    palette.setColor(QPalette.ButtonText, Qt.white)
    app.setPalette(palette)

def main():
    # Initialize application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern looking style
    
    # Set app icon
    icon_path = os.path.join('resources', 'balloon_icon.png')
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    
    # Set up dark theme
    setup_dark_theme(app)
    
    # Initialize MVC components
    settings = load_config()
    
    # Models
    telemetry_model = TelemetryModel()
    connection_model = ConnectionModel()
    settings_model = SettingsModel(settings)
    
    # Controllers
    serial_controller = SerialController(connection_model)
    telemetry_controller = TelemetryController(telemetry_model, serial_controller)
    map_controller = MapController(telemetry_model)
    command_controller = CommandController(serial_controller, settings_model)
    radio_controller = RadioController(telemetry_model)
    
    # Connect signals between components
    serial_controller.packet_received.connect(telemetry_controller.process_packet)
    
    # Main view
    main_window = MainWindow(
        telemetry_model,
        connection_model, 
        settings_model,
        serial_controller,
        command_controller,
        map_controller
    )
    
    # Create the dashboard panel with the telemetry model
    dashboard_panel = DashboardPanel(telemetry_model)
    
    # Connect the radio controller to the connection status in the dashboard
    radio_controller.register_connection_callback(dashboard_panel.update_connection_status)
    
    # Add the dashboard panel to your main window
    # main_window.add_panel(dashboard_panel)
    
    # Process command line arguments
    for arg in sys.argv:
        if arg.upper().startswith('COM'):
            # Auto-connect to specified port
            main_window.auto_connect(arg.upper())
        elif arg.lower() == 'testgps':
            # Enable GPS simulation
            telemetry_controller.enable_gps_simulation()
    
    # Display window and run event loop
    main_window.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())