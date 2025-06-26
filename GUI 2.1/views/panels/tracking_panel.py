from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QGroupBox, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QColor, QPalette
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from views.widgets.compass_widget import CompassWidget

class StatusIndicator(QFrame):
    """Custom status indicator widget"""
    
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.status = "UNKNOWN"
        self.label_text = label_text
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Status label
        self.status_label = QLabel(self.label_text)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.status_label)
        
        # Status indicator
        self.indicator = QLabel("●")
        self.indicator.setAlignment(Qt.AlignCenter)
        self.indicator.setFont(QFont("Arial", 24))
        layout.addWidget(self.indicator)
        
        # Status text
        self.status_text = QLabel("UNKNOWN")
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setFont(QFont("Arial", 8))
        layout.addWidget(self.status_text)
        
        # Set initial style
        self.set_status("UNKNOWN")
        
        # Frame styling
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #2a2a2a;
            }
        """)
    
    def set_status(self, status):
        """Set the status and update colors"""
        self.status = status.upper()
        self.status_text.setText(self.status)
        
        if self.status == "OK" or self.status == "GOOD":
            color = "#00ff00"  # Green
        elif self.status == "WARNING" or self.status == "CAUTION":
            color = "#ffff00"  # Yellow
        elif self.status == "ERROR" or self.status == "CRITICAL":
            color = "#ff0000"  # Red
        else:
            color = "#888888"  # Gray for unknown
        
        self.indicator.setStyleSheet(f"color: {color};")
        self.status_text.setStyleSheet(f"color: {color};")
    
    def set_custom_status(self, text, color):
        """Set custom status text and color"""
        self.status = text
        self.status_text.setText(text)
        self.indicator.setStyleSheet(f"color: {color};")
        self.status_text.setStyleSheet(f"color: {color};")


class TrackingPanel(QWidget):
    """Panel for balloon tracking visualization and ground station operations"""
    
    def __init__(self, telemetry_model, map_controller, parent=None):
        super().__init__(parent)
        self.telemetry_model = telemetry_model
        self.map_controller = map_controller
        
        # Tracking data
        self.balloon_lat = 0.0
        self.balloon_lon = 0.0
        self.balloon_alt = 0.0
        self.ground_lat = 0.0
        self.ground_lon = 0.0
        self.bearing = 0.0
        self.elevation = 0.0
        self.distance = 0.0
        
        self.setup_ui()
        self.setup_connections()
        
        # Timer for updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(1000)  # Update every second
        
        # Timer for exposure timing (check every second for 20-second intervals)
        self.exposure_timer = QTimer()
        self.exposure_timer.timeout.connect(self.check_exposure_timing)
        self.exposure_timer.start(1000)  # Check every second
        
        # Timer for LED plot updates
        self.led_plot_timer = QTimer()
        self.led_plot_timer.timeout.connect(self.update_led_timing_plot)
        self.led_plot_timer.start(100)  # Update plot every 100ms for smooth animation
        
        # Variables for tracking LED status and exposure timing
        self.last_minute = -1  # Track minute changes
        self.last_exposure_check = 0  # Track exposure timing
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Balloon Tracking & Ground Station Control")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #00ff00; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Create main content layout
        content_layout = QHBoxLayout()
        
        # Left column - Tracking information
        left_column = self.create_tracking_section()
        content_layout.addWidget(left_column)
        
        # Right column - Status and time
        right_column = self.create_status_section()
        content_layout.addWidget(right_column)
        
        main_layout.addLayout(content_layout)
        
        # Add LED timing plot
        led_plot_section = self.create_led_timing_plot()
        main_layout.addWidget(led_plot_section)
        
        # Add stretch to push everything to top
        main_layout.addStretch()
    
    def create_tracking_section(self):
        """Create the tracking information section"""
        group = QGroupBox("Balloon Tracking")
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                font-weight: bold;
                color: #00ff00;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        layout = QGridLayout(group)
        layout.setSpacing(15)
        
        # Compass for bearing
        compass_frame = QFrame()
        compass_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        compass_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #2a2a2a;
            }
        """)
        compass_layout = QVBoxLayout(compass_frame)
        
        compass_label = QLabel("Bearing to Balloon")
        compass_label.setAlignment(Qt.AlignCenter)
        compass_label.setFont(QFont("Arial", 12, QFont.Bold))
        compass_label.setStyleSheet("color: #ffffff; margin: 5px;")
        compass_layout.addWidget(compass_label)
        
        self.bearing_compass = CompassWidget()
        self.bearing_compass.setFixedSize(150, 150)
        compass_layout.addWidget(self.bearing_compass, 0, Qt.AlignCenter)
        
        self.bearing_label = QLabel("---°")
        self.bearing_label.setAlignment(Qt.AlignCenter)
        self.bearing_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.bearing_label.setStyleSheet("color: #00ff00; margin: 5px;")
        compass_layout.addWidget(self.bearing_label)
        
        layout.addWidget(compass_frame, 0, 0, 2, 1)
        
        # Tracking parameters
        params_frame = QFrame()
        params_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        params_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #2a2a2a;
                padding: 10px;
            }
        """)
        params_layout = QGridLayout(params_frame)
        
        # Balloon altitude
        self.add_parameter_display(params_layout, "Balloon Altitude:", "altitude_label", "--- m", 0)
        
        # Elevation angle
        self.add_parameter_display(params_layout, "Elevation Angle:", "elevation_label", "---°", 1)
        
        # Distance
        self.add_parameter_display(params_layout, "Distance:", "distance_label", "--- km", 2)
        
        # Right Ascension
        self.add_parameter_display(params_layout, "Right Ascension:", "ra_label", "---h ---m", 3)
        
        # Declination
        self.add_parameter_display(params_layout, "Declination:", "dec_label", "---° ---'", 4)
        
        layout.addWidget(params_frame, 0, 1)
        
        return group
    
    def create_status_section(self):
        """Create the status and time section"""
        group = QGroupBox("System Status & Time")
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                font-weight: bold;
                color: #00ff00;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # UTC Time display
        time_frame = QFrame()
        time_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        time_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #2a2a2a;
                padding: 15px;
            }
        """)
        time_layout = QVBoxLayout(time_frame)
        
        utc_title = QLabel("UTC Time")
        utc_title.setAlignment(Qt.AlignCenter)
        utc_title.setFont(QFont("Arial", 12, QFont.Bold))
        utc_title.setStyleSheet("color: #ffffff; margin-bottom: 5px;")
        time_layout.addWidget(utc_title)
        
        self.utc_time_label = QLabel("--:--:--")
        self.utc_time_label.setAlignment(Qt.AlignCenter)
        self.utc_time_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.utc_time_label.setStyleSheet("color: #00ff00;")
        time_layout.addWidget(self.utc_time_label)
        
        self.utc_date_label = QLabel("----/--/--")
        self.utc_date_label.setAlignment(Qt.AlignCenter)
        self.utc_date_label.setFont(QFont("Arial", 12))
        self.utc_date_label.setStyleSheet("color: #ffffff;")
        time_layout.addWidget(self.utc_date_label)
        
        # Time source indicator
        self.time_source_label = QLabel("System")
        self.time_source_label.setAlignment(Qt.AlignCenter)
        self.time_source_label.setFont(QFont("Arial", 8))
        self.time_source_label.setStyleSheet("color: #888888; margin-top: 5px;")
        time_layout.addWidget(self.time_source_label)
        
        layout.addWidget(time_frame)
        
        # Status indicators
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        status_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #2a2a2a;
                padding: 10px;
            }
        """)
        status_layout = QGridLayout(status_frame)
        
        status_title = QLabel("System Status")
        status_title.setAlignment(Qt.AlignCenter)
        status_title.setFont(QFont("Arial", 12, QFont.Bold))
        status_title.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        status_layout.addWidget(status_title, 0, 0, 1, 3)
        
        # Three status indicators
        self.status1 = StatusIndicator("GPS Lock")
        self.status2 = StatusIndicator("Radio Link")
        self.status3 = StatusIndicator("Source LED")  # Changed to Source LED for LED status
        
        status_layout.addWidget(self.status1, 1, 0)
        status_layout.addWidget(self.status2, 1, 1)
        status_layout.addWidget(self.status3, 1, 2)
        
        layout.addWidget(status_frame)
        
        # Add stretch
        layout.addStretch()
        
        return group
    
    def add_parameter_display(self, layout, label_text, value_attr, default_value, row):
        """Add a parameter display to the layout"""
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 10, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")
        
        value_label = QLabel(default_value)
        value_label.setFont(QFont("Arial", 12, QFont.Bold))
        value_label.setStyleSheet("color: #00ff00;")
        
        # Store reference to value label
        setattr(self, value_attr, value_label)
        
        layout.addWidget(label, row, 0)
        layout.addWidget(value_label, row, 1)
    
    def setup_connections(self):
        """Connect to model signals"""
        self.telemetry_model.position_updated.connect(self.update_balloon_position)
        self.telemetry_model.ground_station_gps_updated.connect(self.update_ground_position)
        self.map_controller.user_location_changed.connect(self.update_ground_position_from_controller)
    
    def update_balloon_position(self, lat, lon, alt):
        """Update balloon position and recalculate tracking"""
        if lat != 0 and lon != 0:
            self.balloon_lat = lat
            self.balloon_lon = lon
            self.balloon_alt = alt
            self.calculate_tracking_parameters()
    
    def update_ground_position(self, lat, lon, alt):
        """Update ground station position from GPS"""
        self.ground_lat = lat
        self.ground_lon = lon
        self.calculate_tracking_parameters()
    
    def update_ground_position_from_controller(self, lat, lon):
        """Update ground station position from map controller"""
        self.ground_lat = lat
        self.ground_lon = lon
        self.calculate_tracking_parameters()
    
    def calculate_tracking_parameters(self):
        """Calculate bearing, elevation, distance, and celestial coordinates"""
        if self.ground_lat == 0 or self.ground_lon == 0 or self.balloon_lat == 0 or self.balloon_lon == 0:
            return
        
        # Calculate bearing
        self.bearing = self.calculate_bearing(self.ground_lat, self.ground_lon, 
                                            self.balloon_lat, self.balloon_lon)
        
        # Calculate distance
        self.distance = self.calculate_distance(self.ground_lat, self.ground_lon,
                                              self.balloon_lat, self.balloon_lon)
        
        # Calculate elevation angle
        if self.distance > 0:
            # Convert distance to meters and calculate elevation
            distance_m = self.distance * 1000
            height_diff = self.balloon_alt  # Assuming ground station at sea level
            self.elevation = math.degrees(math.atan2(height_diff, distance_m))
        else:
            self.elevation = 0
        
        # Update compass
        self.bearing_compass.setBearing(self.bearing)
    
    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate bearing from point 1 to point 2"""
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
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat_rad = math.radians(lat2 - lat1)
        dlon_rad = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat_rad/2) * math.sin(dlat_rad/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(dlon_rad/2) * math.sin(dlon_rad/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def calculate_celestial_coordinates(self):
        """Calculate right ascension and declination (simplified)"""
        # This is a simplified calculation - for accurate celestial coordinates,
        # you would need proper astronomical calculations including time, location, etc.
        
        # For now, we'll convert the bearing and elevation to approximate celestial coordinates
        # This is NOT astronomically accurate but provides placeholder values
        
        # Convert bearing to RA (very rough approximation)
        ra_hours = self.bearing / 15.0  # 360° / 24h = 15°/h
        ra_h = int(ra_hours)
        ra_m = int((ra_hours - ra_h) * 60)
        
        # Use elevation as declination approximation
        dec_deg = int(self.elevation)
        dec_min = int((self.elevation - dec_deg) * 60)
        
        return ra_h, ra_m, dec_deg, dec_min
    
    def update_displays(self):
        """Update all display elements"""
        # Update bearing display
        self.bearing_label.setText(f"{self.bearing:.1f}°")
        
        # Update tracking parameters
        self.altitude_label.setText(f"{self.balloon_alt:.1f} m")
        self.elevation_label.setText(f"{self.elevation:.1f}°")
        self.distance_label.setText(f"{self.distance:.2f} km")
        
        # Calculate and update celestial coordinates
        ra_h, ra_m, dec_deg, dec_min = self.calculate_celestial_coordinates()
        self.ra_label.setText(f"{ra_h:02d}h {ra_m:02d}m")
        self.dec_label.setText(f"{dec_deg:+03d}° {abs(dec_min):02d}'")
        
        # Update UTC time from ground station GPS if available
        if hasattr(self.telemetry_model, 'gs_gps_utc_unix') and self.telemetry_model.gs_gps_utc_unix > 0:
            # Use ground station GPS UTC time
            gps_utc_time = QDateTime.fromSecsSinceEpoch(int(self.telemetry_model.gs_gps_utc_unix))
            gps_utc_time.setTimeSpec(Qt.UTC)
            self.utc_time_label.setText(gps_utc_time.toString("hh:mm:ss"))
            self.utc_date_label.setText(gps_utc_time.toString("yyyy/MM/dd"))
            
            # Update source indicator
            self.time_source_label.setText("GPS")
            self.time_source_label.setStyleSheet("color: #00ff00; margin-top: 5px;")
            
            # Add GPS indicator to show source
            self.utc_time_label.setToolTip("UTC time from Ground Station GPS")
            self.utc_date_label.setToolTip("UTC date from Ground Station GPS")
        else:
            # Fallback to system UTC time
            utc_now = QDateTime.currentDateTimeUtc()
            self.utc_time_label.setText(utc_now.toString("hh:mm:ss"))
            self.utc_date_label.setText(utc_now.toString("yyyy/MM/dd"))
            
            # Update source indicator
            self.time_source_label.setText("System")
            self.time_source_label.setStyleSheet("color: #888888; margin-top: 5px;")
            
            # Add indicator to show source
            self.utc_time_label.setToolTip("UTC time from System Clock (GPS not available)")
            self.utc_date_label.setToolTip("UTC date from System Clock (GPS not available)")
        
        # Update status indicators based on telemetry
        self.update_status_indicators()
        
        # Update LED status based on UTC time (after other status updates)
        self.update_led_status()
    
    def update_status_indicators(self):
        """Update status indicators based on system state"""
        # GPS Lock status
        if hasattr(self.telemetry_model, 'gps_valid') and self.telemetry_model.gps_valid:
            self.status1.set_status("OK")
        else:
            self.status1.set_status("ERROR")
        
        # Radio Link status (based on recent telemetry)
        if hasattr(self.telemetry_model, 'rssi') and self.telemetry_model.rssi > -100:
            if self.telemetry_model.rssi > -80:
                self.status2.set_status("OK")
            else:
                self.status2.set_status("WARNING")
        else:
            self.status2.set_status("ERROR")
        
        # Don't update status3 here - it's used for LED status
        # LED status is updated by update_led_status() method
    
    def get_current_utc_time(self):
        """Get current UTC time, preferring GPS time if available"""
        if hasattr(self.telemetry_model, 'gs_gps_utc_unix') and self.telemetry_model.gs_gps_utc_unix > 0:
            # Use ground station GPS UTC time
            return QDateTime.fromSecsSinceEpoch(int(self.telemetry_model.gs_gps_utc_unix))
        else:
            # Fallback to system UTC time
            return QDateTime.currentDateTimeUtc()
    
    def check_exposure_timing(self):
        """Check for exposure timing and LED status updates based on GPS UTC time"""
        current_utc = self.get_current_utc_time()
        current_minute = current_utc.time().minute()
        current_second = current_utc.time().second()
        
        # Check if minute has changed for LED status update
        if current_minute != self.last_minute:
            self.update_led_status()
            self.last_minute = current_minute
        
        # Check for exposure timing (only during even minutes)
        if current_minute % 2 == 0:  # Even minute
            # Calculate seconds from start of minute
            seconds_in_minute = current_second
            
            # Check if we should send EXPOSURE START message every 20 seconds
            # (at 0, 20, 40 seconds of even minutes)
            if seconds_in_minute % 20 == 0 and seconds_in_minute != self.last_exposure_check:
                print("EXPOSURE START")
                self.last_exposure_check = seconds_in_minute
        else:
            # Reset exposure check for odd minutes
            self.last_exposure_check = -1
    
    def update_led_status(self):
        """Update LED status indicator based on even/odd minute"""
        utc_time = self.get_current_utc_time()
        current_minute = utc_time.time().minute()
        
        print(f"DEBUG: Updating LED status - Current UTC minute: {current_minute}")
        
        if current_minute % 2 == 0:  # Even minute
            # Show red indicator for "Source LED on"
            print("DEBUG: Setting Source LED On (Red)")
            self.status3.set_custom_status("Source LED On", "#ff0000")  # Red
        else:  # Odd minute
            # Show green indicator for "Tracking LED on"
            print("DEBUG: Setting Tracking LED On (Green)")
            self.status3.set_custom_status("Tracking LED On", "#00ff00")  # Green
    
    def create_led_timing_plot(self):
        """Create LED timing plot showing red and green LED patterns"""
        group = QGroupBox("LED Timing Pattern")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                color: #00ff00;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        # Create matplotlib figure and canvas
        self.led_figure = Figure(figsize=(12, 3), facecolor='#2a2a2a')
        self.led_canvas = FigureCanvas(self.led_figure)
        self.led_canvas.setStyleSheet("background-color: #2a2a2a;")
        
        # Create subplot
        self.led_ax = self.led_figure.add_subplot(111, facecolor='#2a2a2a')
        
        # Initialize plot data (2 minutes window)
        self.time_window = 120  # 2 minutes in seconds
        
        # Initialize plot lines
        self.red_line, = self.led_ax.plot([], [], 'r-', linewidth=3, label='Red LED (Source: 10s ON/OFF)')
        self.green_line, = self.led_ax.plot([], [], 'g-', linewidth=3, label='Green LED (Tracking: 1s ON/OFF)')
        
        # Configure plot
        self.led_ax.set_xlim(0, self.time_window)
        self.led_ax.set_ylim(-0.5, 2.5)
        self.led_ax.set_xlabel('UTC Time', color='white')
        self.led_ax.set_ylabel('LED State', color='white')
        self.led_ax.tick_params(colors='white')
        self.led_ax.grid(True, alpha=0.3, color='white')
        self.led_ax.legend(facecolor='#2a2a2a', edgecolor='white', labelcolor='white')
        
        # Set LED state labels
        self.led_ax.set_yticks([0, 1, 2])
        self.led_ax.set_yticklabels(['OFF', 'Red ON', 'Green ON'], color='white')
        
        # Style the plot
        self.led_figure.patch.set_facecolor('#2a2a2a')
        self.led_ax.spines['bottom'].set_color('white')
        self.led_ax.spines['top'].set_color('white')
        self.led_ax.spines['right'].set_color('white')
        self.led_ax.spines['left'].set_color('white')
        
        layout.addWidget(self.led_canvas)
        
        return group

    def update_led_timing_plot(self):
        """Update LED timing plot with current patterns"""
        current_time = time.time()
        
        # Create time array for the rolling window (past 2 minutes)
        time_points = np.linspace(current_time - self.time_window, current_time, self.time_window * 10)
        
        # Calculate LED states for each time point
        red_states = []
        green_states = []
        
        for t in time_points:
            # Convert to UTC time for this point
            abs_utc = QDateTime.fromSecsSinceEpoch(int(t))
            abs_utc.setTimeSpec(Qt.UTC)
            abs_minute = abs_utc.time().minute()
            abs_second = abs_utc.time().second()
            
            # RED LED pattern: even minutes, ON for 10s, OFF for 10s
            if abs_minute % 2 == 0:  # Even minute
                # 10 seconds on, 10 seconds off pattern
                cycle_pos = abs_second % 20
                red_state = 1 if cycle_pos < 10 else 0
            else:
                red_state = 0
            
            # GREEN LED pattern: odd minutes, ON for 1s, OFF for 1s
            if abs_minute % 2 == 1:  # Odd minute
                # 1 second on, 1 second off pattern
                cycle_pos = abs_second % 2
                green_state = 2 if cycle_pos < 1 else 0
            else:
                green_state = 0
            
            red_states.append(red_state)
            green_states.append(green_state)
        
        # Convert time points to relative seconds for display
        relative_time = time_points - time_points[0]
        
        # Update plot data
        self.red_line.set_data(relative_time, red_states)
        self.green_line.set_data(relative_time, green_states)
        
        # Update x-axis to show current time window
        self.led_ax.set_xlim(0, self.time_window)
        
        # Clear previous current time indicator and add new one
        # Remove old vertical lines except the data lines
        for line in self.led_ax.lines[2:]:  # Keep only the red and green lines
            line.remove()
        
        # Add current time indicator at the end
        self.led_ax.axvline(x=self.time_window, color='yellow', linestyle='--', alpha=0.7, linewidth=2)
        
        # Update time labels on x-axis to show actual times
        current_utc = QDateTime.fromSecsSinceEpoch(int(current_time))
        start_utc = QDateTime.fromSecsSinceEpoch(int(current_time - self.time_window))
        
        # Set custom x-axis labels
        x_ticks = np.linspace(0, self.time_window, 5)
        x_labels = []
        for tick in x_ticks:
            tick_time = QDateTime.fromSecsSinceEpoch(int(current_time - self.time_window + tick))
            tick_time.setTimeSpec(Qt.UTC)
            x_labels.append(tick_time.toString("hh:mm:ss"))
        
        self.led_ax.set_xticks(x_ticks)
        self.led_ax.set_xticklabels(x_labels, rotation=45, fontsize=8)
        
        # Refresh canvas
        self.led_canvas.draw()
