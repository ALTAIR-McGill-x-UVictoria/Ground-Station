"""
Tracking Calculator for balloon tracking operations
Handles all mathematical calculations for bearing, distance, elevation, and coordinate conversions
"""
import math
from datetime import datetime
import pytz


class TrackingCalculator:
    """Handles all tracking calculations and coordinate conversions"""
    
    def __init__(self):
        # Earth's radius in kilometers
        self.EARTH_RADIUS_KM = 6371.0
    
    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """
        Calculate bearing from point 1 to point 2 in degrees
        
        Args:
            lat1, lon1: Starting point latitude and longitude in degrees
            lat2, lon2: Ending point latitude and longitude in degrees
            
        Returns:
            Bearing in degrees (0-360, where 0 is North)
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        return (bearing_deg + 360) % 360
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two points using Haversine formula
        
        Args:
            lat1, lon1: First point latitude and longitude in degrees
            lat2, lon2: Second point latitude and longitude in degrees
            
        Returns:
            Distance in kilometers
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat_rad = math.radians(lat2 - lat1)
        dlon_rad = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat_rad/2) * math.sin(dlat_rad/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(dlon_rad/2) * math.sin(dlon_rad/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return self.EARTH_RADIUS_KM * c
    
    def calculate_elevation_angle(self, ground_alt, balloon_alt, distance_km):
        """
        Calculate elevation angle from ground station to balloon
        
        Args:
            ground_alt: Ground station altitude in meters
            balloon_alt: Balloon altitude in meters
            distance_km: Horizontal distance in kilometers
            
        Returns:
            Elevation angle in degrees
        """
        if distance_km <= 0:
            return 0.0
        
        # Convert distance to meters
        distance_m = distance_km * 1000
        height_diff = balloon_alt - ground_alt
        
        elevation_rad = math.atan2(height_diff, distance_m)
        return math.degrees(elevation_rad)
    
    def calculate_tracking_parameters(self, ground_lat, ground_lon, ground_alt, 
                                    balloon_lat, balloon_lon, balloon_alt):
        """
        Calculate all tracking parameters: bearing, distance, elevation
        
        Args:
            ground_lat, ground_lon, ground_alt: Ground station position
            balloon_lat, balloon_lon, balloon_alt: Balloon position
            
        Returns:
            Dictionary with bearing, distance, elevation, and other parameters
        """
        # Check for valid coordinates
        if (ground_lat == 0 and ground_lon == 0) or (balloon_lat == 0 and balloon_lon == 0):
            return {
                'bearing': 0.0,
                'distance': 0.0,
                'elevation': 0.0,
                'valid': False
            }
        
        # Calculate bearing
        bearing = self.calculate_bearing(ground_lat, ground_lon, balloon_lat, balloon_lon)
        
        # Calculate distance
        distance = self.calculate_distance(ground_lat, ground_lon, balloon_lat, balloon_lon)
        
        # Calculate elevation angle
        elevation = self.calculate_elevation_angle(ground_alt, balloon_alt, distance)
        
        return {
            'bearing': bearing,
            'distance': distance,
            'elevation': elevation,
            'valid': True,
            'ground_position': (ground_lat, ground_lon, ground_alt),
            'balloon_position': (balloon_lat, balloon_lon, balloon_alt)
        }
    
    def calculate_mount_coordinates(self, bearing, elevation):
        """
        Calculate target azimuth and altitude for mount tracking
        
        Args:
            bearing: Bearing to target in degrees
            elevation: Elevation angle in degrees
            
        Returns:
            Tuple of (azimuth, altitude) or (None, None) if invalid
        """
        # Convert bearing to azimuth (bearing is typically from north, azimuth from north clockwise)
        azimuth = bearing
        altitude = elevation
        
        # Ensure azimuth is in 0-360 range
        azimuth = azimuth % 360.0
        
        # Ensure altitude is in valid range (-90 to 90)
        altitude = max(-90.0, min(90.0, altitude))
        
        return azimuth, altitude
    
    def calculate_parameters_for_position(self, ground_lat, ground_lon, ground_alt,
                                        target_lat, target_lon, target_alt):
        """
        Calculate bearing, elevation and distance for given target coordinates
        
        Args:
            ground_lat, ground_lon, ground_alt: Ground station position
            target_lat, target_lon, target_alt: Target position
            
        Returns:
            Tuple of (bearing, elevation, distance)
        """
        bearing = self.calculate_bearing(ground_lat, ground_lon, target_lat, target_lon)
        distance = self.calculate_distance(ground_lat, ground_lon, target_lat, target_lon)
        
        if distance > 0:
            elevation = self.calculate_elevation_angle(ground_alt, target_alt, distance)
        else:
            elevation = 0.0
            
        return bearing, elevation, distance
    
    def validate_coordinates(self, lat, lon, alt=None):
        """
        Validate coordinate values
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            alt: Altitude in meters (optional)
            
        Returns:
            Boolean indicating if coordinates are valid
        """
        # Check latitude range
        if not (-90.0 <= lat <= 90.0):
            return False
        
        # Check longitude range
        if not (-180.0 <= lon <= 180.0):
            return False
        
        # Check altitude if provided (reasonable range)
        if alt is not None:
            if not (-1000.0 <= alt <= 100000.0):  # -1km to 100km
                return False
        
        # Check for null island (0,0) which is usually invalid data
        if lat == 0.0 and lon == 0.0:
            return False
        
        return True
    
    def calculate_azimuth_difference(self, az1, az2):
        """
        Calculate the shortest angular difference between two azimuth values
        Handles wraparound at 0/360 degrees
        
        Args:
            az1, az2: Azimuth values in degrees
            
        Returns:
            Angular difference in degrees (always positive, 0-180)
        """
        diff = abs(az2 - az1)
        if diff > 180:
            diff = 360 - diff
        return diff
    
    def normalize_azimuth(self, azimuth):
        """
        Normalize azimuth to 0-360 degree range
        
        Args:
            azimuth: Azimuth value in degrees
            
        Returns:
            Normalized azimuth (0-360 degrees)
        """
        while azimuth < 0:
            azimuth += 360
        while azimuth >= 360:
            azimuth -= 360
        return azimuth
    
    def clamp_altitude(self, altitude):
        """
        Clamp altitude to valid mount range
        
        Args:
            altitude: Altitude value in degrees
            
        Returns:
            Clamped altitude (-90 to 90 degrees)
        """
        return max(-90.0, min(90.0, altitude))
    
    def get_utc_time_offset(self, offset_hours=-4):
        """
        Get current UTC time with specified offset
        
        Args:
            offset_hours: Time offset from UTC (default -4 for EDT)
            
        Returns:
            datetime object with timezone
        """
        utc = pytz.UTC
        target_tz = pytz.FixedOffset(offset_hours * 60)  # Convert hours to minutes
        
        utc_now = datetime.now(utc)
        return utc_now.astimezone(target_tz)
    
    def format_coordinates(self, lat, lon, alt=None, precision=6):
        """
        Format coordinates for display
        
        Args:
            lat, lon: Latitude and longitude
            alt: Altitude (optional)
            precision: Decimal places for lat/lon
            
        Returns:
            Formatted coordinate string
        """
        lat_str = f"{lat:.{precision}f}°"
        lon_str = f"{lon:.{precision}f}°"
        
        if alt is not None:
            alt_str = f"{alt:.1f}m"
            return f"{lat_str}, {lon_str}, {alt_str}"
        else:
            return f"{lat_str}, {lon_str}"
    
    def format_bearing_elevation(self, bearing, elevation, distance=None):
        """
        Format bearing and elevation for display
        
        Args:
            bearing: Bearing in degrees
            elevation: Elevation in degrees
            distance: Distance in km (optional)
            
        Returns:
            Formatted string
        """
        bearing_str = f"Bearing: {bearing:.1f}°"
        elevation_str = f"Elevation: {elevation:.1f}°"
        
        if distance is not None:
            distance_str = f"Distance: {distance:.2f} km"
            return f"{bearing_str}, {elevation_str}, {distance_str}"
        else:
            return f"{bearing_str}, {elevation_str}"
    
    def calculate_ground_track_projection(self, lat, lon, alt, bearing, distance_km):
        """
        Calculate a point on the ground track at specified distance and bearing
        Useful for prediction and path planning
        
        Args:
            lat, lon: Starting point
            alt: Starting altitude
            bearing: Bearing in degrees
            distance_km: Distance to project in kilometers
            
        Returns:
            Tuple of (new_lat, new_lon, estimated_alt)
        """
        R = self.EARTH_RADIUS_KM
        
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing)
        
        new_lat_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance_km / R) +
            math.cos(lat_rad) * math.sin(distance_km / R) * math.cos(bearing_rad)
        )
        
        new_lon_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat_rad),
            math.cos(distance_km / R) - math.sin(lat_rad) * math.sin(new_lat_rad)
        )
        
        new_lat = math.degrees(new_lat_rad)
        new_lon = math.degrees(new_lon_rad)
        
        # Simple altitude estimation (could be enhanced with terrain data)
        estimated_alt = alt  # For now, keep same altitude
        
        return new_lat, new_lon, estimated_alt
