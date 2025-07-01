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
            packet = packet.strip()
            
            # Check for ground station controller packet formats
            if packet.startswith('GPS:'):
                return self._process_gps_packet(packet[4:])  # Remove 'GPS:' prefix
            elif packet.startswith('GS:'):
                return self._process_ground_station_packet(packet[3:])  # Remove 'GS:' prefix
            elif packet.startswith('FC:'):
                return self._process_flight_computer_packet(packet[3:])  # Remove 'FC:' prefix
            
            # Legacy packet processing (for backward compatibility)
            # Split packet into values
            values = packet.split(',')
            
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
    
    def _process_gps_packet(self, data):
        """Process GPS packet: lat,lon,alt,hdop,vdop,utc_unix,satellites,speed_kmh,course"""
        try:
            values = data.split(',')
            if len(values) != 9:
                self.packet_parsed.emit(False, f"Invalid GPS packet format: expected 9 values, got {len(values)}")
                return False
            
            gps_data = {
                'lat': float(values[0]),
                'lon': float(values[1]),
                'alt': float(values[2]),
                'hdop': float(values[3]),
                'vdop': float(values[4]),
                'utc_unix': int(values[5]),
                'satellites': int(values[6]),
                'speed_kmh': float(values[7]),
                'course': float(values[8])
            }
            
            # Update telemetry model with ground station GPS data
            self.telemetry_model.update_ground_station_gps(gps_data)
            
            self.packet_parsed.emit(True, "Ground station GPS data received")
            return True
            
        except (ValueError, IndexError) as e:
            self.packet_parsed.emit(False, f"GPS packet parse error: {str(e)}")
            return False
    
    def _process_ground_station_packet(self, data):
        """Process ground station packet: RSSI,SNR,time_since_last_packet"""
        try:
            values = data.split(',')
            if len(values) != 3:
                self.packet_parsed.emit(False, f"Invalid GS packet format: expected 3 values, got {len(values)}")
                return False
            
            gs_data = {
                'rssi': int(values[0]),
                'snr': int(values[1]),
                'time_since_last_packet': int(values[2])
            }
            
            # Update telemetry model with ground station telemetry
            self.telemetry_model.update_ground_station_telemetry(gs_data)
            
            self.packet_parsed.emit(True, "Ground station telemetry received")
            return True
            
        except (ValueError, IndexError) as e:
            self.packet_parsed.emit(False, f"GS packet parse error: {str(e)}")
            return False
    
    def _process_flight_computer_packet(self, data):
        """Process flight computer packet with flexible field count based on actual data"""
        try:
            values = data.split(',')
            if len(values) < 34:  # Minimum based on your example
                self.packet_parsed.emit(False, f"Invalid FC packet format: expected at least 34 values, got {len(values)}")
                return False
            
            # Parse according to the new FC packet structure (flexible field count)
            fc_data = {
                # Basic communication data (3 fields: 0-2)
                'ack': int(values[0]) if values[0].strip() else 0,
                'rssi': int(values[1]) if values[1].strip() else 0,
                'snr': int(values[2]) if values[2].strip() else 0,
                
                # FC time data (2 fields: 3-4)
                'fc_unix_time_usec': int(values[3]) if values[3].strip() else 0,
                'fc_boot_time_ms': int(values[4]) if values[4].strip() else 0,
                
                # Pixhawk GPS data (5 fields: 5-9)
                'gps_lat': float(values[5]) if values[5].strip() else 0.0,
                'gps_lon': float(values[6]) if values[6].strip() else 0.0,
                'gps_alt': float(values[7]) if values[7].strip() else 0.0,
                'ground_speed': float(values[8]) if values[8].strip() else 0.0,
                'gps_time': float(values[9]) if values[9].strip() else 0.0,
                
                # FC IMU data (3 fields: 10-12)
                'abs_pressure1': float(values[10]) if values[10].strip() else 0.0,
                'temperature1': float(values[11]) if values[11].strip() else 0.0,
                'altitude1': float(values[12]) if values[12].strip() else 0.0,
                
                # Pixhawk IMU data (3 fields: 13-15)
                'abs_pressure2': float(values[13]) if values[13].strip() else 0.0,
                'temperature2': float(values[14]) if values[14].strip() else 0.0,
                'diff_pressure2': float(values[15]) if values[15].strip() else 0.0,
                
                # FC Status (2 fields: 16-17)
                'sd_status': bool(int(values[16])) if values[16].strip() else False,
                'actuator_status': bool(int(values[17])) if values[17].strip() else False,
                
                # Pixhawk Status (3 fields: 18-20)
                'logging_active': bool(int(values[18])) if values[18].strip() else False,
                'write_rate': int(values[19]) if values[19].strip() else 0,
                'space_left': int(values[20]) if values[20].strip() else 0,
                
                # Pixhawk Time (2 fields: 21-22)
                'pix_unix_time_usec': int(values[21]) if values[21].strip() else 0,
                'pix_boot_time_ms': int(values[22]) if values[22].strip() else 0,
                
                # Vibration data (6 fields: 23-28)
                'vibe_x': float(values[23]) if values[23].strip() else 0.0,
                'vibe_y': float(values[24]) if values[24].strip() else 0.0,
                'vibe_z': float(values[25]) if values[25].strip() else 0.0,
                'clip_x': int(values[26]) if values[26].strip() else 0,
                'clip_y': int(values[27]) if values[27].strip() else 0,
                'clip_z': int(values[28]) if values[28].strip() else 0,
                
                # Navigation/GPS bearing data (6 fields: 29-34)
                'gps_bearing': float(values[29]) if values[29].strip() else 0.0,
                'gps_bearing_magnetic': float(values[30]) if values[30].strip() else 0.0,
                'gps_bearing_true': float(values[31]) if values[31].strip() else 0.0,
                'gps_bearing_ground_speed': float(values[32]) if values[32].strip() else 0.0,
                'gps_bearing_ground_speed_magnetic': float(values[33]) if values[33].strip() else 0.0,
                'gps_bearing_ground_speed_true': float(values[34]) if len(values) > 34 and values[34].strip() else 0.0,
                
                # Photodiode data (2 fields: 35-36) - if available
                'photodiode1': int(values[35]) if len(values) > 35 and values[35].strip() else 0,
                'photodiode2': int(values[36]) if len(values) > 36 and values[36].strip() else 0,
                
                # Battery voltages - if available in future packets
                'fc_battery_voltage': float(values[37]) if len(values) > 37 and values[37].strip() else 0.0,
                'led_battery_voltage': float(values[38]) if len(values) > 38 and values[38].strip() else 0.0,
            }
            
            # Update telemetry model with flight computer data
            self.telemetry_model.update_flight_computer_telemetry(fc_data)
            
            # Emit GPS update signal if valid
            if fc_data['gps_lat'] != 0 and fc_data['gps_lon'] != 0:
                self.gps_updated.emit(
                    fc_data['gps_lat'],
                    fc_data['gps_lon'],
                    fc_data['gps_alt']
                )
            
            self.packet_parsed.emit(True, f"Flight computer telemetry received ({len(values)} fields)")
            return True
            
        except (ValueError, IndexError) as e:
            self.packet_parsed.emit(False, f"FC packet parse error: {str(e)}")
            return False