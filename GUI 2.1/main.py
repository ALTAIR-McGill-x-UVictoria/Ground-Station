import sys
import os
import subprocess
import threading
import re
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtCore import Qt

from views.main_window import MainWindow
from models.telemetry_model import TelemetryModel
from models.connection_model import ConnectionModel
from models.settings_model import SettingsModel
# from controllers.event_controller import EventController
from controllers.serial_controller import SerialController
from controllers.telemetry_controller import TelemetryController
from controllers.map_controller import MapController
from controllers.command_controller import CommandController
from utils.config import load_config

class SDRController:
    def __init__(self, telemetry_model):
        self.telemetry_model = telemetry_model
        self.process = None
        self.running = False
        
    def start_sdr(self):
        """Start the LoRa SDR decoder in a separate thread"""
        self.running = True
        self.thread = threading.Thread(target=self._run_sdr)
        self.thread.daemon = True  # Make thread terminate when main program exits
        self.thread.start()
        
    def stop_sdr(self):
        """Stop the LoRa SDR decoder"""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process = None
            
    def _run_sdr(self):
        """Run lora.py and process its output"""
        try:
            # Start the lora.py process with unbuffered output
            self.process = subprocess.Popen(
                [sys.executable, "-u", "lora.py"],  # -u for unbuffered Python output
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,  # Use unbuffered mode
                universal_newlines=True
            )
            
            # Process output from the SDR decoder
            while self.running and self.process.poll() is None:
                line = self.process.stdout.readline().strip()
                if not line:
                    continue
                    
                print(f"SDR: {line}")  # Echo SDR output to console
                
                # Check if this is a radio packet line - more flexible matching
                if "rx msg" in line.lower():
                    # Extract everything after "rx msg:"
                    parts = line.split("rx msg:", 1)
                    if len(parts) > 1:
                        packet_data = parts[1].strip()
                        print(f"Found packet: {packet_data}")
                        self._process_packet(packet_data)
                
        except Exception as e:
            print(f"SDR Error: {e}")
        finally:
            if self.process:
                self.process.terminate()
                
    def _process_packet(self, packet_data):
        """Process a received packet according to radioPacket structure"""
        try:
            # More aggressive cleaning - first remove the problematic characters
            clean_data = packet_data.replace('ÿ', '')
            
            # Then clean any remaining non-printable characters
            clean_data = re.sub(r'[^\x20-\x7E,.-]', '', clean_data)
            print(f"Cleaned packet data: {clean_data}")
            
            # Split the comma-separated values
            values = clean_data.split(',')
            if len(values) < 19:
                print(f"Invalid packet format (not enough values): {clean_data}")
                return
                
            # Parse values according to the radioPacket structure
            try:
                packet = {
                    # Communication data
                    'ack': int(values[0]) if values[0].strip() else 0,
                    'RSSI': int(values[1]) if values[1].strip() else 0,
                    'SNR': int(values[2]) if values[2].strip() else 0,
                    # IMU data
                    'fRoll': float(values[3]) if values[3].strip() else 0.0,
                    'fPitch': float(values[4]) if values[4].strip() else 0.0,
                    'fYaw': float(values[5]) if values[5].strip() else 0.0,
                    'Pressure': float(values[6]) if values[6].strip() else 0.0,
                    'Temperature': float(values[7]) if values[7].strip() else 0.0,
                    'Altitude': float(values[8]) if values[8].strip() else 0.0,
                    # System status
                    'SDStatus': bool(int(values[9])) if values[9].strip() else False,
                    'actuatorStatus': bool(int(values[10])) if values[10].strip() else False,
                    'photodiodeValue1': int(values[11]) if values[11].strip() else 0,
                    'photodiodeValue2': int(values[12]) if values[12].strip() else 0,
                    # GPS data
                    'gpsLat': float(values[13]) if values[13].strip() else 0.0,
                    'gpsLon': float(values[14]) if values[14].strip() else 0.0,
                    'gpsAlt': float(values[15]) if values[15].strip() else 0.0,
                    'gpsSpeed': float(values[16]) if values[16].strip() else 0.0,
                    'gpsTime': float(values[17]) if values[17].strip() else 0.0,
                    'gpsValid': bool(int(values[18])) if values[18].strip() else False
                }
                
                print("Successfully parsed packet")
                # Update telemetry model with the received data
                self.telemetry_model.update_from_sdr(packet)
                
            except (ValueError, IndexError) as e:
                print(f"Error converting values: {e}")
                # Try to show which value caused the problem
                for i, val in enumerate(values):
                    try:
                        if i < 3 or (9 <= i <= 12) or i == 18:
                            int(val)
                        else:
                            float(val)
                    except ValueError:
                        print(f"Value at index {i} is invalid: '{val}'")
                
        except Exception as e:
            print(f"Error parsing packet: {e} in data: {packet_data}")

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
    telemetry_controller = TelemetryController(telemetry_model)
    map_controller = MapController(telemetry_model, settings_model)
    command_controller = CommandController(serial_controller, settings_model)
    sdr_controller = SDRController(telemetry_model)
    
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
    
    # Process command line arguments
    for arg in sys.argv:
        if arg.upper().startswith('COM'):
            # Auto-connect to specified port
            main_window.auto_connect(arg.upper())
        elif arg.lower() == 'testgps':
            # Enable GPS simulation
            telemetry_controller.enable_gps_simulation()
        elif arg.lower() == 'sdr':
            # Start SDR mode
            print("Starting SDR mode...")
            sdr_controller.start_sdr()
    
    # Display window and run event loop
    main_window.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())