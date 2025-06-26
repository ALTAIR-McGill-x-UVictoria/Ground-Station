import math
import requests # For IP geolocation
from PyQt5.QtCore import QObject, pyqtSignal

class MapController(QObject):
    """Controller for handling map interactions, including logic from gui.py"""
    
    user_location_changed = pyqtSignal(float, float)  # lat, lon
    # bearing_calculated signal: (bearing_value, type_of_bearing)
    # type_of_bearing can be "vehicle_heading" or "target_bearing"
    bearing_calculated = pyqtSignal(float, str) 
    
    def __init__(self, telemetry_model, settings_model): # Added settings_model
        super().__init__()
        self.telemetry_model = telemetry_model
        self.settings_model = settings_model # For API keys or default locations
        
        # Default user location (e.g., Montreal from gui.py, or from settings)
        self.user_lat = self.settings_model.get('map.default_user_lat', 45.5017)
        self.user_lon = self.settings_model.get('map.default_user_lon', -73.5673)
        
        self.last_vehicle_lat = None
        self.last_vehicle_lon = None
        
        # Connect to model signals
        self.telemetry_model.position_updated.connect(self.handle_vehicle_position_update)
        self.telemetry_model.ground_station_gps_updated.connect(self.handle_ground_station_gps_update)
    
    def detect_user_location(self):
        """Detect user's location using IP geolocation (from gui.py)."""
        try:
            # Try multiple geolocation services
            services = [
                'http://ip-api.com/json/',
                'https://ipinfo.io/json',
                'https://ipapi.co/json/'
            ]
            
            timeout_seconds = self.settings_model.get('map.geolocation_timeout', 5)
            
            for service_url in services:
                try:
                    response = requests.get(service_url, timeout=timeout_seconds)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Parse response based on service
                    if 'ip-api.com' in service_url:
                        lat = float(data.get('lat', self.user_lat))
                        lon = float(data.get('lon', self.user_lon))
                    elif 'ipinfo.io' in service_url:
                        loc = data.get('loc', '').split(',')
                        if len(loc) == 2:
                            lat = float(loc[0])
                            lon = float(loc[1])
                        else:
                            continue
                    else:  # ipapi.co
                        lat = float(data.get('latitude', self.user_lat))
                        lon = float(data.get('longitude', self.user_lon))
                    
                    if lat != self.user_lat or lon != self.user_lon:
                        self.user_lat = lat
                        self.user_lon = lon
                        self.user_location_changed.emit(self.user_lat, self.user_lon)
                        print(f"MapController: User location detected via {service_url}: {self.user_lat}, {self.user_lon}")
                    return True
                    
                except requests.exceptions.RequestException as e:
                    print(f"MapController: {service_url} failed: {e}")
                    continue
                except (ValueError, KeyError) as e:
                    print(f"MapController: Error parsing response from {service_url}: {e}")
                    continue
            
            # If all services failed, emit current location anyway
            print("MapController: All geolocation services failed. Using default location.")
            self.user_location_changed.emit(self.user_lat, self.user_lon)
            return False
            
        except Exception as e:
            print(f"MapController: Unexpected error in detect_user_location: {e}")
            self.user_location_changed.emit(self.user_lat, self.user_lon)
            return False

    def set_user_location(self, lat, lon):
        """Manually set user's location."""
        if self.user_lat != lat or self.user_lon != lon:
            self.user_lat = lat
            self.user_lon = lon
            self.user_location_changed.emit(lat, lon)
            print(f"MapController: User location set manually: {lat}, {lon}")
            # Recalculate bearings if vehicle position is known
            if self.last_vehicle_lat is not None and self.last_vehicle_lon is not None:
                self.calculate_target_bearing_to_vehicle(self.last_vehicle_lat, self.last_vehicle_lon)

    def handle_vehicle_position_update(self, vehicle_lat, vehicle_lon, vehicle_alt):
        """Called when vehicle position updates from telemetry_model."""
        if vehicle_lat == 0 and vehicle_lon == 0: # Invalid GPS data
            return

        # Calculate vehicle heading if previous position exists
        if self.last_vehicle_lat is not None and self.last_vehicle_lon is not None:
            # Ensure there's a significant enough change to calculate bearing
            # This avoids erratic bearings from tiny GPS fluctuations when stationary
            min_dist_sq = 0.00001 * 0.00001 # Approx 1 meter change squared
            if (vehicle_lat - self.last_vehicle_lat)**2 + (vehicle_lon - self.last_vehicle_lon)**2 > min_dist_sq:
                heading = self._calculate_bearing_static(
                    self.last_vehicle_lat, self.last_vehicle_lon,
                    vehicle_lat, vehicle_lon
                )
                self.bearing_calculated.emit(heading, "vehicle_heading")
        
        # Calculate bearing from ground station (user) to vehicle
        self.calculate_target_bearing_to_vehicle(vehicle_lat, vehicle_lon)
        
        # Store current position for next calculation
        self.last_vehicle_lat = vehicle_lat
        self.last_vehicle_lon = vehicle_lon

    def handle_ground_station_gps_update(self, gs_lat, gs_lon, gs_alt):
        """Called when ground station GPS data is received from GS packets."""
        print(f"MapController: Ground station GPS received: {gs_lat:.6f}, {gs_lon:.6f}, alt={gs_alt:.1f}m")
        
        # Update the user location with the ground station's actual GPS position
        if gs_lat != 0 and gs_lon != 0:  # Valid GPS coordinates
            if self.user_lat != gs_lat or self.user_lon != gs_lon:
                self.user_lat = gs_lat
                self.user_lon = gs_lon
                
                # Use QTimer to delay the emission slightly to ensure map is ready
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, lambda: self.user_location_changed.emit(gs_lat, gs_lon))
                print(f"MapController: Ground station location updated from GPS data: {gs_lat:.6f}, {gs_lon:.6f}")
                
                # Recalculate bearings if vehicle position is known
                if self.last_vehicle_lat is not None and self.last_vehicle_lon is not None:
                    self.calculate_target_bearing_to_vehicle(self.last_vehicle_lat, self.last_vehicle_lon)

    def calculate_target_bearing_to_vehicle(self, vehicle_lat, vehicle_lon):
        """Calculates bearing from user to vehicle."""
        if self.user_lat is not None and self.user_lon is not None:
            target_bearing = self._calculate_bearing_static(
                self.user_lat, self.user_lon,
                vehicle_lat, vehicle_lon
            )
            self.bearing_calculated.emit(target_bearing, "target_bearing")

    @staticmethod
    def _calculate_bearing_static(lat1, lon1, lat2, lon2):
        """
        Calculate great circle bearing between two points (static method from gui.py).
        Returns bearing in degrees (0-360).
        """
        try:
            lat1_rad = math.radians(float(lat1))
            lon1_rad = math.radians(float(lon1))
            lat2_rad = math.radians(float(lat2))
            lon2_rad = math.radians(float(lon2))
            
            delta_lon = lon2_rad - lon1_rad
            
            x = math.sin(delta_lon) * math.cos(lat2_rad)
            y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
                math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
            
            initial_bearing_rad = math.atan2(x, y)
            bearing_deg = (math.degrees(initial_bearing_rad) + 360) % 360 # Normalize to 0-360
            
            return bearing_deg
            
        except (ValueError, TypeError) as e:
            print(f"MapController: Error calculating bearing: {e}")
            return 0.0