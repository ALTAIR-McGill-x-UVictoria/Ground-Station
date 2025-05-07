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

        # Add these if they don't exist
        self.photodiode1 = 0
        self.photodiode2 = 0
        
        # Initialize arrays that might be missing
        if not hasattr(self, 'vertical_speed_data'):
            self.vertical_speed_data = []
    
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
            # Use consistent attribute naming - use gps_lat not latitude
            'gps_lat': self.gps_lat,
            'gps_lon': self.gps_lon,
            'gps_altitude': self.gps_alt,
            'gps_speed': self.gps_speed,
            'gps_time': self.gps_time,
            'gps_valid': self.gps_valid,
            # Use consistent attribute naming - use sd_status not sd_card_status
            'sd_status': self.sd_status,
            'actuator_status': self.actuator_status,
            'photodiode1': self.photodiode1 if hasattr(self, 'photodiode1') else 0,
            'photodiode2': self.photodiode2 if hasattr(self, 'photodiode2') else 0
        }