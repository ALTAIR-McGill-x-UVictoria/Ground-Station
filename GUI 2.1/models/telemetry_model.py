from PyQt5.QtCore import QObject, pyqtSignal
import time

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
    ground_station_gps_updated = pyqtSignal(float, float, float)  # lat, lon, alt
    status_indicator_changed = pyqtSignal(str, object)  # indicator_name, new_value
    packet_received = pyqtSignal(dict)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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
        self.gps_speed = 0.0  # Add this line
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

        # Additional sensor data
        self.photodiode1 = 0
        self.photodiode2 = 0
        
        # Status fields
        self.led_status = False
        self.source_status = False
        self.ack_status = False
        
        # Time fields from new FC packet format
        self.fc_unix_time_usec = 0
        self.fc_boot_time_ms = 0
        self.pix_unix_time_usec = 0
        self.pix_boot_time_ms = 0
        
        # IMU data from FC and Pixhawk
        self.abs_pressure1 = 0.0  # FC IMU
        self.temperature1 = 0.0   # FC IMU (same as self.temperature)
        self.altitude1 = 0.0      # FC IMU (same as self.altitude)
        self.abs_pressure2 = 0.0  # Pixhawk IMU
        self.temperature2 = 0.0   # Pixhawk IMU
        self.diff_pressure2 = 0.0 # Pixhawk IMU
        
        # Pixhawk status
        self.logging_active = False
        self.write_rate = 0
        self.space_left = 0
        
        # Vibration data
        self.vibe_x = 0.0
        self.vibe_y = 0.0
        self.vibe_z = 0.0
        self.clip_x = 0
        self.clip_y = 0
        self.clip_z = 0
        
        # Navigation/GPS bearing data
        self.gps_bearing = 0.0
        self.gps_bearing_magnetic = 0.0
        self.gps_bearing_true = 0.0
        self.gps_bearing_ground_speed = 0.0
        self.gps_bearing_ground_speed_magnetic = 0.0
        self.gps_bearing_ground_speed_true = 0.0
        
        # Battery voltages
        self.fc_battery_voltage = 0.0
        self.led_battery_voltage = 0.0
        
        # Legacy fields for backward compatibility
        self.battery_voltage = 0.0
        self.current_draw = 0.0
        self.humidity = 0.0
        self.packet_count = 0
        self.flight_mode = 0
        self.error_flags = 0
        
        # Initialize arrays that might be missing
        if not hasattr(self, 'vertical_speed_data'):
            self.vertical_speed_data = []
        
        # Status indicators storage
        self._status_indicators = {}
    
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
        
        # Debug - show what we're updating
        print(f"Updating telemetry with: {', '.join([f'{k}={v}' for k, v in telemetry_data.items() if k in ['altitude', 'temperature', 'rssi', 'gps_speed']])}")
        
        # Update current values
        for key, value in telemetry_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
                # Call update_status_indicator for status fields
                if key in ['sd_status', 'actuator_status', 'led_status', 'source_status', 'ack_status']:
                    self.update_status_indicator(key, value)
            else:
                print(f"Warning: TelemetryModel has no attribute '{key}'")
        
        # If gps_speed is updated, also update ground_speed for plot consistency
        if 'gps_speed' in telemetry_data:
            self.ground_speed = telemetry_data['gps_speed']

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

    def update_from_sdr(self, packet):
        """Update telemetry data from SDR packet"""
        # Prepare telemetry dictionary for bulk update
        telemetry_data = {
            'roll': packet['fRoll'],
            'pitch': packet['fPitch'],
            'yaw': packet['fYaw'],
            'pressure': packet['Pressure'],
            'temperature': packet['Temperature'],
            'altitude': packet['Altitude'],
            'sd_status': packet['SDStatus'],  # Standardize name
            'actuator_status': packet['actuatorStatus'],
            'photodiode1': packet['photodiodeValue1'],
            'photodiode2': packet['photodiodeValue2'],
            'rssi': packet['RSSI'],
            'snr': packet['SNR']
        }
        
        # Add GPS data if valid
        if packet['gpsValid']:
            telemetry_data.update({
                'gps_lat': packet['gpsLat'],
                'gps_lon': packet['gpsLon'],
                'gps_alt': packet['gpsAlt'],
                'gps_speed': packet['gpsSpeed'],
                'gps_time': packet['gpsTime'],
                'gps_valid': True
            })
        
        # Use the existing update method to ensure consistent behavior
        self.update_telemetry(telemetry_data)
        
        # Debug output
        print(f"Updated telemetry from SDR: alt={self.altitude}m, temp={self.temperature}°C")
        self.packet_received.emit(packet)
    
    def get_latest_telemetry(self):
        """Return a dictionary with the current telemetry values"""
        return {
            'altitude': self.altitude,
            'temperature': self.temperature,
            'pressure': self.pressure,
            'vertical_speed': self.vertical_speed,
            'ground_speed': self.ground_speed,
            'roll': self.roll,
            'pitch': self.pitch,
            'yaw': self.yaw,
            'rssi': self.rssi,
            'snr': self.snr,
            # GPS data
            'gps_lat': self.gps_lat,
            'gps_lon': self.gps_lon,
            'gps_altitude': self.gps_alt,
            'gps_alt': self.gps_alt,  # Both naming conventions
            'gps_speed': self.gps_speed,
            'gps_time': self.gps_time,
            'gps_valid': self.gps_valid,
            # Status data
            'sd_status': self.sd_status,
            'actuator_status': self.actuator_status,
            'led_status': self.led_status,
            'source_status': self.source_status,
            'ack_status': self.ack_status,
            'ack': getattr(self, 'ack', 0),
            # Sensor data
            'photodiode1': self.photodiode1 if hasattr(self, 'photodiode1') else 0,
            'photodiode2': self.photodiode2 if hasattr(self, 'photodiode2') else 0,
            # Time fields from new FC packet format
            'fc_unix_time_usec': getattr(self, 'fc_unix_time_usec', 0),
            'fc_boot_time_ms': getattr(self, 'fc_boot_time_ms', 0),
            'pix_unix_time_usec': getattr(self, 'pix_unix_time_usec', 0),
            'pix_boot_time_ms': getattr(self, 'pix_boot_time_ms', 0),
            # IMU data
            'abs_pressure1': getattr(self, 'abs_pressure1', 0.0),
            'temperature1': getattr(self, 'temperature1', 0.0),
            'altitude1': getattr(self, 'altitude1', 0.0),
            'abs_pressure2': getattr(self, 'abs_pressure2', 0.0),
            'temperature2': getattr(self, 'temperature2', 0.0),
            'diff_pressure2': getattr(self, 'diff_pressure2', 0.0),
            # Pixhawk status
            'logging_active': getattr(self, 'logging_active', False),
            'write_rate': getattr(self, 'write_rate', 0),
            'space_left': getattr(self, 'space_left', 0),
            # Vibration data
            'vibe_x': getattr(self, 'vibe_x', 0.0),
            'vibe_y': getattr(self, 'vibe_y', 0.0),
            'vibe_z': getattr(self, 'vibe_z', 0.0),
            'clip_x': getattr(self, 'clip_x', 0),
            'clip_y': getattr(self, 'clip_y', 0),
            'clip_z': getattr(self, 'clip_z', 0),
            # Navigation/GPS bearing data
            'gps_bearing': getattr(self, 'gps_bearing', 0.0),
            'gps_bearing_magnetic': getattr(self, 'gps_bearing_magnetic', 0.0),
            'gps_bearing_true': getattr(self, 'gps_bearing_true', 0.0),
            'gps_bearing_ground_speed': getattr(self, 'gps_bearing_ground_speed', 0.0),
            'gps_bearing_ground_speed_magnetic': getattr(self, 'gps_bearing_ground_speed_magnetic', 0.0),
            'gps_bearing_ground_speed_true': getattr(self, 'gps_bearing_ground_speed_true', 0.0),
            # Battery voltages
            'fc_battery_voltage': getattr(self, 'fc_battery_voltage', 0.0),
            'led_battery_voltage': getattr(self, 'led_battery_voltage', 0.0),
            # Legacy fields for backward compatibility
            'battery_voltage': getattr(self, 'battery_voltage', 0.0),
            'current_draw': getattr(self, 'current_draw', 0.0),
            'humidity': getattr(self, 'humidity', 0.0),
            'packet_count': getattr(self, 'packet_count', 0),
            'flight_mode': getattr(self, 'flight_mode', 0),
            'error_flags': getattr(self, 'error_flags', 0),
            # Alternative naming for backward compatibility
            'fRoll': self.roll,
            'fPitch': self.pitch,
            'fYaw': self.yaw
        }
    
    def get_latest_data(self):
        """Alias for get_latest_telemetry for backward compatibility"""
        return self.get_latest_telemetry()
    
    def update_ground_station_gps(self, gps_data):
        """Update ground station GPS data"""
        # Store ground station GPS data separately
        self.gs_gps_lat = gps_data['lat']
        self.gs_gps_lon = gps_data['lon']
        self.gs_gps_alt = gps_data['alt']
        self.gs_gps_hdop = gps_data['hdop']
        self.gs_gps_vdop = gps_data['vdop']
        self.gs_gps_utc_unix = gps_data['utc_unix']
        self.gs_gps_satellites = gps_data['satellites']
        self.gs_gps_speed_kmh = gps_data['speed_kmh']
        self.gs_gps_course = gps_data['course']
        
        print(f"Ground station GPS updated: {gps_data['lat']:.6f}, {gps_data['lon']:.6f}, alt={gps_data['alt']:.1f}m")
        
        # Emit signal for ground station position update (separate from vehicle position)
        self.ground_station_gps_updated.emit(gps_data['lat'], gps_data['lon'], gps_data['alt'])
        self.data_updated.emit()
    
    def update_ground_station_telemetry(self, gs_data):
        """Update ground station telemetry data"""
        self.gs_rssi = gs_data['rssi']
        self.gs_snr = gs_data['snr']
        self.gs_time_since_last_packet = gs_data['time_since_last_packet']
        
        # print(f"Ground station telemetry updated: RSSI={gs_data['rssi']}, SNR={gs_data['snr']}, time_since_last={gs_data['time_since_last_packet']}")
        
        # Update signal strength data with ground station values
        self.update_signal(gs_data['rssi'], gs_data['snr'])
    def update_status_indicator(self, indicator_name, new_value):
        """Update a status indicator and emit a signal if it changes"""
        old_value = self._status_indicators.get(indicator_name)
        if old_value != new_value:
            self._status_indicators[indicator_name] = new_value
            self.status_indicator_changed.emit(indicator_name, new_value)

    def update_flight_computer_telemetry(self, fc_data):
        """Update flight computer telemetry data with new extended format"""
        current_time = time.time() - self.start_time
        
        # Update current values - handle both old and new format fields
        self.ack = fc_data.get('ack', 0)
        self.rssi = fc_data.get('rssi', 0)
        self.snr = fc_data.get('snr', 0)
        
        # Time fields
        self.fc_unix_time_usec = fc_data.get('fc_unix_time_usec', 0)
        self.fc_boot_time_ms = fc_data.get('fc_boot_time_ms', 0)
        self.pix_unix_time_usec = fc_data.get('pix_unix_time_usec', 0)
        self.pix_boot_time_ms = fc_data.get('pix_boot_time_ms', 0)
        
        # GPS data (Pixhawk GPS)
        self.gps_lat = fc_data.get('gps_lat', 0.0)
        self.gps_lon = fc_data.get('gps_lon', 0.0)
        self.gps_alt = fc_data.get('gps_alt', 0.0)
        self.ground_speed = fc_data.get('ground_speed', 0.0)
        self.gps_speed = self.ground_speed  # Keep both for compatibility
        self.gps_time = fc_data.get('gps_time', 0.0)
        self.gps_valid = self.gps_lat != 0.0 and self.gps_lon != 0.0
        
        # IMU data from FC
        self.abs_pressure1 = fc_data.get('abs_pressure1', 0.0)
        self.temperature1 = fc_data.get('temperature1', 0.0)
        self.altitude1 = fc_data.get('altitude1', 0.0)
        # Use FC values as primary sensor data
        self.pressure = self.abs_pressure1
        self.temperature = self.temperature1
        self.altitude = self.altitude1
        
        # IMU data from Pixhawk
        self.abs_pressure2 = fc_data.get('abs_pressure2', 0.0)
        self.temperature2 = fc_data.get('temperature2', 0.0)
        self.diff_pressure2 = fc_data.get('diff_pressure2', 0.0)
        
        # Status fields
        self.sd_status = fc_data.get('sd_status', False)
        self.actuator_status = fc_data.get('actuator_status', False)
        self.logging_active = fc_data.get('logging_active', False)
        self.write_rate = fc_data.get('write_rate', 0)
        self.space_left = fc_data.get('space_left', 0)
        # Update status indicators for relevant fields
        for status_key in ['sd_status', 'actuator_status', 'logging_active']:
            self.update_status_indicator(status_key, getattr(self, status_key))
        
        # Vibration data
        self.vibe_x = fc_data.get('vibe_x', 0.0)
        self.vibe_y = fc_data.get('vibe_y', 0.0)
        self.vibe_z = fc_data.get('vibe_z', 0.0)
        self.clip_x = fc_data.get('clip_x', 0)
        self.clip_y = fc_data.get('clip_y', 0)
        self.clip_z = fc_data.get('clip_z', 0)
        
        # Navigation/GPS bearing data
        self.gps_bearing = fc_data.get('gps_bearing', 0.0)
        self.gps_bearing_magnetic = fc_data.get('gps_bearing_magnetic', 0.0)
        self.gps_bearing_true = fc_data.get('gps_bearing_true', 0.0)
        self.gps_bearing_ground_speed = fc_data.get('gps_bearing_ground_speed', 0.0)
        self.gps_bearing_ground_speed_magnetic = fc_data.get('gps_bearing_ground_speed_magnetic', 0.0)
        self.gps_bearing_ground_speed_true = fc_data.get('gps_bearing_ground_speed_true', 0.0)
        
        # Photodiode data
        self.photodiode1 = fc_data.get('photodiode1', 0)
        self.photodiode2 = fc_data.get('photodiode2', 0)
        
        # Battery voltages
        self.fc_battery_voltage = fc_data.get('fc_battery_voltage', 0.0)
        self.led_battery_voltage = fc_data.get('led_battery_voltage', 0.0)
        # Set main battery voltage to FC battery for compatibility
        self.battery_voltage = self.fc_battery_voltage
        
        # Legacy field support for backward compatibility
        if 'roll' in fc_data:
            self.roll = fc_data['roll']
        if 'pitch' in fc_data:
            self.pitch = fc_data['pitch']
        if 'yaw' in fc_data:
            self.yaw = fc_data['yaw']
        
        # Calculate vertical speed
        self.calculate_vertical_speed(self.altitude)
        
        # Add to arrays
        self.telemetry_time_data.append(current_time)
        self.altitude_data.append(self.altitude)
        self.temperature_data.append(self.temperature)
        self.pressure_data.append(self.pressure)
        self.ground_speed_data.append(self.ground_speed)
        self.vertical_speed_data.append(self.vertical_speed)
        
        # Limit array size
        if len(self.telemetry_time_data) > self.max_data_points:
            self.telemetry_time_data = self.telemetry_time_data[-self.max_data_points:]
            self.altitude_data = self.altitude_data[-self.max_data_points:]
            self.temperature_data = self.temperature_data[-self.max_data_points:]
            self.pressure_data = self.pressure_data[-self.max_data_points:]
            self.ground_speed_data = self.ground_speed_data[-self.max_data_points:]
            self.vertical_speed_data = self.vertical_speed_data[-self.max_data_points:]
        
        # Emit signals
        self.data_updated.emit()
        self.altitude_updated.emit(self.altitude)
        self.signal_updated.emit(self.rssi, self.snr)
        
        if self.gps_valid and self.gps_lat != 0 and self.gps_lon != 0:
            self.position_updated.emit(self.gps_lat, self.gps_lon, self.gps_alt)
        
        print(f"Flight computer telemetry updated: alt={self.altitude}m, temp={self.temperature}°C, GPS valid={self.gps_valid}, battery={self.fc_battery_voltage}V")
        self.packet_received.emit(fc_data)