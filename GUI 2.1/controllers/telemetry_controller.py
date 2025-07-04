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
            print(f"Processing packet: {packet[:100]}{'...' if len(packet) > 100 else ''}")
            
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
            
            # New extended telemetry packet format (should be 39+ fields)
            elif len(values) >= 20:  # Minimum required fields for extended format
                try:
                    print(f"Processing extended packet with {len(values)} fields")
                    
                    # Helper function to safely parse values
                    def safe_int(idx, default=0):
                        try:
                            return int(values[idx]) if idx < len(values) and values[idx].strip() else default
                        except (ValueError, IndexError):
                            return default
                    
                    def safe_float(idx, default=0.0):
                        try:
                            return float(values[idx]) if idx < len(values) and values[idx].strip() else default
                        except (ValueError, IndexError):
                            return default
                    
                    def safe_bool(idx, default=False):
                        try:
                            return bool(int(values[idx])) if idx < len(values) and values[idx].strip() else default
                        except (ValueError, IndexError):
                            return default
                    
                    # Parse extended telemetry data with safer indexing
                    telemetry = {
                        'ack': safe_int(0),
                        'rssi': safe_int(1),
                        'snr': safe_int(2),
                        'fc_boot_time_ms': safe_int(4),  # Field 3 is empty, field 4 has boot time
                        'gps_lat': safe_float(5),        # Field 5
                        'gps_lon': safe_float(6),        # Field 6
                        'gps_alt': safe_float(7),        # Field 7
                        'ground_speed': safe_float(8),   # Field 8
                        'gps_time': safe_float(9),       # Field 9
                        # Fields 10-12 are empty (FC IMU data)
                        'pressure': safe_float(13),      # absPressure2
                        'temperature': safe_float(14),   # temperature2
                        'diff_pressure2': safe_float(15), # diffPressure2
                        'sd_status': safe_bool(16),
                        'actuator_status': safe_bool(17),
                        'logging_active': safe_bool(18),
                        'write_rate': safe_int(19),
                        'space_left': safe_int(20),
                        # Field 21 is empty (pix_unix_time_usec)
                        'pix_boot_time_ms': safe_int(22), # Field 22
                        # Fields 23-28 are empty (vibration data)
                        'gps_bearing': safe_float(29),
                        'gps_bearing_magnetic': safe_float(30),
                        # Fields 31-34 are empty (other bearing data)
                        'photodiode_value1': safe_int(35),
                        'photodiode_value2': safe_int(36),
                        'fc_battery_voltage': safe_float(37),
                        'led_battery_voltage': safe_float(38),
                        # Derived fields for compatibility
                        'gps_valid': safe_float(5) != 0.0 and safe_float(6) != 0.0,
                        'altitude': safe_float(7),  # Use GPS altitude as primary altitude
                        # LED status derived from photodiode values (placeholder logic)
                        'led_status': safe_int(35) > 5 or safe_int(36) > 5,  # Adjusted threshold
                        'source_status': True  # Placeholder - adjust based on actual requirements
                    }
                    
                    print(f"Parsed key values: RSSI={telemetry['rssi']}, GPS=({telemetry['gps_lat']:.6f},{telemetry['gps_lon']:.6f}), Alt={telemetry['altitude']:.2f}")
                    
                    # Update model with extended telemetry
                    self.telemetry_model.update_telemetry(telemetry)
                    
                    # Emit GPS update signal if valid
                    if telemetry['gps_valid'] and telemetry['gps_lat'] != 0 and telemetry['gps_lon'] != 0:
                        self.gps_updated.emit(
                            telemetry['gps_lat'],
                            telemetry['gps_lon'],
                            telemetry['gps_alt']
                        )
                    
                    # Emit success signal
                    self.packet_parsed.emit(True, f"Extended telemetry data received ({len(values)} fields)")
                    return True
                    
                except Exception as e:
                    print(f"Extended telemetry parse error: {str(e)}")
                    self.packet_parsed.emit(False, f"Extended telemetry parse error: {str(e)}")
                    return False
            
            # Legacy full telemetry packet (17 fields) - for backward compatibility
            elif len(values) == 17:
                try:
                    # Parse legacy complete telemetry data
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
            # Handle "No valid data" case
            if "No valid data" in data:
                self.packet_parsed.emit(True, "GPS: No valid data")
                return True
            
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
        """Process flight computer packet according to the new format"""
        try:
            values = data.split(',')
            print(f"FC packet has {len(values)} fields")
            
            if len(values) < 30:  # Reduced minimum requirement for robustness
                print(f"Warning: FC packet has only {len(values)} fields, expected at least 30")
                # Still try to process it with available fields
            
            # Helper function to safely parse values
            def safe_int(val, default=0):
                try:
                    return int(val) if val and val.strip() else default
                except (ValueError, TypeError):
                    return default
            
            def safe_float(val, default=0.0):
                try:
                    return float(val) if val and val.strip() else default
                except (ValueError, TypeError):
                    return default
            
            def safe_bool(val, default=False):
                try:
                    return bool(int(val)) if val and val.strip() else default
                except (ValueError, TypeError):
                    return default
            
            # Parse according to the exact packet structure from your C code
            fc_data = {
                # Basic fields (0-2)
                'ack': safe_int(values[0]) if len(values) > 0 else 0,
                'rssi': safe_int(values[1]) if len(values) > 1 else 0,
                'snr': safe_int(values[2]) if len(values) > 2 else 0,
                
                # FC time (3-4) - note field 3 is empty in your format
                'fc_unix_time_usec': safe_int(values[3]) if len(values) > 3 else 0,  # Empty in format
                'fc_boot_time_ms': safe_int(values[4]) if len(values) > 4 else 0,
                
                # Pixhawk GPS (5-9)
                'gps_lat': safe_float(values[5]) if len(values) > 5 else 0.0,
                'gps_lon': safe_float(values[6]) if len(values) > 6 else 0.0,
                'gps_alt': safe_float(values[7]) if len(values) > 7 else 0.0,
                'ground_speed': safe_float(values[8]) if len(values) > 8 else 0.0,
                'gps_time': safe_float(values[9]) if len(values) > 9 else 0.0,
                
                # FC IMU (10-12) - empty in your format
                'abs_pressure1': safe_float(values[10]) if len(values) > 10 else 0.0,
                'temperature1': safe_float(values[11]) if len(values) > 11 else 0.0,
                'altitude1': safe_float(values[12]) if len(values) > 12 else 0.0,
                
                # Pixhawk IMU (13-15)
                'abs_pressure2': safe_float(values[13]) if len(values) > 13 else 0.0,
                'temperature2': safe_float(values[14]) if len(values) > 14 else 0.0,
                'diff_pressure2': safe_float(values[15]) if len(values) > 15 else 0.0,
                
                # FC Status (16-17)
                'sd_status': safe_bool(values[16]) if len(values) > 16 else False,
                'actuator_status': safe_bool(values[17]) if len(values) > 17 else False,
                
                # Pixhawk Status (18-20)
                'logging_active': safe_bool(values[18]) if len(values) > 18 else False,
                'write_rate': safe_int(values[19]) if len(values) > 19 else 0,
                'space_left': safe_int(values[20]) if len(values) > 20 else 0,
                
                # Pixhawk Time (21-22) - note field 21 is empty
                'pix_unix_time_usec': safe_int(values[21]) if len(values) > 21 else 0,  # Empty in format
                'pix_boot_time_ms': safe_int(values[22]) if len(values) > 22 else 0,
                
                # Navigation (29-30) - skipping vibration fields 23-28
                'gps_bearing': safe_float(values[29]) if len(values) > 29 else 0.0,
                'gps_bearing_magnetic': safe_float(values[30]) if len(values) > 30 else 0.0,
                
                # Photodiodes (35-36) - skipping unused fields 31-34
                'photodiode_value1': safe_int(values[35]) if len(values) > 35 else 0,
                'photodiode_value2': safe_int(values[36]) if len(values) > 36 else 0,
                
                # Battery voltages (37-38)
                'fc_battery_voltage': safe_float(values[37]) if len(values) > 37 else 0.0,
                'led_battery_voltage': safe_float(values[38]) if len(values) > 38 else 0.0,
                
                # Derived fields for compatibility
                'gps_valid': safe_float(values[5]) != 0.0 and safe_float(values[6]) != 0.0 if len(values) > 6 else False,
                'altitude': safe_float(values[7]) if len(values) > 7 else 0.0,  # Use GPS altitude
                'pressure': safe_float(values[13]) if len(values) > 13 else 0.0,  # Use Pixhawk pressure
                'temperature': safe_float(values[14]) if len(values) > 14 else 0.0,  # Use Pixhawk temperature
            }
            
            print(f"FC parsed: RSSI={fc_data['rssi']}, GPS=({fc_data['gps_lat']:.6f},{fc_data['gps_lon']:.6f}), Alt={fc_data['altitude']:.2f}")
            
            # Update telemetry model - use the generic update method
            self.telemetry_model.update_telemetry(fc_data)
            
            # Emit GPS update signal if valid
            if fc_data['gps_valid']:
                self.gps_updated.emit(
                    fc_data['gps_lat'],
                    fc_data['gps_lon'],
                    fc_data['gps_alt']
                )
            
            self.packet_parsed.emit(True, f"Flight computer telemetry received ({len(values)} fields)")
            return True
            
        except Exception as e:
            print(f"FC packet parse error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.packet_parsed.emit(False, f"FC packet parse error: {str(e)}")
            return False