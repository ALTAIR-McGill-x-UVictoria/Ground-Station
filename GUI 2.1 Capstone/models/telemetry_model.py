from PyQt5.QtCore import QObject, pyqtSignal
import time
import struct
import logging

class TelemetryModel(QObject):
    """
    Model for storing and managing telemetry data.
    Emits signals when data is updated.
    """
    # Define signals
    data_updated = pyqtSignal()
    altitude_updated = pyqtSignal(float)
    position_updated = pyqtSignal(float, float, float)  # lat, lon, alt
    signal_updated = pyqtSignal(int, int)  # rssi, snr
    
    def __init__(self):
        super().__init__()
        
        # Initialize time reference
        self.start_time = time.time()
        
        # Initialize data arrays for plotting
        self.altitude_data = []
        self.temperature_data = []
        self.pressure_data = []
        self.ground_speed_data = []
        self.vertical_speed_data = []
        
        # Signal strength data
        self.rssi_data = []
        self.snr_data = []
        
        # Time data for x-axis
        self.telemetry_time_data = []
        self.signal_time_data = []
        
        # Current values
        self.altitude = 0
        self.temperature = 0
        self.pressure = 0
        self.vertical_speed = 0
        self.ground_speed = 0
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.rssi = 0
        self.snr = 0
        
        # GPS data
        self.gps_lat = 0
        self.gps_lon = 0
        self.gps_alt = 0
        self.gps_time = 0
        self.gps_valid = False
        
        # System status
        self.sd_status = False
        self.led_status = False
        self.actuator_status = False
        self.source_status = False
        self.ack_status = False
        
        # Last altitude data for vertical speed calculation
        self.last_altitude = 0
        self.last_altitude_time = 0
        
        # Maximum number of data points to keep
        self.max_data_points = 1000

        self.logger = logging.getLogger(__name__)
        self.telemetry_data = {
            # Control to Power board data
            "timestamp": 0,
            "pressure": 0,
            "altitude": 0,
            "temperature": 0,
            "linear_accel_x": 0.0,
            "linear_accel_y": 0.0,
            "linear_accel_z": 0.0,
            "angular_vel_x": 0.0,
            "angular_vel_y": 0.0,
            "angular_vel_z": 0.0,
            "orientation_yaw": 0.0,
            "orientation_pitch": 0.0,
            "orientation_roll": 0.0,
            "status_msg": "",
            
            # Power to Control board data
            "transponder_timestamp": 0,
            "battery_voltage": 0.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "abort_command": False,
            "status_heartbeat": "",
            
            # Additional computed fields
            "packet_count": 0,
            "rssi": -80,  # Default value
            "vertical_speed": 0.0,
            "horizontal_speed": 0.0,
            "heading": 0.0,
            "external_temp": 0.0,
            "internal_temp": 0.0,
            "max_altitude": 0.0,
            "predicted_landing": {"latitude": 0.0, "longitude": 0.0},
            "time_to_landing": 0
        }
        self.callbacks = []
        self.last_altitude = 0
        self.last_altitude_time = time.time()
        self.packet_count = 0
    
    def register_callback(self, callback):
        """Register a callback function that will be called when data is updated"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
    
    def update_signal(self, rssi, snr):
        """Update signal strength data"""
        current_time = time.time() - self.start_time
        
        # Update current values
        self.rssi = rssi
        self.snr = snr
        
        # Add to arrays
        self.signal_time_data.append(current_time)
        self.rssi_data.append(rssi)
        self.snr_data.append(snr)
        
        # Limit array size
        if len(self.signal_time_data) > self.max_data_points:
            self.signal_time_data = self.signal_time_data[-self.max_data_points:]
            self.rssi_data = self.rssi_data[-self.max_data_points:]
            self.snr_data = self.snr_data[-self.max_data_points:]
        
        # Emit signal
        self.signal_updated.emit(rssi, snr)
    
    def update_telemetry(self, telemetry_data):
        """Update telemetry data with a dictionary of values"""
        current_time = time.time() - self.start_time
        
        # Update current values
        for key, value in telemetry_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Calculate vertical speed if altitude changed
        if 'altitude' in telemetry_data:
            self.calculate_vertical_speed(telemetry_data['altitude'])
        
        # Add to arrays
        self.telemetry_time_data.append(current_time)
        self.altitude_data.append(self.altitude)
        self.temperature_data.append(self.temperature)
        self.pressure_data.append(self.pressure)
        self.ground_speed_data.append(self.ground_speed)
        if hasattr(self, 'vertical_speed'):
            self.vertical_speed_data.append(self.vertical_speed)
        
        # Limit array size
        if len(self.telemetry_time_data) > self.max_data_points:
            self.telemetry_time_data = self.telemetry_time_data[-self.max_data_points:]
            self.altitude_data = self.altitude_data[-self.max_data_points:]
            self.temperature_data = self.temperature_data[-self.max_data_points:]
            self.pressure_data = self.pressure_data[-self.max_data_points:]
            self.ground_speed_data = self.ground_speed_data[-self.max_data_points:]
            if len(self.vertical_speed_data) > self.max_data_points:
                self.vertical_speed_data = self.vertical_speed_data[-self.max_data_points:]
        
        # Emit signals
        self.data_updated.emit()
        self.altitude_updated.emit(self.altitude)
        
        if 'gps_lat' in telemetry_data and 'gps_lon' in telemetry_data:
            self.position_updated.emit(self.gps_lat, self.gps_lon, self.gps_alt)
    
    def calculate_vertical_speed(self, current_altitude):
        """Calculate vertical speed based on altitude changes"""
        now = time.time()
        
        if self.last_altitude_time == 0:
            # First measurement
            self.last_altitude = current_altitude
            self.last_altitude_time = now
            self.vertical_speed = 0
            return
        
        # Calculate time difference and altitude change
        time_diff = now - self.last_altitude_time
        if time_diff < 0.1:  # Avoid division by very small numbers
            return
            
        altitude_diff = current_altitude - self.last_altitude
        self.vertical_speed = altitude_diff / time_diff
        
        # Update last values for next calculation
        self.last_altitude = current_altitude
        self.last_altitude_time = now

    def parse_control_to_power_packet(self, data):
        """Parse packet from Control to Power board"""
        try:
            # Check minimum packet size
            if len(data) < 0x34:  # Minimum size without variable length
                return False
            
            # Parse fixed length fields
            timestamp = struct.unpack("<I", data[0x00:0x04])[0]
            pressure = struct.unpack("<I", data[0x04:0x08])[0]
            altitude = struct.unpack("<I", data[0x08:0x0C])[0]
            temperature = struct.unpack("<I", data[0x0C:0x10])[0]
            linear_accel_x = struct.unpack("<f", data[0x10:0x14])[0]
            linear_accel_y = struct.unpack("<f", data[0x14:0x18])[0]
            linear_accel_z = struct.unpack("<f", data[0x18:0x1C])[0]
            angular_vel_x = struct.unpack("<f", data[0x1C:0x20])[0]
            angular_vel_y = struct.unpack("<f", data[0x20:0x24])[0]
            angular_vel_z = struct.unpack("<f", data[0x24:0x28])[0]
            orientation_yaw = struct.unpack("<f", data[0x28:0x2C])[0]
            orientation_pitch = struct.unpack("<f", data[0x2C:0x30])[0]
            orientation_roll = struct.unpack("<f", data[0x30:0x34])[0]
            
            # Update telemetry data
            self.telemetry_data["timestamp"] = timestamp
            self.telemetry_data["pressure"] = pressure
            self.telemetry_data["altitude"] = altitude
            self.telemetry_data["temperature"] = temperature
            self.telemetry_data["linear_accel_x"] = linear_accel_x
            self.telemetry_data["linear_accel_y"] = linear_accel_y
            self.telemetry_data["linear_accel_z"] = linear_accel_z
            self.telemetry_data["angular_vel_x"] = angular_vel_x
            self.telemetry_data["angular_vel_y"] = angular_vel_y
            self.telemetry_data["angular_vel_z"] = angular_vel_z
            self.telemetry_data["orientation_yaw"] = orientation_yaw
            self.telemetry_data["orientation_pitch"] = orientation_pitch
            self.telemetry_data["orientation_roll"] = orientation_roll
            
            # Parse variable-length status message if present
            if len(data) >= 0x36:  # Has at least the message length field
                status_msg_length = struct.unpack("<H", data[0x34:0x36])[0]
                
                if len(data) >= 0x36 + status_msg_length:
                    try:
                        self.telemetry_data["status_msg"] = data[0x36:0x36+status_msg_length].decode('utf-8', errors='replace')
                    except Exception as e:
                        logging.error(f"Error decoding status message: {e}")
            
            # Notify subscribers
            self.data_updated.emit(self.telemetry_data)
            return True
            
        except Exception as e:
            logging.error(f"Error parsing Control to Power packet: {e}")
            return False

    def parse_power_to_control_packet(self, data):
        """Parse packet from Power to Control board"""
        try:
            # Check minimum packet size
            if len(data) < 0x11:  # Minimum size without variable length
                return False
            
            # Parse fixed length fields
            transponder_timestamp = struct.unpack("<I", data[0x00:0x04])[0]
            battery_voltage = struct.unpack("<f", data[0x04:0x08])[0]
            latitude = struct.unpack("<f", data[0x08:0x0C])[0]
            longitude = struct.unpack("<f", data[0x0C:0x10])[0]
            abort_command = bool(data[0x10])
            
            # Update telemetry data
            self.telemetry_data["transponder_timestamp"] = transponder_timestamp
            self.telemetry_data["battery_voltage"] = battery_voltage
            self.telemetry_data["latitude"] = latitude
            self.telemetry_data["longitude"] = longitude
            self.telemetry_data["abort_command"] = abort_command
            
            # Parse status message + heartbeat if present
            if len(data) > 0x11:
                try:
                    self.telemetry_data["status_heartbeat"] = data[0x11:].decode('utf-8', errors='replace')
                except Exception as e:
                    logging.error(f"Error decoding status heartbeat: {e}")
            
            # Notify subscribers
            self.data_updated.emit(self.telemetry_data)
            return True
            
        except Exception as e:
            logging.error(f"Error parsing Power to Control packet: {e}")
            return False

    def _notify_callbacks(self):
        """Notify all registered callbacks with the current telemetry data"""
        for callback in self.callbacks:
            callback(self.telemetry_data)
    
    def parse_packet(self, data, packet_type):
        """Parse a packet based on its type"""
        if packet_type == "control_to_power":
            return self.parse_control_to_power_packet(data)
        elif packet_type == "power_to_control":
            return self.parse_power_to_control_packet(data)
        else:
            self.logger.error(f"Unknown packet type: {packet_type}")
            return False
    
    def get_telemetry_data(self):
        """Return a dictionary of all telemetry data"""
        return self.telemetry_data.copy()
    
    def _calculate_vertical_speed(self):
        """Calculate vertical speed based on altitude changes"""
        current_time = time.time()
        current_altitude = self.telemetry_data["altitude"]
        
        # Calculate time delta and altitude delta
        time_delta = current_time - self.last_altitude_time
        if time_delta > 0.1:  # Only update if enough time has passed
            altitude_delta = current_altitude - self.last_altitude
            vertical_speed = altitude_delta / time_delta
            
            # Apply smoothing filter
            curr_vs = self.telemetry_data["vertical_speed"]
            self.telemetry_data["vertical_speed"] = curr_vs * 0.7 + vertical_speed * 0.3
            
            # Update last values
            self.last_altitude = current_altitude
            self.last_altitude_time = current_time
    
    def _update_max_altitude(self):
        """Update maximum achieved altitude"""
        current_altitude = self.telemetry_data["altitude"]
        if current_altitude > self.telemetry_data["max_altitude"]:
            self.telemetry_data["max_altitude"] = current_altitude
    
    def _calculate_horizontal_speed(self):
        """Calculate horizontal speed based on GPS changes"""
        # Placeholder - would use previous GPS coordinates and haversine formula
        self.telemetry_data["horizontal_speed"] = 0.0
        self.telemetry_data["heading"] = self.telemetry_data["orientation_yaw"]
    
    def _predict_landing(self):
        """Predict landing location based on current trajectory"""
        # Simple prediction - in a real application this would use wind data and physics models
        self.telemetry_data["predicted_landing"] = {
            "latitude": self.telemetry_data["latitude"],
            "longitude": self.telemetry_data["longitude"]
        }
        
        # Estimate time to landing
        altitude = self.telemetry_data["altitude"]
        vert_speed = self.telemetry_data["vertical_speed"]
        
        if vert_speed < -0.1:  # If falling
            self.telemetry_data["time_to_landing"] = abs(altitude / vert_speed)
        else:
            self.telemetry_data["time_to_landing"] = 0