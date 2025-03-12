import math
import requests
from PyQt5.QtCore import QObject, pyqtSignal

class MapController(QObject):
    """Controller for handling map interactions"""
    
    # Define signals
    user_location_changed = pyqtSignal(float, float)  # lat, lon
    bearing_calculated = pyqtSignal(float, str)  # bearing, type (vehicle or target)
    
    def __init__(self, telemetry_model):
        super().__init__()
        self.telemetry_model = telemetry_model
        
        # Default user location (Montreal)
        self.user_lat = 45.5017
        self.user_lon = -73.5673
        
        # Connect to model signals
        self.telemetry_model.position_updated.connect(self.calculate_bearings)
    
    def detect_user_location(self):
        """Detect user's location using IP geolocation"""
        try:
            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.user_lat = float(data['latitude'])
                self.user_lon = float(data['longitude'])
                self.user_location_changed.emit(self.user_lat, self.user_lon)
                return True
            return False
        except Exception:
            return False
    
    def set_user_location(self, lat, lon):
        """Manually set user's location"""
        self.user_lat = lat
        self.user_lon = lon
        self.user_location_changed.emit(lat, lon)
        # Calculate bearings with new user location
        self.calculate_bearings(
            self.telemetry_model.gps_lat,
            self.telemetry_model.gps_lon,
            self.telemetry_model.gps_alt
        )
    
    def calculate_bearings(self, vehicle_lat, vehicle_lon, vehicle_alt):
        """Calculate bearings between points"""
        # Skip if we don't have valid coordinates
        if not vehicle_lat or not vehicle_lon or vehicle_lat == 0 or vehicle_lon == 0:
            return
        
        # Calculate vehicle heading (if we have previous coordinates)
        if hasattr(self, 'last_vehicle_lat') and hasattr(self, 'last_vehicle_lon'):
            if self.last_vehicle_lat != vehicle_lat or self.last_vehicle_lon != vehicle_lon:
                bearing = self.calculate_bearing(
                    self.last_vehicle_lat, self.last_vehicle_lon,
                    vehicle_lat, vehicle_lon
                )
                self.bearing_calculated.emit(bearing, "vehicle")
                
        # Calculate bearing from ground station to vehicle
        if self.user_lat and self.user_lon:
            target_bearing = self.calculate_bearing(
                self.user_lat, self.user_lon,
                vehicle_lat, vehicle_lon
            )
            self.bearing_calculated.emit(target_bearing, "target")
        
        # Store current position for next calculation
        self.last_vehicle_lat = vehicle_lat
        self.last_vehicle_lon = vehicle_lon
    
    @staticmethod
    def calculate_bearing(lat1, lon1, lat2, lon2):
        """Calculate great circle bearing between two points"""
        try:
            # Convert to radians
            lat1 = math.radians(float(lat1))
            lon1 = math.radians(float(lon1))
            lat2 = math.radians(float(lat2))
            lon2 = math.radians(float(lon2))
            
            # Calculate bearing
            d_lon = lon2 - lon1
            x = math.sin(d_lon) * math.cos(lat2)
            y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
            
            initial_bearing = math.atan2(x, y)
            bearing = (math.degrees(initial_bearing) + 360) % 360
            
            return bearing
            
        except Exception:
            return 0.0