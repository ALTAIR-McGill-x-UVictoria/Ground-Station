from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QGroupBox, QSizePolicy, QSpacerItem, QSpinBox, QDoubleSpinBox, QPushButton, QMessageBox
)
from PyQt5.QtCore import QDateTime, QTimeZone, Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QColor, QPalette
import time
import math
import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import os
import sys
from views.widgets.compass_widget import CompassWidget
import pytz
from datetime import datetime
from .EKF_algo.EKF import EKF

# Import the new controller classes
from controllers.mount_controller import MountController
from controllers.camera_controller import CameraController
from controllers.tracking_calculator import TrackingCalculator

# For backward compatibility, keep the RGB_photo function
try:
    from controllers.camera_controller import RGB_photo
except ImportError:
    def RGB_photo(filename, gain, exposure):
        print(f"CAMERA NOT AVAILABLE - Would capture RGB: {filename} with gain={gain}, exposure={exposure}")

class StatusIndicator(QFrame):
    """Custom status indicator widget"""
    
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.status = "UNKNOWN"
        self.label_text = label_text
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        
        # Status label
        self.status_label = QLabel(self.label_text)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 8, QFont.Bold))
        self.status_label.setStyleSheet("color: #ffffff;")  # Ensure white text
        layout.addWidget(self.status_label)
        
        # Status indicator
        self.indicator = QLabel("●")
        self.indicator.setAlignment(Qt.AlignCenter)
        self.indicator.setFont(QFont("Arial", 16))
        layout.addWidget(self.indicator)
        
        # Status text
        self.status_text = QLabel("UNKNOWN")
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setFont(QFont("Arial", 7))
        layout.addWidget(self.status_text)
        
        # Frame styling
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
                padding: 2px;
                min-height: 60px;
                max-height: 80px;
            }
        """)
        
        # Set initial style after UI is created
        self.set_status("UNKNOWN")
    
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
        
        # Set styles with important flag to override any conflicting styles
        self.indicator.setStyleSheet(f"color: {color} !important; background: transparent;")
        self.status_text.setStyleSheet(f"color: {color} !important; background: transparent;")
        
        # Debug print
        print(f"StatusIndicator '{self.label_text}' set to {self.status} with color {color}")
    
    def set_custom_status(self, text, color):
        """Set custom status text and color"""
        self.status = text
        self.status_text.setText(text)
        self.indicator.setStyleSheet(f"color: {color} !important; background: transparent;")
        self.status_text.setStyleSheet(f"color: {color} !important; background: transparent;")
        
        # Debug print
        print(f"StatusIndicator '{self.label_text}' set to custom '{text}' with color {color}")


class TrackingPanel(QWidget):
    """Panel for balloon tracking visualization and ground station operations"""
    
    def __init__(self, telemetry_model, map_controller, parent=None):
        super().__init__(parent)
        self.telemetry_model = telemetry_model
        self.map_controller = map_controller
        
        # Initialize controllers
        self._init_controllers()
        
        # Initialize data members
        self._init_data_members()
        
        # Initialize UI and connections
        self._init_ui_and_connections()
        
        # Initialize timers
        self._init_timers()
    
    def _init_controllers(self):
        """Initialize hardware and calculation controllers"""
        # Mount controller
        self.mount_controller = MountController()
        
        # Camera controller  
        self.camera_controller = CameraController()
        
        # Tracking calculator
        self.tracking_calculator = TrackingCalculator()
        
        # EKF for prediction
        self.ekf = EKF()
        
        print("Controllers initialized successfully")
    
    def _init_data_members(self):
        """Initialize data members and state variables"""
        # Tracking data
        self.balloon_lat = 0
        self.balloon_lon = 0
        self.balloon_alt = 0
        self.ground_lat = 0.0
        self.ground_lon = 0.0
        self.ground_alt = 0.0
        self.bearing = 0.0
        self.elevation = 0.0
        self.distance = 0.0
        self.slew_in_progress = False
        self.mount_at_target = False  # Track if mount has reached target position
        self.mount_settled_tolerance = 1.0  # Default tolerance for mount positioning (degrees)
        self.last_sent_azimuth = None  # Track last commanded azimuth
        self.last_sent_altitude = None  # Track last commanded altitude
        
        # Prediction data
        self.pred_lat = 0.0
        self.pred_lon = 0.0
        self.pred_alt = 0.0
        self.tracking_enabled = True
        self.last_pred_slew_time = 0
        
        # Manual mount control mode
        self.manual_control_mode = False  # False = auto tracking, True = manual control
        
        # Variables for tracking LED status and exposure timing
        self.last_minute = -1  # Track minute changes
        self.last_exposure_check = -1  # Track exposure timing
        
        # Acceleration data
        self.acc_x = 0
        self.acc_y = 0
        self.acc_z = 0
        
        # Logging setup
        self.log_dir = os.path.join(os.path.dirname(__file__), '../../logs')
        os.makedirs(self.log_dir, exist_ok=True)
        now = datetime.utcnow().strftime('%Y-%m-%d %H-%M-%S')
        self.log_file = os.path.join(self.log_dir, f'tracking_panel_log_{now}.txt')
        
        print("Data members initialized")
    
    def _init_ui_and_connections(self):
        """Initialize UI and setup connections"""
        self.setup_ui()
        self.setup_connections()
        print("UI and connections initialized")
    
    def _init_timers(self):
        """Initialize update timers"""
        # Main update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(1000)  # Update every second
        
        # Exposure timing timer
        self.exposure_timer = QTimer()
        self.exposure_timer.timeout.connect(self.check_exposure_timing)
        self.exposure_timer.start(1000)  # Check every second
        
        # LED plot timer
        self.led_plot_timer = QTimer()
        self.led_plot_timer.timeout.connect(self.update_led_timing_plot)
        self.led_plot_timer.start(100)  # Update plot every 100ms for smooth animation
        
        # Start prediction thread
        self.prediction_thread = threading.Thread(target=self.prediction_loop, daemon=True)
        self.prediction_thread.start()
        
        print("Timers and threads initialized")
    
    def set_mount_port_getter(self, port_getter_func):
        """Set a function that returns the currently selected mount port"""
        self.mount_controller.set_port_getter(port_getter_func)
    
    def reconnect_mount(self):
        """Reconnect to mount with current port selection"""
        return self.mount_controller.reconnect()
    
    def move_to_azalt_position(self, azimuth, altitude):
        """Move mount to specific azimuth/altitude position"""
        return self.mount_controller.move_to_position(azimuth, altitude)
    
    def move_to_azalt_position_precise(self, azimuth, altitude, precision_threshold=1.0):
        """Move mount to specific azimuth/altitude position with precision control"""
        return self.mount_controller.move_to_position_precise(azimuth, altitude, precision_threshold)
    
    def get_mount_position(self):
        """Get current mount position"""
        return self.mount_controller.get_position()
    
    def is_mount_moving(self):
        """Check if mount is currently moving"""
        return self.mount_controller.is_moving()
    
    def should_send_new_position(self, target_az, target_alt):
        """Determine if we should send a new position to the mount"""
        return self.mount_controller.should_send_new_position(target_az, target_alt)
    
    def update_last_sent_position(self, azimuth, altitude):
        """Update the last sent position tracking"""
        self.mount_controller.update_last_sent_position(azimuth, altitude)
    
    def set_position_tolerance(self, tolerance_degrees):
        """Set the minimum position change required to send new coordinates"""
        self.mount_controller.set_position_tolerance(tolerance_degrees)
    
    def set_settled_tolerance(self, tolerance_degrees):
        """Set the tolerance for considering the mount 'at target'"""
        self.mount_controller.set_settled_tolerance(tolerance_degrees)
    
    def force_new_position(self, azimuth, altitude):
        """Force the mount to move to a new position regardless of tolerances"""
        self.mount_controller.force_move_to_position(azimuth, altitude)
    
    @property
    def mount_connected(self):
        """Check if mount is connected"""
        return self.mount_controller.is_connected()
    
    def update_manual_control_states(self):
        """Update the enabled state of manual control buttons based on mount connection"""
        if hasattr(self, 'goto_button'):
            connected = self.mount_connected
            self.goto_button.setEnabled(connected)
            self.reset_button.setEnabled(connected)
            self.get_position_button.setEnabled(connected)
            self.reconnect_mount_button.setEnabled(True)  # Always enabled
            self.mode_toggle_button.setEnabled(True)  # Always enabled
    
    def should_send_new_position(self, target_az, target_alt):
        """Check if we should send a new position to the mount"""
        # Check if mount is still moving to the last target
        if self.is_mount_moving():
            return False  # Don't send new position while moving
        
        # Check if mount is at the target position
        current_az, current_alt = self.get_mount_position()
        if current_az is not None and current_alt is not None:
            az_error = abs(current_az - target_az)
            alt_error = abs(current_alt - target_alt)
            
            # Handle azimuth wraparound
            if az_error > 180:
                az_error = 360 - az_error
                
            if az_error <= self.mount_settled_tolerance and alt_error <= self.mount_settled_tolerance:
                if not self.mount_at_target:
                    print(f"Mount reached target position within tolerance (Az±{az_error:.2f}°, Alt±{alt_error:.2f}°)")
                    self.mount_at_target = True
                return False  # Mount is at target, don't send again
            else:
                self.mount_at_target = False
        
        return True  # Should send new position
    
    def update_last_sent_position(self, azimuth, altitude):
        """Update the last sent position tracking"""
        self.last_sent_azimuth = azimuth
        self.last_sent_altitude = altitude
        self.mount_at_target = False  # Reset since we're sending a new position
    
    def set_position_tolerance(self, tolerance_degrees):
        """Set the minimum position change required to send new coordinates"""
        self.position_tolerance = max(0.1, tolerance_degrees)  # Minimum 0.1 degrees
        print(f"Position tolerance set to {self.position_tolerance:.1f}°")
    
    def set_settled_tolerance(self, tolerance_degrees):
        """Set the tolerance for considering the mount 'at target'"""
        self.mount_settled_tolerance = max(0.1, tolerance_degrees)  # Minimum 0.1 degrees
        print(f"Mount settled tolerance set to {self.mount_settled_tolerance:.1f}°")
    
    def force_new_position(self, azimuth, altitude):
        """Force the mount to move to a new position regardless of tolerances"""
        print(f"Force positioning to Az={azimuth:.2f}°, Alt={altitude:.2f}°")
        self.last_sent_azimuth = azimuth  # Reset to force movement
        self.last_sent_altitude = altitude
        self.safe_slew_azalt(azimuth, altitude)
    
    def setup_ui(self):
        """Set up the user interface for the tracking panel"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        # Create main content layout (removed title)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(8)
        
        # Left column - Tracking information
        left_column = self.create_tracking_section()
        content_layout.addWidget(left_column, 1)  # Reduced space for tracking
        
        # Right column - Status and time
        right_column = self.create_status_section()
        content_layout.addWidget(right_column, 1)  # Equal space for status
        
        main_layout.addLayout(content_layout)
        
        # Add manual mount control section
        mount_control_section = self.create_manual_mount_control_section()
        main_layout.addWidget(mount_control_section)
        
        # Add LED timing plot
        led_plot_section = self.create_led_timing_plot()
        main_layout.addWidget(led_plot_section)
        
        # No stretch - let components fill available space
    
    def create_tracking_section(self):
        """Create the tracking information section, including manual ground station entry"""
        group = QGroupBox("Balloon Tracking")
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 1ex;
                font-weight: bold;
                color: #00ff00;
                font-size: 12px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)

        layout = QGridLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # Compass for bearing (make it more compact)
        compass_frame = QFrame()
        compass_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        compass_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
            }
        """)
        compass_layout = QVBoxLayout(compass_frame)
        compass_layout.setSpacing(2)  # Tighter spacing
        compass_layout.setContentsMargins(6, 6, 6, 6)  # Smaller margins

        compass_label = QLabel("Bearing to Balloon")
        compass_label.setAlignment(Qt.AlignCenter)
        compass_label.setFont(QFont("Arial", 9, QFont.Bold))  # Smaller font
        compass_label.setStyleSheet("color: #ffffff; margin: 1px;")  # Less margin
        compass_layout.addWidget(compass_label)

        self.bearing_compass = CompassWidget()
        self.bearing_compass.setFixedSize(100, 100)  # Smaller compass (was 120x120)
        compass_layout.addWidget(self.bearing_compass, 0, Qt.AlignCenter)

        self.bearing_label = QLabel("---°")
        self.bearing_label.setAlignment(Qt.AlignCenter)
        self.bearing_label.setFont(QFont("Arial", 11, QFont.Bold))  # Slightly smaller font
        self.bearing_label.setStyleSheet("color: #00ff00; margin: 1px;")  # Less margin
        compass_layout.addWidget(self.bearing_label)

        layout.addWidget(compass_frame, 0, 0, 2, 1)

        # Tracking parameters (more compact)
        params_frame = QFrame()
        params_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        params_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
                padding: 6px;
            }
        """)
        params_layout = QGridLayout(params_frame)
        params_layout.setSpacing(4)
        params_layout.setContentsMargins(6, 6, 6, 6)

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
        
        self.add_parameter_display(params_layout, "Pred Bearing:", "pred_bearing_label", "---°", 5)

        layout.addWidget(params_frame, 0, 1)

        # Manual ground station entry section
        manual_frame = QFrame()
        manual_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        manual_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #232323;
                padding: 6px;
            }
        """)
        manual_layout = QGridLayout(manual_frame)
        manual_layout.setSpacing(4)
        manual_layout.setContentsMargins(6, 6, 6, 6)

        manual_label = QLabel("Manual Ground Station Coordinates")
        manual_label.setFont(QFont("Arial", 9, QFont.Bold))
        manual_label.setStyleSheet("color: #00ff00;")
        manual_layout.addWidget(manual_label, 0, 0, 1, 3)

        # Latitude
        lat_label = QLabel("Lat:")
        lat_label.setFont(QFont("Arial", 8))
        lat_label.setStyleSheet("color: #ffffff;")
        manual_layout.addWidget(lat_label, 1, 0)
        self.manual_lat_spin = QDoubleSpinBox()
        self.manual_lat_spin.setRange(-90.0, 90.0)
        self.manual_lat_spin.setDecimals(6)
        self.manual_lat_spin.setSingleStep(0.0001)
        self.manual_lat_spin.setValue(self.ground_lat)
        self.manual_lat_spin.setStyleSheet("background-color: #2a2a2a; color: #ffffff; border: 1px solid #3a3a3a; border-radius: 2px; min-width: 80px;")
        manual_layout.addWidget(self.manual_lat_spin, 1, 1)

        # Longitude
        lon_label = QLabel("Lon:")
        lon_label.setFont(QFont("Arial", 8))
        lon_label.setStyleSheet("color: #ffffff;")
        manual_layout.addWidget(lon_label, 2, 0)
        self.manual_lon_spin = QDoubleSpinBox()
        self.manual_lon_spin.setRange(-180.0, 180.0)
        self.manual_lon_spin.setDecimals(6)
        self.manual_lon_spin.setSingleStep(0.0001)
        self.manual_lon_spin.setValue(self.ground_lon)
        self.manual_lon_spin.setStyleSheet("background-color: #2a2a2a; color: #ffffff; border: 1px solid #3a3a3a; border-radius: 2px; min-width: 80px;")
        manual_layout.addWidget(self.manual_lon_spin, 2, 1)

        # Altitude
        alt_label = QLabel("Alt (m):")
        alt_label.setFont(QFont("Arial", 8))
        alt_label.setStyleSheet("color: #ffffff;")
        manual_layout.addWidget(alt_label, 3, 0)
        self.manual_alt_spin = QDoubleSpinBox()
        self.manual_alt_spin.setRange(-500.0, 9000.0)
        self.manual_alt_spin.setDecimals(2)
        self.manual_alt_spin.setSingleStep(0.1)
        self.manual_alt_spin.setValue(self.ground_alt)
        self.manual_alt_spin.setStyleSheet("background-color: #2a2a2a; color: #ffffff; border: 1px solid #3a3a3a; border-radius: 2px; min-width: 80px;")
        manual_layout.addWidget(self.manual_alt_spin, 3, 1)

        # Apply button
        self.manual_apply_btn = QPushButton("Apply")
        self.manual_apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        manual_layout.addWidget(self.manual_apply_btn, 4, 0, 1, 2)

        # Add manual entry frame to layout (below params)
        layout.addWidget(manual_frame, 2, 0, 1, 2)

        # Connect apply button
        self.manual_apply_btn.clicked.connect(self.apply_manual_ground_station)

        return group
    
    def log_tracking_data(self):
        """Log all tracking panel data to a separate file"""
        import datetime
        data = {
            'timestamp_utc': self.get_current_utc_time().toPyDateTime(),
            'balloon_lat': self.balloon_lat,
            'balloon_lon': self.balloon_lon,
            'balloon_alt': self.balloon_alt,
            'ground_lat': self.ground_lat,
            'ground_lon': self.ground_lon,
            'ground_alt': self.ground_alt,
            'bearing': self.bearing,
            'elevation': self.elevation,
            'distance': self.distance,
        }
        # Add target mount coordinates
        try:
            target_az, target_alt = self.calculate_target_coordinates()
            if target_az is not None and target_alt is not None:
                data['target_azimuth'] = f'{target_az:.2f}'
                data['target_altitude'] = f'{target_alt:.2f}'
            else:
                data['target_azimuth'] = 'No GPS'
                data['target_altitude'] = 'No GPS'
            
            # Add current mount position if available
            current_az, current_alt = self.get_mount_position()
            if current_az is not None and current_alt is not None:
                data['mount_azimuth'] = f'{current_az:.2f}'
                data['mount_altitude'] = f'{current_alt:.2f}'
            else:
                data['mount_azimuth'] = 'N/A'
                data['mount_altitude'] = 'N/A'
                
        except Exception as e:
            data['target_azimuth'] = 'N/A'
            data['target_altitude'] = 'N/A'
            data['mount_azimuth'] = 'N/A'
            data['mount_altitude'] = 'N/A'
            
        # Write as a single line (CSV style)
        with open(self.log_file, 'a') as f:
            f.write(','.join(f'{k}={v}' for k, v in data.items()) + '\n')

    def apply_manual_ground_station(self):
        """Apply manual ground station coordinates from user input"""
        lat = self.manual_lat_spin.value()
        lon = self.manual_lon_spin.value()
        alt = self.manual_alt_spin.value()
        print(f"Manual ground station set: lat={lat}, lon={lon}, alt={alt}")
        self.ground_lat = lat
        self.ground_lon = lon
        self.ground_alt = alt
        self.calculate_tracking_parameters()
        # Optionally, emit a signal or update map_controller if needed
        # If you want to propagate this to the map_controller, you could do:
        # self.map_controller.set_user_location(lat, lon, alt)
        # But only if such a method exists and is appropriate
    
    def update_camera_gain(self, value):
        """Update camera gain setting"""
        if self.camera_controller.set_gain(value):
            print(f"Camera gain updated to: {value}")
        else:
            print(f"Failed to update camera gain to: {value}")
    
    def update_camera_exposure(self, value):
        """Update camera exposure setting (value in milliseconds)"""
        if self.camera_controller.set_exposure_ms(value):
            print(f"Camera exposure updated to: {value} ms")
        else:
            print(f"Failed to update camera exposure to: {value} ms")
    
    def initialize_camera_for_capture(self):
        """Initialize camera for capture"""
        return self.camera_controller.prepare_for_capture()
    
    def generate_filename(self):
        """Generate a unique filename for camera capture"""
        return self.camera_controller.generate_filename("balloon_tracking")
    
    def create_status_section(self):
        """Create the status and time section"""
        group = QGroupBox("System Status & Time")
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 1ex;
                font-weight: bold;
                color: #00ff00;
                font-size: 12px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # UTC Time display (more compact)
        time_frame = QFrame()
        time_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        time_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
                padding: 8px;
            }
        """)
        time_layout = QVBoxLayout(time_frame)
        time_layout.setSpacing(2)
        time_layout.setContentsMargins(4, 4, 4, 4)
        
        utc_title = QLabel("UTC Time")
        utc_title.setAlignment(Qt.AlignCenter)
        utc_title.setFont(QFont("Arial", 10, QFont.Bold))
        utc_title.setStyleSheet("color: #ffffff; margin-bottom: 2px;")
        time_layout.addWidget(utc_title)
        
        self.utc_time_label = QLabel("--:--:--")
        self.utc_time_label.setAlignment(Qt.AlignCenter)
        self.utc_time_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.utc_time_label.setStyleSheet("color: #00ff00;")
        time_layout.addWidget(self.utc_time_label)
        
        self.utc_date_label = QLabel("----/--/--")
        self.utc_date_label.setAlignment(Qt.AlignCenter)
        self.utc_date_label.setFont(QFont("Arial", 10))
        self.utc_date_label.setStyleSheet("color: #ffffff;")
        time_layout.addWidget(self.utc_date_label)
        
        # Time source indicator
        self.time_source_label = QLabel("System")
        self.time_source_label.setAlignment(Qt.AlignCenter)
        self.time_source_label.setFont(QFont("Arial", 8))
        self.time_source_label.setStyleSheet("color: #888888; margin-top: 2px;")
        time_layout.addWidget(self.time_source_label)
        
        layout.addWidget(time_frame)
        
        # Status indicators (make them more prominent)
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        status_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
                padding: 8px;
            }
        """)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setSpacing(6)  # More spacing
        status_layout.setContentsMargins(6, 6, 6, 6)
        
        status_title = QLabel("System Status")
        status_title.setAlignment(Qt.AlignCenter)
        status_title.setFont(QFont("Arial", 10, QFont.Bold))
        status_title.setStyleSheet("color: #ffffff; margin-bottom: 4px;")
        status_layout.addWidget(status_title)
        
        # Three status indicators in a horizontal layout
        indicators_layout = QHBoxLayout()
        indicators_layout.setSpacing(6)  # More spacing between indicators
        
        # Three status indicators
        self.status1 = StatusIndicator("GPS Lock")
        self.status2 = StatusIndicator("Radio Link")
        self.status3 = StatusIndicator("Source LED")  # Changed to Source LED for LED status
        
        indicators_layout.addWidget(self.status1)
        indicators_layout.addWidget(self.status2)
        indicators_layout.addWidget(self.status3)
        
        status_layout.addLayout(indicators_layout)
        
        layout.addWidget(status_frame)
        
        # Camera control section
        camera_frame = QFrame()
        camera_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        camera_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
                padding: 8px;
            }
        """)
        camera_layout = QVBoxLayout(camera_frame)
        camera_layout.setSpacing(6)
        camera_layout.setContentsMargins(6, 6, 6, 6)
        
        camera_title = QLabel("Camera Control")
        camera_title.setAlignment(Qt.AlignCenter)
        camera_title.setFont(QFont("Arial", 10, QFont.Bold))
        camera_title.setStyleSheet("color: #ffffff; margin-bottom: 4px;")
        camera_layout.addWidget(camera_title)
        
        # Camera status indicator
        camera_info = self.camera_controller.get_camera_info()
        camera_status_text = "AVAILABLE" if camera_info['available'] else "NOT AVAILABLE"
        camera_status_color = "#00ff00" if camera_info['available'] else "#ff0000"
        self.camera_status_label = QLabel(camera_status_text)
        self.camera_status_label.setAlignment(Qt.AlignCenter)
        self.camera_status_label.setFont(QFont("Arial", 8))
        self.camera_status_label.setStyleSheet(f"color: {camera_status_color}; margin-bottom: 6px;")
        camera_layout.addWidget(self.camera_status_label)
        
        # Camera info display
        if camera_info['available']:
            camera_model = camera_info.get('name', 'Unknown Camera')
            camera_info_label = QLabel(f"{camera_model}")
            camera_info_label.setAlignment(Qt.AlignCenter)
            camera_info_label.setFont(QFont("Arial", 7))
            camera_info_label.setStyleSheet("color: #888888; margin-bottom: 6px;")
            camera_layout.addWidget(camera_info_label)
        
        # Camera controls layout
        controls_layout = QGridLayout()
        controls_layout.setSpacing(4)
        
        # Gain control
        gain_label = QLabel("Gain:")
        gain_label.setFont(QFont("Arial", 9))
        gain_label.setStyleSheet("color: #ffffff;")
        controls_layout.addWidget(gain_label, 0, 0)
        
        # Initialize gain and exposure with controller values
        camera_info = self.camera_controller.get_camera_info()
        self.gain_spinbox = QSpinBox()
        self.gain_spinbox.setRange(0, 500)
        self.gain_spinbox.setValue(camera_info.get('gain', 150))
        self.gain_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                padding: 2px;
                min-width: 60px;
            }
        """)
        self.gain_spinbox.valueChanged.connect(self.update_camera_gain)
        controls_layout.addWidget(self.gain_spinbox, 0, 1)
        
        # Exposure control (in milliseconds for user convenience)
        exposure_label = QLabel("Exposure (ms):")
        exposure_label.setFont(QFont("Arial", 9))
        exposure_label.setStyleSheet("color: #ffffff;")
        controls_layout.addWidget(exposure_label, 1, 0)
        
        self.exposure_spinbox = QDoubleSpinBox()
        self.exposure_spinbox.setRange(0.1, 10000.0)  # 0.1ms to 10 seconds
        self.exposure_spinbox.setValue(camera_info.get('exposure_ms', 30.0))  # Default 30ms
        self.exposure_spinbox.setDecimals(1)
        self.exposure_spinbox.setSuffix(" ms")
        self.exposure_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                padding: 2px;
                min-width: 80px;
            }
        """)
        self.exposure_spinbox.valueChanged.connect(self.update_camera_exposure)
        controls_layout.addWidget(self.exposure_spinbox, 1, 1)
        
        camera_layout.addLayout(controls_layout)
        
        # Add manual capture button for testing
        test_capture_button = QPushButton("Test Capture")
        test_capture_button.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        test_capture_button.clicked.connect(self.trigger_camera_capture)
        camera_layout.addWidget(test_capture_button)
        
        layout.addWidget(camera_frame)

        #Add toggle button for telescope slewing mode tracking/predicting
        
        return group
    
    def add_parameter_display(self, layout, label_text, value_attr, default_value, row):
        """Add a parameter display to the layout"""
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 9, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")
        
        value_label = QLabel(default_value)
        value_label.setFont(QFont("Arial", 10, QFont.Bold))
        value_label.setStyleSheet("color: #00ff00;")
        
        # Store reference to value label
        setattr(self, value_attr, value_label)
        
        layout.addWidget(label, row, 0)
        layout.addWidget(value_label, row, 1)
    
    def setup_connections(self):
        """Connect to model signals"""
        self.telemetry_model.acc_updated.connect(self.update_acceleration)
        self.telemetry_model.position_updated.connect(self.update_balloon_position)
        self.telemetry_model.ground_station_gps_updated.connect(self.update_ground_position)
        self.map_controller.user_location_changed.connect(self.update_ground_position_from_controller)
    
    def update_acceleration(self, acc_x, acc_y, acc_z):
        """Update acceleration display"""
        self.acc_x = acc_x# Assuming you have a QLabel for acceleration display
        self.acc_y = acc_y
        self.acc_z = acc_z - 9.81

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
        self.ground_alt = alt
        self.calculate_tracking_parameters()
    
    def update_ground_position_from_controller(self, lat, lon, alt):
        """Update ground station position from map controller"""
        self.ground_lat = lat
        self.ground_lon = lon
        self.ground_alt = alt
        self.calculate_tracking_parameters()
    
    def update_mount_position_display(self):
        """Update the mount position display with current azimuth and altitude"""
        try:
            current_az, current_alt = self.get_mount_position()
            if current_az is not None and current_alt is not None:
                self.current_az_label.setText(f"Az: {current_az:.1f}°")
                self.current_alt_label.setText(f"Alt: {current_alt:.1f}°")
            else:
                self.current_az_label.setText("Az: --°")
                self.current_alt_label.setText("Alt: --°")
        except Exception as e:
            print(f"Error updating mount position display: {e}")
            self.current_az_label.setText("Az: --°")
            self.current_alt_label.setText("Alt: --°")
    
    def calculate_tracking_parameters(self):
        """Calculate bearing, elevation, distance, and celestial coordinates"""
        if self.ground_lat == 0 or self.ground_lon == 0 or self.balloon_lat == 0 or self.balloon_lon == 0:
            return

        # Use tracking calculator for all calculations
        tracking_params = self.tracking_calculator.calculate_tracking_parameters(
            self.ground_lat, self.ground_lon, self.ground_alt,
            self.balloon_lat, self.balloon_lon, self.balloon_alt
        )
        
        if tracking_params['valid']:
            self.bearing = tracking_params['bearing']
            self.distance = tracking_params['distance']
            self.elevation = tracking_params['elevation']
            
            # Update compass
            self.bearing_compass.setBearing(self.bearing)
    
    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate bearing from point 1 to point 2"""
        return self.tracking_calculator.calculate_bearing(lat1, lon1, lat2, lon2)
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula"""
        return self.tracking_calculator.calculate_distance(lat1, lon1, lat2, lon2)
    
    def calculate_parameters_for(self, lat, lon, alt):
        """Calculate bearing, elevation and distance for given coordinates."""
        return self.tracking_calculator.calculate_parameters_for_position(
            self.ground_lat, self.ground_lon, self.ground_alt,
            lat, lon, alt
        )
    
    def calculate_target_coordinates(self, bearing=None, elevation=None):
        """Calculate target azimuth and altitude for mount tracking"""
        if bearing is None:
            bearing = self.bearing
        if elevation is None:
            elevation = self.elevation
        
        # Check if we have valid tracking data
        if (self.balloon_lat == 0 and self.balloon_lon == 0) or (self.ground_lat == 0 and self.ground_lon == 0):
            print("Target coordinates - No valid GPS data available")
            return None, None  # Return None when no valid data
            
        # Use tracking calculator to convert bearing/elevation to mount coordinates
        azimuth, altitude = self.tracking_calculator.calculate_mount_coordinates(bearing, elevation)
        
        print(f"Target coordinates - Azimuth: {azimuth:.2f}°, Altitude: {altitude:.2f}°")
        
        return azimuth, altitude
    

    def update_displays(self):
        """Update all display elements"""
        # Update bearing display
        self.bearing_label.setText(f"{self.bearing:.1f}°")

        # Update tracking parameters
        self.altitude_label.setText(f"{self.balloon_alt:.1f} m")
        self.elevation_label.setText(f"{self.elevation:.1f}°")
        self.distance_label.setText(f"{self.distance:.2f} km")

        # Calculate target azimuth/altitude for mount
        if self.tracking_enabled:
            target_az, target_alt = self.calculate_target_coordinates()
            if target_az is None or target_alt is None:
                target_az, target_alt = 0.0, 0.0  # Default for display only
        else:
            # Use predicted coordinates
            pb, pe, _ = self.calculate_parameters_for(self.pred_lat, self.pred_lon, self.pred_alt)
            target_az, target_alt = self.calculate_target_coordinates(pb, pe)
            if target_az is None or target_alt is None:
                target_az, target_alt = 0.0, 0.0  # Default for display only
            self.pred_bearing_label.setText(f"{pb:.1f}°")  

        # Update coordinate displays (using azimuth/altitude instead of RA/DEC)
        self.ra_label.setText(f"{target_az:.2f}°")  # Reuse RA label for azimuth
        # Update coordinate displays (using azimuth/altitude instead of RA/DEC)
        self.ra_label.setText(f"Az: {target_az:.2f}°")  # Reuse RA label for azimuth
        self.dec_label.setText(f"Alt: {target_alt:.2f}°")  # Reuse DEC label for altitude
        
        # Update mount status information
        current_az, current_alt = self.get_mount_position()
        if current_az is not None and current_alt is not None:
            mount_status = f"Mount: Az {current_az:.1f}°, Alt {current_alt:.1f}°"
            
            # Check if mount has reached its target position
            if (self.last_sent_azimuth is not None and self.last_sent_altitude is not None):
                az_error = abs(current_az - self.last_sent_azimuth)
                alt_error = abs(current_alt - self.last_sent_altitude)
                
                # Handle azimuth wraparound
                if az_error > 180:
                    az_error = 360 - az_error
                    
                if az_error <= self.mount_settled_tolerance and alt_error <= self.mount_settled_tolerance:
                    if not self.mount_at_target:
                        print(f"Mount reached target position within tolerance (Az±{az_error:.2f}°, Alt±{alt_error:.2f}°)")
                        self.mount_at_target = True
                else:
                    self.mount_at_target = False
            
            if self.mount_at_target:
                mount_status = "At Target"
            elif self.is_mount_moving():
                mount_status = "Moving"
            else:
                mount_status = "Stationary"
            
            # Update the mount status label with detailed information
            self.mount_status_label.setText(mount_status)
            
            # Set color based on status
            if self.mount_at_target:
                self.mount_status_label.setStyleSheet("color: #00ff00; margin: 2px;")  # Green for at target
            elif self.is_mount_moving():
                self.mount_status_label.setStyleSheet("color: #ffaa00; margin: 2px;")  # Orange for moving
            else:
                self.mount_status_label.setStyleSheet("color: #00aaff; margin: 2px;")  # Blue for stationary
            
        else:
            mount_status = "Mount: Position Unknown"
            self.mount_status_label.setText(mount_status)
            self.mount_status_label.setStyleSheet("color: #888888; margin: 2px;")  # Gray for unknown
        
        # Update manual mount control display
        if hasattr(self, 'current_az_label') and hasattr(self, 'current_alt_label'):
            self.update_mount_position_display()

        # Log tracking data
        self.log_tracking_data()

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

        # Move mount to target position (throttled to every 15 seconds) - only in auto tracking mode
        # Only move if we have valid tracking data (non-zero coordinates)
        if (not self.manual_control_mode and 
            time.time() - self.last_pred_slew_time >= 15 and
            self.balloon_lat != 0 and self.balloon_lon != 0 and 
            self.ground_lat != 0 and self.ground_lon != 0 and
            target_az is not None and target_alt is not None):
            print(f"DEBUG: Moving mount to target position - Az: {target_az}, Alt: {target_alt}")
            self.safe_slew_azalt(target_az, target_alt)
            self.last_pred_slew_time = time.time()
        elif not self.manual_control_mode and (self.balloon_lat == 0 or self.balloon_lon == 0 or self.ground_lat == 0 or self.ground_lon == 0):
            print("DEBUG: Skipping mount movement - waiting for valid GPS coordinates")
        elif not self.manual_control_mode and (target_az is None or target_alt is None):
            print("DEBUG: Skipping mount movement - invalid target coordinates")

    def update_status_indicators(self):
        """Update status indicators based on system state"""
        print("DEBUG: Updating status indicators...")
        
        # GPS Lock status
        if hasattr(self.telemetry_model, 'gps_valid') and self.telemetry_model.gps_valid:
            print("DEBUG: GPS valid - setting OK")
            self.status1.set_status("OK")
        else:
            print("DEBUG: GPS invalid - setting ERROR")
            self.status1.set_status("ERROR")
        
        # Radio Link status (based on recent telemetry)
        if hasattr(self.telemetry_model, 'rssi') and self.telemetry_model.rssi > -100:
            if self.telemetry_model.rssi > -80:
                print(f"DEBUG: RSSI good ({self.telemetry_model.rssi}) - setting OK")
                self.status2.set_status("OK")
            else:
                print(f"DEBUG: RSSI weak ({self.telemetry_model.rssi}) - setting WARNING")
                self.status2.set_status("WARNING")
        else:
            print("DEBUG: No RSSI or too low - setting ERROR")
            self.status2.set_status("ERROR")
        
        # Don't update status3 here - it's used for LED status
        # LED status is updated by update_led_status() method
        print("DEBUG: Status3 (LED) handled separately")
    
    def get_current_utc_time(self):
        """Get current UTC-4 time, preferring GPS time if available"""
        tz = QTimeZone(b"-04:00")  # UTC-4 fixed offset

        if hasattr(self.telemetry_model, 'gs_gps_utc_unix') and self.telemetry_model.gs_gps_utc_unix > 0:
            # Convert GPS UTC time to UTC-4
            dt = QDateTime.fromSecsSinceEpoch(int(self.telemetry_model.gs_gps_utc_unix))
        else:
            # Convert system UTC time to UTC-4
            dt = QDateTime.currentDateTimeUtc()

        dt.setTimeZone(tz)
        return dt
    
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
            if (seconds_in_minute // 10) % 2 == 0:
                if (self.last_exposure_check == -1 or current_second > (self.last_exposure_check + (self.camera_controller.exposure // 1e6))) and seconds_in_minute != self.last_exposure_check:
                    print(f"EXPOSURE START {current_second}")
                    self.trigger_camera_capture()
                    # Trigger camera capture
                    self.last_exposure_check = seconds_in_minute

            else:
                self.last_exposure_check = -1

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
    
    def create_manual_mount_control_section(self):
        """Create manual mount control section with azimuth/altitude input and reset button"""
        group = QGroupBox("Manual Mount Control")
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 1ex;
                font-weight: bold;
                color: #ffaa00;
                font-size: 12px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        layout = QHBoxLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 15, 10, 10)
        
        # Current position display
        current_frame = QFrame()
        current_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        current_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
                padding: 5px;
            }
        """)
        current_layout = QVBoxLayout(current_frame)
        current_layout.setSpacing(5)
        
        current_title = QLabel("Current Position")
        current_title.setFont(QFont("Arial", 9, QFont.Bold))
        current_title.setStyleSheet("color: #ffffff; margin-bottom: 5px;")
        current_title.setAlignment(Qt.AlignCenter)
        current_layout.addWidget(current_title)
        
        self.current_az_label = QLabel("Az: --°")
        self.current_az_label.setFont(QFont("Arial", 8))
        self.current_az_label.setStyleSheet("color: #00ff00; margin: 2px;")
        current_layout.addWidget(self.current_az_label)
        
        self.current_alt_label = QLabel("Alt: --°")
        self.current_alt_label.setFont(QFont("Arial", 8))
        self.current_alt_label.setStyleSheet("color: #00ff00; margin: 2px;")
        current_layout.addWidget(self.current_alt_label)
        
        self.mount_status_label = QLabel("Disconnected")
        self.mount_status_label.setFont(QFont("Arial", 8))
        self.mount_status_label.setStyleSheet("color: #888888; margin: 2px;")
        current_layout.addWidget(self.mount_status_label)
        
        # Mode toggle button
        self.mode_toggle_button = QPushButton("Auto Tracking")
        self.mode_toggle_button.setCheckable(True)
        self.mode_toggle_button.setChecked(False)  # Start in auto tracking mode
        self.mode_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #4a6a4a;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 8px;
                margin-top: 5px;
            }
            QPushButton:checked {
                background-color: #aa6644;
                color: #ffffff;
            }
            QPushButton:hover {
                border: 1px solid #ffaa00;
            }
            QPushButton:pressed {
                background-color: #3a5a3a;
            }
        """)
        current_layout.addWidget(self.mode_toggle_button)
        
        layout.addWidget(current_frame)
        
        # Manual control inputs
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        control_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
                padding: 5px;
            }
        """)
        control_layout = QGridLayout(control_frame)
        control_layout.setSpacing(8)
        
        control_title = QLabel("Set Position")
        control_title.setFont(QFont("Arial", 9, QFont.Bold))
        control_title.setStyleSheet("color: #ffffff; margin-bottom: 5px;")
        control_title.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(control_title, 0, 0, 1, 2)
        
        # Azimuth input
        az_label = QLabel("Azimuth (°):")
        az_label.setFont(QFont("Arial", 8))
        az_label.setStyleSheet("color: #ffffff;")
        control_layout.addWidget(az_label, 1, 0)
        
        self.manual_az_spin = QDoubleSpinBox()
        self.manual_az_spin.setRange(0.0, 360.0)
        self.manual_az_spin.setDecimals(2)
        self.manual_az_spin.setSingleStep(1.0)
        self.manual_az_spin.setValue(0.0)
        self.manual_az_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                min-width: 80px;
                padding: 2px;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #ffaa00;
            }
        """)
        control_layout.addWidget(self.manual_az_spin, 1, 1)
        
        # Altitude input
        alt_label = QLabel("Altitude (°):")
        alt_label.setFont(QFont("Arial", 8))
        alt_label.setStyleSheet("color: #ffffff;")
        control_layout.addWidget(alt_label, 2, 0)
        
        self.manual_alt_spin = QDoubleSpinBox()
        self.manual_alt_spin.setRange(-90.0, 90.0)
        self.manual_alt_spin.setDecimals(2)
        self.manual_alt_spin.setSingleStep(1.0)
        self.manual_alt_spin.setValue(0.0)
        self.manual_alt_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                min-width: 80px;
                padding: 2px;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #ffaa00;
            }
        """)
        control_layout.addWidget(self.manual_alt_spin, 2, 1)
        
        # Precision mode checkbox
        self.precision_checkbox = QPushButton("Fast Mode")
        self.precision_checkbox.setCheckable(True)
        self.precision_checkbox.setChecked(False)  # Default to fast mode
        self.precision_checkbox.clicked.connect(self.update_precision_mode_text)
        self.precision_checkbox.setStyleSheet("""
            QPushButton {
                background-color: #4a4a6a;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 8px;
                margin-top: 3px;
            }
            QPushButton:checked {
                background-color: #6a6a4a;
                color: #ffffff;
            }
            QPushButton:hover {
                border: 1px solid #ffaa00;
            }
        """)
        self.precision_checkbox.clicked.connect(self.update_precision_mode_text)
        control_layout.addWidget(self.precision_checkbox, 3, 0, 1, 2)
        
        # Set initial text
        self.update_precision_mode_text()
        
        layout.addWidget(control_frame)
        
        # Control buttons
        button_frame = QFrame()
        button_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        button_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
                padding: 5px;
            }
        """)
        button_layout = QVBoxLayout(button_frame)
        button_layout.setSpacing(8)
        
        button_title = QLabel("Actions")
        button_title.setFont(QFont("Arial", 9, QFont.Bold))
        button_title.setStyleSheet("color: #ffffff; margin-bottom: 5px;")
        button_title.setAlignment(Qt.AlignCenter)
        button_layout.addWidget(button_title)
        
        # Go To button
        self.goto_button = QPushButton("Go To Position")
        self.goto_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 1px solid #ffaa00;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
                border: 1px solid #444444;
            }
        """)
        button_layout.addWidget(self.goto_button)
        
        # Reset button
        self.reset_button = QPushButton("Reset (0°, 0°)")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #aa4444;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #bb5555;
                border: 1px solid #ffaa00;
            }
            QPushButton:pressed {
                background-color: #993333;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
                border: 1px solid #444444;
            }
        """)
        button_layout.addWidget(self.reset_button)
        
        # Get Current Position button
        self.get_position_button = QPushButton("Update Position")
        self.get_position_button.setStyleSheet("""
            QPushButton {
                background-color: #4a6a4a;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #5a7a5a;
                border: 1px solid #ffaa00;
            }
            QPushButton:pressed {
                background-color: #3a5a3a;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
                border: 1px solid #444444;
            }
        """)
        button_layout.addWidget(self.get_position_button)
        
        # Reconnect Mount button
        self.reconnect_mount_button = QPushButton("Reconnect Mount")
        self.reconnect_mount_button.setStyleSheet("""
            QPushButton {
                background-color: #6a4a6a;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #7a5a7a;
                border: 1px solid #ffaa00;
            }
            QPushButton:pressed {
                background-color: #5a3a5a;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
                border: 1px solid #444444;
            }
        """)
        button_layout.addWidget(self.reconnect_mount_button)
        
        layout.addWidget(button_frame)
        
        # Connect button signals
        self.goto_button.clicked.connect(self.manual_goto_position)
        self.reset_button.clicked.connect(self.reset_mount_position)
        self.get_position_button.clicked.connect(self.update_mount_position_display)
        self.mode_toggle_button.clicked.connect(self.toggle_control_mode)
        self.reconnect_mount_button.clicked.connect(self.reconnect_mount_with_feedback)
        
        return group
    
    def create_led_timing_plot(self):
        """Create LED timing plot showing red and green LED patterns"""
        group = QGroupBox("LED Timing Pattern")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 1ex;
                color: #00ff00;
                padding: 6px;
                font-size: 12px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        
        # Create matplotlib figure and canvas
        self.led_figure = Figure(figsize=(12, 2.5), facecolor='#2a2a2a')
        self.led_canvas = FigureCanvas(self.led_figure)
        self.led_canvas.setStyleSheet("background-color: #2a2a2a;")
        self.led_canvas.setMaximumHeight(200)  # Limit height
        
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
        self.led_ax.set_xlabel('UTC Time', color='white', fontsize=9)
        self.led_ax.set_ylabel('LED State', color='white', fontsize=9)
        self.led_ax.tick_params(colors='white', labelsize=8)
        self.led_ax.grid(True, alpha=0.3, color='white')
        self.led_ax.legend(facecolor='#2a2a2a', edgecolor='white', labelcolor='white', fontsize=8)
        
        # Set LED state labels
        self.led_ax.set_yticks([0, 1, 2])
        self.led_ax.set_yticklabels(['OFF', 'Red ON', 'Green ON'], color='white', fontsize=8)
        
        # Style the plot
        self.led_figure.patch.set_facecolor('#2a2a2a')
        self.led_ax.spines['bottom'].set_color('white')
        self.led_ax.spines['top'].set_color('white')
        self.led_ax.spines['right'].set_color('white')
        self.led_ax.spines['left'].set_color('white')
        
        # Tight layout to reduce margins
        self.led_figure.tight_layout(pad=1.0)
        
        layout.addWidget(self.led_canvas)
        
        return group

    def update_led_timing_plot(self):
        """Update LED timing plot with current patterns"""
        current_time = self.get_current_utc_time()
        
        # Compute the start time of the window (subtract seconds)
        start_time = current_time.addSecs(-self.time_window)

        # Convert QDateTime to float seconds since epoch for plotting
        start_epoch = start_time.toSecsSinceEpoch()
        end_epoch = current_time.toSecsSinceEpoch()

        time_points = np.linspace(start_epoch, end_epoch, self.time_window * 10)
            
        # Calculate LED states for each time point
        red_states = []
        green_states = []
        
        for t in time_points:
            # Convert to UTC time for this point
            abs_utc = QDateTime.fromSecsSinceEpoch(int(t))
            # abs_utc.setTimeSpec(Qt.UTC)
            global abs_minute, abs_second
            abs_minute = abs_utc.time().minute()
            abs_second = abs_utc.time().second()
            
            # RED LED pattern: even minutes, ON for 10s, OFF for 10s
            if abs_minute % 2 == 0:  # Even minute
                # 10 seconds on, 10 seconds off pattern
                cycle_pos = abs_second % 20
                global red_state
                red_state = 1 if cycle_pos < 10 else 0
            else:
                red_state = 0
            
            # GREEN LED pattern: odd minutes, ON for 1s, OFF for 1s
            if abs_minute % 2 == 1:  # Odd minute
                # 1 second on, 1 second off pattern
                cycle_pos = abs_second % 2
                green_state = 2 if (cycle_pos < 1 and abs_second < 50) else 0
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
        current_utc =  current_time.toSecsSinceEpoch()
        start_utc = start_time.toSecsSinceEpoch()
        
        # Set custom x-axis labels
        x_ticks = np.linspace(0, self.time_window, 5)
        x_labels = []
        for tick in x_ticks:
            tick_time = current_time.addSecs(int(-self.time_window + tick))
            tick_time.setTimeSpec(Qt.UTC)
            x_labels.append(tick_time.toString("hh:mm:ss"))
        
        self.led_ax.set_xticks(x_ticks)
        self.led_ax.set_xticklabels(x_labels, rotation=45, fontsize=8)
        
        # Refresh canvas
        self.led_canvas.draw()

    def trigger_camera_capture(self):
        """Trigger camera capture and save image with unique filename asynchronously"""
        def capture_callback(success, filename):
            """Callback for when capture completes"""
            # UI updates must run on the main thread
            QTimer.singleShot(0, lambda: self.update_camera_status(success=success))
        
        try:
            if self.camera_controller.is_available():
                filename = self.camera_controller.generate_filename("balloon_tracking")
                print(f"Triggering camera capture: {filename}")
                
                # Get current camera info for logging
                camera_info = self.camera_controller.get_camera_info()
                print(f"Camera settings - Gain: {camera_info.get('gain', 'N/A')}, "
                      f"Exposure: {camera_info.get('exposure_ms', 'N/A')} ms")
                
                # Start async capture
                self.camera_controller.capture_rgb_image_async(filename, capture_callback)
            else:
                print("Camera not available or not initialized")
                self.update_camera_status(success=False)
                
        except Exception as e:
            print(f"Error during camera capture: {e}")
            self.update_camera_status(success=False)

        
    def reset_camera_status(self):
        """Reset camera status display to default"""
        if hasattr(self, 'camera_status_label'):
            camera_info = self.camera_controller.get_camera_info()
            camera_status_text = "AVAILABLE" if camera_info['available'] else "NOT AVAILABLE"
            camera_status_color = "#00ff00" if camera_info['available'] else "#ff0000"
            self.camera_status_label.setText(camera_status_text)
            self.camera_status_label.setStyleSheet(f"color: {camera_status_color}; margin-bottom: 6px;")
    
    def update_camera_status(self, success=True):
        """Update camera status display after capture"""
        if hasattr(self, 'camera_status_label'):
            if success:
                self.camera_status_label.setText("CAPTURE OK")
                self.camera_status_label.setStyleSheet("color: #00ff00; margin-bottom: 6px;")
                # Reset after 3 seconds
                QTimer.singleShot(3000, self.reset_camera_status)
            else:
                self.camera_status_label.setText("CAPTURE FAILED")
                self.camera_status_label.setStyleSheet("color: #ff0000; margin-bottom: 6px;")
                # Reset after 5 seconds
                QTimer.singleShot(5000, self.reset_camera_status)
    
    def safe_slew_azalt(self, azimuth, altitude):
        """Safely slew mount to azimuth/altitude position with smart positioning"""
        # Check if we should send this position
        if not self.should_send_new_position(azimuth, altitude):
            return  # Don't send if position hasn't changed significantly or mount is at target
        
        if self.slew_in_progress:
            print("Slew already in progress, skipping new position")
            return  # Don't start a new slew if one is in progress
            
        self.slew_in_progress = True

        def threaded_slew():
            try:
                success = self.move_to_azalt_position(azimuth, altitude)
                if success:
                    print(f"Mount slewing to Az={azimuth:.2f}°, Alt={altitude:.2f}°")
                    self.update_last_sent_position(azimuth, altitude)
                else:
                    print("Mount slew failed")
            except Exception as e:
                print(f"Error during mount slew: {e}")
            finally:
                self.slew_in_progress = False  # Mark slew as done

        threading.Thread(target=threaded_slew, daemon=True).start()

    def set_tracking_enabled(self, enabled:bool):
        self.tracking_enabled = bool(enabled)
    
    def prediction_loop(self):
        while True:
            time.sleep(5)
            if self.balloon_lat != 0 and self.balloon_lon != 0:
                self.ekf.update(
                    self.balloon_lat, 
                    self.balloon_lon,
                    self.balloon_alt
                )
                self.pred_lat, self.pred_lon, self.pred_alt = self.ekf.get_state()
    
    def manual_goto_position(self):
        """Handle manual goto position button click"""
        if not self.mount_connected:
            QMessageBox.warning(self, "Mount Error", "Mount not connected!")
            return
        
        azimuth = self.manual_az_spin.value()
        altitude = self.manual_alt_spin.value()
        
        # Validate ranges
        if not (0.0 <= azimuth <= 360.0):
            QMessageBox.warning(self, "Invalid Input", "Azimuth must be between 0° and 360°")
            return
        
        if not (-90.0 <= altitude <= 90.0):
            QMessageBox.warning(self, "Invalid Input", "Altitude must be between -90° and 90°")
            return
        
        # Disable buttons during operation
        self.goto_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        
        try:
            print(f"Manual command: Moving mount to Az={azimuth:.2f}°, Alt={altitude:.2f}°")
            
            # Use the retry method (now asynchronous)
            success = self.safe_slew_azalt_with_retry(azimuth, altitude)
            
            if success:
                print(f"✓ Manual command initiated")
                # Show immediate feedback
                self.mount_status_label.setText("Moving...")
                self.mount_status_label.setStyleSheet("color: #ffaa00; margin: 2px;")
            else:
                QMessageBox.warning(self, "Mount Error", "Failed to initiate mount movement.")
                
        except Exception as e:
            print(f"Error in manual goto: {e}")
            QMessageBox.critical(self, "Mount Error", f"Error moving mount: {str(e)}")
        finally:
            # Re-enable buttons after short delay
            QTimer.singleShot(2000, lambda: self.goto_button.setEnabled(True))
            QTimer.singleShot(2000, lambda: self.reset_button.setEnabled(True))
            
        # Update display after a short delay to allow mount to start moving
        QTimer.singleShot(500, self.update_mount_position_display)
    
    def reconnect_mount_with_feedback(self):
        """Reconnect to mount with user feedback"""
        try:
            current_port = self.mount_controller.get_current_port()
            print(f"Reconnecting to mount on {current_port}...")
            
            # Disable button during reconnection
            self.reconnect_mount_button.setEnabled(False)
            self.reconnect_mount_button.setText("Connecting...")
            
            # Reconnect
            success = self.reconnect_mount()
            
            if success:
                QMessageBox.information(self, "Mount Connection", f"Successfully connected to mount on {current_port}")
                print(f"✓ Mount reconnected successfully on {current_port}")
            else:
                QMessageBox.warning(self, "Mount Connection", f"Failed to connect to mount on {current_port}. Check port and mount power.")
                print(f"✗ Mount reconnection failed on {current_port}")
                
        except Exception as e:
            QMessageBox.critical(self, "Mount Error", f"Error during reconnection: {str(e)}")
            print(f"Error during mount reconnection: {e}")
        finally:
            # Re-enable button
            self.reconnect_mount_button.setEnabled(True)
            self.reconnect_mount_button.setText("Reconnect Mount")
            self.update_manual_control_states()
            
            # Update position display
            QTimer.singleShot(500, self.update_mount_position_display)
    
    def safe_slew_azalt_with_retry(self, azimuth, altitude, max_retries=2):
        """Safe slewing with retry logic for manual commands (asynchronous)"""
        def async_slew():
            for attempt in range(max_retries + 1):
                try:
                    print(f"Attempt {attempt + 1}/{max_retries + 1}: Moving mount to Az={azimuth:.2f}°, Alt={altitude:.2f}°")
                    
                    # Use precision or fast movement based on user setting
                    if hasattr(self, 'precision_checkbox') and self.precision_checkbox.isChecked():
                        print("Using precision movement mode")
                        success = self.move_to_azalt_position_precise(azimuth, altitude)
                    else:
                        print("Using fast movement mode")
                        success = self.move_to_azalt_position(azimuth, altitude)
                        
                    if success:
                        self.update_last_sent_position(azimuth, altitude)
                        print(f"✓ Manual command successful")
                        return True
                    else:
                        print(f"Attempt {attempt + 1} failed")
                        if attempt < max_retries:
                            print("Waiting 2 seconds before retry...")
                            time.sleep(2)
                            
                except Exception as e:
                    print(f"Attempt {attempt + 1} error: {e}")
                    if attempt < max_retries:
                        print("Waiting 2 seconds before retry...")
                        time.sleep(2)
                    else:
                        print(f"All attempts failed: {e}")
            
            print("All manual command attempts failed")
            return False
        
        # Run asynchronously to prevent UI freezing
        threading.Thread(target=async_slew, daemon=True).start()
        return True  # Return immediately since we're async
    
    def reset_mount_position(self):
        """Reset mount to home position (0°, 0°)"""
        if not self.mount_connected:
            QMessageBox.warning(self, "Mount Error", "Mount not connected!")
            return
        
        reply = QMessageBox.question(self, "Reset Mount", 
                                   "Reset mount to home position (Az=0°, Alt=0°)?",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Disable buttons during operation
            self.goto_button.setEnabled(False)
            self.reset_button.setEnabled(False)
            
            try:
                # Set spin boxes to home position
                self.manual_az_spin.setValue(0.0)
                self.manual_alt_spin.setValue(0.0)
                
                print("Manual command: Resetting mount to home position (0°, 0°)")
                
                # Use the retry method (now asynchronous)
                success = self.safe_slew_azalt_with_retry(0.0, 0.0)
                
                if success:
                    print("✓ Reset command initiated")
                    # Show immediate feedback
                    self.mount_status_label.setText("Resetting...")
                    self.mount_status_label.setStyleSheet("color: #ffaa00; margin: 2px;")
                else:
                    QMessageBox.warning(self, "Mount Error", "Failed to initiate mount reset.")
                    
            except Exception as e:
                print(f"Error in reset: {e}")
                QMessageBox.critical(self, "Mount Error", f"Error resetting mount: {str(e)}")
            finally:
                # Re-enable buttons after short delay
                QTimer.singleShot(2000, lambda: self.goto_button.setEnabled(True))
                QTimer.singleShot(2000, lambda: self.reset_button.setEnabled(True))
            
            # Update display after a short delay
            QTimer.singleShot(500, self.update_mount_position_display)
    
    def update_precision_mode_text(self):
        """Update the precision mode button text based on current state"""
        if hasattr(self, 'precision_checkbox'):
            if self.precision_checkbox.isChecked():
                self.precision_checkbox.setText("Precision Mode ✓")
                self.precision_checkbox.setStyleSheet("""
                    QPushButton {
                        background-color: #4a6a4a;
                        color: #ffffff;
                        border: 1px solid #666666;
                        border-radius: 3px;
                        padding: 3px 6px;
                        font-size: 8px;
                        margin-top: 3px;
                    }
                    QPushButton:hover {
                        border: 1px solid #ffaa00;
                        background-color: #5a7a5a;
                    }
                """)
            else:
                self.precision_checkbox.setText("Fast Mode ⚡")
                self.precision_checkbox.setStyleSheet("""
                    QPushButton {
                        background-color: #6a4a4a;
                        color: #ffffff;
                        border: 1px solid #666666;
                        border-radius: 3px;
                        padding: 3px 6px;
                        font-size: 8px;
                        margin-top: 3px;
                    }
                    QPushButton:hover {
                        border: 1px solid #ffaa00;
                        background-color: #7a5a5a;
                    }
                """)
    
    def toggle_control_mode(self):
        """Toggle between manual and automatic tracking mode"""
        self.manual_control_mode = self.mode_toggle_button.isChecked()
        
        if self.manual_control_mode:
            self.mode_toggle_button.setText("Manual Control")
            print("Switched to MANUAL control mode - balloon tracking disabled")
        else:
            self.mode_toggle_button.setText("Auto Tracking")
            print("Switched to AUTO TRACKING mode - balloon tracking enabled")
        
        # Update button states
        self.update_manual_control_states()
