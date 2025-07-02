from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QGroupBox, QSizePolicy, QSpacerItem, QSpinBox, QDoubleSpinBox, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QColor, QPalette
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import os
import sys

from views.widgets.compass_widget import CompassWidget

# Import ZWO camera functionality
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'ZWO_Trigger'))
    import zwoasi
    # from Trigger import RAW16_photo, RGB_photo
    # Import camera initialization from Camera_Trigger but don't execute the script
    import importlib.util
    spec = importlib.util.spec_from_file_location("camera_init", 
                                                os.path.join(os.path.dirname(__file__), 'ZWO_Trigger', 'Camera_Trigger.py'))
    camera_init_module = importlib.util.module_from_spec(spec)
    
    # Initialize camera properly following Camera_Trigger.py pattern
    dll_path = os.path.join(os.path.dirname(__file__), 'ZWO_Trigger', 'ZWO_ASI_LIB', 'lib', 'x64', 'ASICamera2.dll')
    print(f"Attempting to load DLL from: {dll_path}")
    
    # Check if DLL exists
    if not os.path.exists(dll_path):
        print(f"❌ DLL not found at: {dll_path}")
        # List directory contents for debugging
        dll_dir = os.path.dirname(dll_path)
        if os.path.exists(dll_dir):
            print(f"Contents of {dll_dir}: {os.listdir(dll_dir)}")
        else:
            print(f"Directory {dll_dir} does not exist")
        raise ImportError(f"Camera DLL not found at {dll_path}")
    
    try:
        # Check if SDK is already initialized by trying to get camera count
        try:
            num_cameras = zwoasi.get_num_cameras()
            print(f"SDK already initialized, found {num_cameras} cameras")
        except:
            # SDK not initialized yet, initialize it
            print(f"Initializing SDK with DLL: {dll_path}")
            zwoasi.init(dll_path)
            print("✅ ASICamera2.dll loaded successfully in GUI")
    except Exception as e:
        print(f"❌ Failed to load SDK in GUI: {e}")
        raise ImportError("Camera SDK not available")
    
    # Check for cameras
    num_cameras = zwoasi.get_num_cameras()
    if num_cameras == 0:
        print('No cameras found')
        raise ImportError("No cameras detected")
    
    cameras_found = zwoasi.list_cameras()
    camera_id = 0  # Use first camera
    print(f'GUI: Using camera #{camera_id}: {cameras_found[camera_id]}')
    
    # Initialize camera object
    camera = zwoasi.Camera(camera_id)
    camera_info = camera.get_camera_property()
    controls = camera.get_controls()
    
    # Add save_control_values function here since it's used by RGB_photo
    def save_control_values(filename, settings):
        try:
            settings_filename = filename + '.txt'
            with open(settings_filename, 'w') as f:
                for k in sorted(settings.keys()):
                    f.write('%s: %s\n' % (k, str(settings[k])))
            print('Camera settings saved to %s' % settings_filename)
        except Exception as e:
            print(f'Error saving camera settings: {e}')
    
    # Set optimal settings following Camera_Trigger.py
    camera.set_control_value(zwoasi.ASI_BANDWIDTHOVERLOAD, camera.get_controls()['BandWidth']['MinValue'])
    camera.disable_dark_subtract()
    
    # Set default control values
    camera.set_control_value(zwoasi.ASI_GAIN, 150)
    camera.set_control_value(zwoasi.ASI_EXPOSURE, 30000)
    camera.set_control_value(zwoasi.ASI_WB_B, 99)
    camera.set_control_value(zwoasi.ASI_WB_R, 75)
    camera.set_control_value(zwoasi.ASI_GAMMA, 50)
    camera.set_control_value(zwoasi.ASI_BRIGHTNESS, 50)
    camera.set_control_value(zwoasi.ASI_FLIP, 0)
    
    # # Enable stills mode
    # try:
    #     camera.stop_video_capture()
    #     camera.stop_exposure()
    # except:
    #     pass  # Ignore errors if already stopped
    
    CAMERA_AVAILABLE = True
    print("ZWO Camera module imported and initialized successfully")
    
    def RGB_photo(filename, gain, exposure):
        camera.set_image_type(zwoasi.ASI_IMG_RGB24)
        camera.capture(filename=filename)
        save_control_values(filename, camera.get_control_values())
        print(f"Captured RGB: {filename} with gain={gain}, exposure={exposure}")



except ImportError as e:
    print(f"ZWO Camera module not available: {e}")
    CAMERA_AVAILABLE = False
    camera = None
    camera_info = None
    controls = None
    
    # Create dummy functions for when camera is not available
    # def RAW16_photo(filename, gain, exposure):
        # print(f"CAMERA NOT AVAILABLE - Would capture RAW16: {filename} with gain={gain}, exposure={exposure}")
    # def save_control_values(filename, settings):
    #     try:
    #         settings_filename = filename + '.txt'
    #         with open(settings_filename, 'w') as f:
    #             for k in sorted(settings.keys()):
    #                 f.write('%s: %s\n' % (k, str(settings[k])))
    #         print('Camera settings saved to %s' % settings_filename)
    #     except Exception as e:
    #         print(f'Error saving camera settings: {e}')
            
    # def RGB_photo(filename, gain, exposure):
    #     # camera.set_image_type(zwoasi.ASI_IMG_RGB24)
    #     # camera.capture(filename=filename)
    #     save_control_values(filename, camera.get_control_values())
    #     print(f"Captured RGB: {filename} with gain={gain}, exposure={exposure}")

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
        
        # Tracking data
        self.balloon_lat = 0.0
        self.balloon_lon = 0.0
        self.balloon_alt = 0.0
        self.ground_lat = 0.0
        self.ground_lon = 0.0
        self.bearing = 0.0
        self.elevation = 0.0
        self.distance = 0.0
        
        # Variables for tracking LED status and exposure timing
        self.last_minute = -1  # Track minute changes
        self.last_exposure_check = -1  # Track exposure timing
        
        # Camera settings (initialize before UI setup)
        self.camera_gain = 150  # Default gain
        self.camera_exposure = 30000  # Default exposure in microseconds
        self.image_counter = 0  # Counter for unique filenames
        
        
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
    
    def setup_ui(self):
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
        
        # Add LED timing plot
        led_plot_section = self.create_led_timing_plot()
        main_layout.addWidget(led_plot_section)
        
        # No stretch - let components fill available space
    
    def create_tracking_section(self):
        """Create the tracking information section"""
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
        
        layout.addWidget(params_frame, 0, 1)
        
        return group
    
    def update_camera_gain(self, value):
        """Update camera gain setting"""
        self.camera_gain = value
        print(f"Camera gain updated to: {value}")
        # Update camera if available
        if CAMERA_AVAILABLE and camera:
            try:
                camera.set_control_value(zwoasi.ASI_GAIN, value)
                print(f"Camera gain applied: {value}")
            except Exception as e:
                print(f"Error setting camera gain: {e}")
    
    def update_camera_exposure(self, value):
        """Update camera exposure setting (value in milliseconds)"""
        self.camera_exposure = int(value * 1000)  # Convert milliseconds to microseconds
        print(f"Camera exposure updated to: {value} ms ({self.camera_exposure} μs)")
        # Update camera if available
        if CAMERA_AVAILABLE and camera:
            try:
                camera.set_control_value(zwoasi.ASI_EXPOSURE, self.camera_exposure)
                print(f"Camera exposure applied: {self.camera_exposure}μs")
            except Exception as e:
                print(f"Error setting camera exposure: {e}")
    
    def initialize_camera_for_capture(self):
        """Initialize camera for capture following Camera_Trigger.py pattern"""
        if not CAMERA_AVAILABLE or not camera:
            return False
            
        try:
            # Ensure stills mode is enabled
            camera.stop_video_capture()
            camera.stop_exposure()
            
            # Apply current settings
            camera.set_control_value(zwoasi.ASI_GAIN, self.camera_gain)
            camera.set_control_value(zwoasi.ASI_EXPOSURE, self.camera_exposure)
            
            # Set image type for RGB capture
            camera.set_image_type(zwoasi.ASI_IMG_RGB24)
            
            print("Camera initialized for capture")
            return True
            
        except Exception as e:
            print(f"Error initializing camera for capture: {e}")
            return False
    
    def generate_filename(self):
        """Generate a unique filename for camera capture"""
        # current_time = QDateTime.currentDateTimeUtc()
        current_time = gps_utc_time
        timestamp = current_time.toString("yyyyMMdd_hhmmss")
        self.image_counter += 1
        # Use .jpg extension for RGB images
        filename = f"balloon_tracking_{timestamp}_{self.image_counter:04d}.tiff"
        return filename
    
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
        camera_status_text = "AVAILABLE" if CAMERA_AVAILABLE else "NOT AVAILABLE"
        camera_status_color = "#00ff00" if CAMERA_AVAILABLE else "#ff0000"
        self.camera_status_label = QLabel(camera_status_text)
        self.camera_status_label.setAlignment(Qt.AlignCenter)
        self.camera_status_label.setFont(QFont("Arial", 8))
        self.camera_status_label.setStyleSheet(f"color: {camera_status_color}; margin-bottom: 6px;")
        camera_layout.addWidget(self.camera_status_label)
        
        # Camera info display
        if CAMERA_AVAILABLE and camera_info:
            camera_model = camera_info.get('Name', 'Unknown Camera')
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
        
        self.gain_spinbox = QSpinBox()
        self.gain_spinbox.setRange(0, 500)
        self.gain_spinbox.setValue(self.camera_gain)
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
        self.exposure_spinbox.setValue(self.camera_exposure / 1000.0)  # Convert microseconds to milliseconds
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
            if (seconds_in_minute // 10) % 2 == 0:
                if (self.last_exposure_check == -1 or current_second > (self.last_exposure_check + (self.camera_exposure // 1e6))) and seconds_in_minute != self.last_exposure_check:
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

    def trigger_camera_capture(self):
        """Trigger camera capture and save image with unique filename"""

        try:
            if CAMERA_AVAILABLE and camera:
                # Initialize camera for capture
                if not self.initialize_camera_for_capture():
                    print("Failed to initialize camera for capture")
                    return

            # Check if seconds increased by 2 (handle wrap-around at 60)
                filename = self.generate_filename()
                print(f"Triggering camera capture: {filename}")
                print(f"Camera settings - Gain: {self.camera_gain}, Exposure: {self.camera_exposure}μs")
                # Call the RGB_photo function from ZWO_Trigger
                RGB_photo(filename, self.camera_gain, self.camera_exposure)
                
                print(f"Camera capture completed: {filename}")
                
                # Update camera status to show success
                if hasattr(self, 'camera_status_label'):
                    self.camera_status_label.setText("CAPTURE OK")
                    self.camera_status_label.setStyleSheet("color: #00ff00; margin-bottom: 6px;")
                    
                    # Reset status after 3 seconds
                    QTimer.singleShot(3000, lambda: self.reset_camera_status())
                # Update last_seconds after the check

            else:
                print("Camera not available or not initialized")
                # Call dummy function to show what would happen
                # RGB_photo("dummy_filename.jpg", self.camera_gain, self.camera_exposure)
        except Exception as e:
            print(f"Error during camera capture: {e}")
            # Update camera status to show error
            if hasattr(self, 'camera_status_label'):
                self.camera_status_label.setText("ERROR")
                self.camera_status_label.setStyleSheet("color: #ff0000; margin-bottom: 6px;")
                # Reset status after 5 seconds
                QTimer.singleShot(5000, lambda: self.reset_camera_status())
    
        
    def reset_camera_status(self):
        """Reset camera status display to default"""
        if hasattr(self, 'camera_status_label'):
            camera_status_text = "AVAILABLE" if CAMERA_AVAILABLE else "NOT AVAILABLE"
            camera_status_color = "#00ff00" if CAMERA_AVAILABLE else "#ff0000"
            self.camera_status_label.setText(camera_status_text)
            self.camera_status_label.setStyleSheet(f"color: {camera_status_color}; margin-bottom: 6px;")