import time
import random
import math
import struct
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from models.telemetry_model import TelemetryModel

class TelemetryController(QObject):
    """Controller for processing telemetry data"""
    
    # Define signals
    packet_parsed = pyqtSignal(bool, str)  # Success flag, message
    gps_updated = pyqtSignal(float, float, float)  # lat, lon, alt
    
    def __init__(self, telemetry_model, serial_controller=None):
        super().__init__()
        self.telemetry_model = telemetry_model
        self.serial_controller = serial_controller
        self.logger = logging.getLogger(__name__)
        self.telemetry_callbacks = []
        
        # Connect to serial controller if provided
        if self.serial_controller:
            self.serial_controller.register_data_callback(self.process_binary_packet)
            self.serial_controller.packet_received.connect(self.process_text_packet)
        
        # GPS simulation variables
        self.gps_simulation = False
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.update_sim_gps)
        self.sim_lat = 45.505623
        self.sim_lon = -73.575737
        self.sim_alt = 150
        self.sim_angle = 0
        self.sim_vertical_speed = 0
    
    def set_serial_controller(self, serial_controller):
        """Set the serial controller and register callback"""
        self.serial_controller = serial_controller
        self.serial_controller.register_data_callback(self.process_binary_packet)
    
    def register_telemetry_callback(self, callback):
        """Register a callback to be called when telemetry data is updated"""
        self.telemetry_callbacks.append(callback)
    
    def process_binary_packet(self, data, packet_type):
        """Process binary packet from serial controller"""
        if packet_type == "control_to_power":
            self.telemetry_model.parse_control_to_power_packet(data)
        elif packet_type == "power_to_control":
            self.telemetry_model.parse_power_to_control_packet(data)
        else:
            self.logger.warning(f"Unknown packet type: {packet_type}")
    
    def process_text_packet(self, text_data):
        """Process text packet (CSV format) for backward compatibility"""
        try:
            # Split by comma and parse values
            values = text_data.split(',')
            # Process according to format (implement as needed)
            pass
        except Exception as e:
            self.logger.error(f"Error processing text packet: {e}")
    
    def process_packet(self, data):
        """Process any packet (called from main.py)"""
        # Try to determine packet type and parse accordingly
        if isinstance(data, bytes) or isinstance(data, bytearray):
            # Binary packet - try to detect type
            if len(data) >= 0x34:  # Minimum size for Control to Power
                self.telemetry_model.parse_control_to_power_packet(data)
            elif len(data) >= 0x11:  # Minimum size for Power to Control
                self.telemetry_model.parse_power_to_control_packet(data)
        elif isinstance(data, str):
            # Text packet
            self.process_text_packet(data)
    
    def get_telemetry_data(self):
        """Get the current telemetry data"""
        return self.telemetry_model.get_telemetry_data()
    
    def enable_gps_simulation(self, enable=True):
        """Enable or disable GPS simulation"""
        self.gps_simulation = enable
        if enable and not self.sim_timer.isActive():
            self.sim_timer.start(1000)  # Update every second
        elif not enable and self.sim_timer.isActive():
            self.sim_timer.stop()
    
    def update_sim_gps(self):
        """Update simulated GPS position"""
        if not self.gps_simulation:
            return
            
        # Store previous position for reference
        prev_lat = self.sim_lat
        prev_lon = self.sim_lon
        
        # Randomly adjust direction
        self.sim_angle += random.uniform(-30, 30)
        
        # Calculate new position
        lat_change = math.cos(math.radians(self.sim_angle)) * 0.0001
        lon_change = math.sin(math.radians(self.sim_angle)) * 0.0001
        self.sim_lat += lat_change
        self.sim_lon += lon_change
        
        # Update vertical speed with random changes
        self.sim_vertical_speed += random.uniform(-0.5, 0.5)
        self.sim_vertical_speed = max(-5, min(5, self.sim_vertical_speed))
        
        # Update altitude based on vertical speed
        self.sim_alt += self.sim_vertical_speed
        self.sim_alt = max(50, min(500, self.sim_alt))
        
        # Create simulated telemetry packet
        telemetry = {
            'ack': 0,
            'rssi': random.randint(-90, -60),
            'snr': random.randint(8, 15),
            'roll': random.uniform(-20, 20),
            'pitch': random.uniform(-20, 20),
            'yaw': random.uniform(0, 360),
            'pressure': 1013.25 - self.sim_alt * 0.12,
            'temperature': 20 - self.sim_alt * 0.006,
            'altitude': self.sim_alt,
            'sd_status': True,
            'led_status': False,
            'source_status': False,
            'actuator_status': False,
            'gps_lat': self.sim_lat,
            'gps_lon': self.sim_lon,
            'gps_alt': self.sim_alt,
            'ground_speed': math.sqrt(lat_change**2 + lon_change**2) * 111000,
            'gps_time': float(time.strftime("%H%M%S")),
            'gps_valid': True
        }
        
        # Update model with simulated data
        self.telemetry_model.update_telemetry(telemetry)
        self.telemetry_model.update_signal(telemetry['rssi'], telemetry['snr'])
        
        # Emit GPS update signal
        self.gps_updated.emit(self.sim_lat, self.sim_lon, self.sim_alt)
    
    def enable_gps_simulation(self):
        """Enable GPS data simulation for testing"""
        # Implementation for GPS simulation if needed
        pass