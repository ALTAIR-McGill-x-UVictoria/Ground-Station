import time
import random
import math
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class TelemetryController(QObject):
    """Controller for processing telemetry data"""
    
    # Define signals
    packet_parsed = pyqtSignal(bool, str)  # Success flag, message
    gps_updated = pyqtSignal(float, float, float)  # lat, lon, alt
    
    def __init__(self, telemetry_model):
        super().__init__()
        self.telemetry_model = telemetry_model
        
        # GPS simulation variables
        self.gps_simulation = False
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.update_sim_gps)
        self.sim_lat = 45.505623
        self.sim_lon = -73.575737
        self.sim_alt = 150
        self.sim_angle = 0
        self.sim_vertical_speed = 0
    
    def process_packet(self, packet):
        """Process incoming telemetry packet"""
        try:
            # Split packet into values
            values = packet.strip().split(',')
            
            # Check for short packet (RSSI/SNR only)
            if 2 <= len(values) < 17:
                try:
                    rssi = int(values[0])
                    snr = int(values[1])
                    
                    # Update model with signal strength
                    self.telemetry_model.update_signal(rssi, snr)
                    
                    # Emit success signal
                    self.packet_parsed.emit(True, "Signal data received")
                    return True
                except ValueError:
                    self.packet_parsed.emit(False, "Invalid signal format")
                    return False
            
            # Full telemetry packet
            elif len(values) == 17:
                try:
                    # Parse complete telemetry data
                    telemetry = {
                        'ack': int(values[0]),
                        'rssi': int(values[1]),
                        'snr': int(values[2]),
                        'roll': float(values[3]),
                        'pitch': float(values[4]),
                        'yaw': float(values[5]),
                        'pressure': float(values[6]),
                        'temperature': float(values[7]),
                        'altitude': float(values[8]),
                        'sd_status': bool(int(values[9]) & 0x01),
                        'led_status': bool(int(values[9]) & 0x02),
                        'source_status': bool(int(values[9]) & 0x04),
                        'actuator_status': bool(int(values[10])),
                        'gps_lat': float(values[11]),
                        'gps_lon': float(values[12]),
                        'gps_alt': float(values[13]),
                        'ground_speed': float(values[14]),
                        'gps_time': float(values[15]),
                        'gps_valid': bool(int(values[16]))
                    }
                    
                    # Update model with complete telemetry
                    self.telemetry_model.update_telemetry(telemetry)
                    
                    # Emit GPS update signal if valid
                    if telemetry['gps_valid'] and telemetry['gps_lat'] != 0 and telemetry['gps_lon'] != 0:
                        self.gps_updated.emit(
                            telemetry['gps_lat'],
                            telemetry['gps_lon'],
                            telemetry['gps_alt']
                        )
                    
                    # Emit success signal
                    self.packet_parsed.emit(True, "Telemetry data received")
                    return True
                    
                except Exception as e:
                    self.packet_parsed.emit(False, f"Telemetry parse error: {str(e)}")
                    return False
            
            # Invalid packet format
            else:
                self.packet_parsed.emit(False, f"Invalid packet format: {len(values)} values")
                return False
                
        except Exception as e:
            self.packet_parsed.emit(False, f"Packet processing error: {str(e)}")
            return False
    
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