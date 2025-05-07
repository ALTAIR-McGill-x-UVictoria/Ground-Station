import time
import math
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                           QLabel, QFrame, QSizePolicy, QSpacerItem, QGroupBox) # Removed QProgressBar, QRect, QPoint
from PyQt5.QtCore import Qt, QTimer # Removed QSize, QRect, QPoint
from PyQt5.QtGui import QFont, QColor # Removed QPalette, QPixmap, QPainter, QBrush, QPen, QRadialGradient

from views.widgets.compass_widget import CompassWidget
from views.widgets.dial_widget import SpeedDialWidget
from views.widgets.clock_widget import DigitalClockWidget # Assuming this is equivalent to gui.py's DigitalClockWidget

# Removed GaugeWidget, ModernIndicator, StatusCard, MissionClockWidget, EventLogger classes

class DashboardPanel(QWidget):
    """Dashboard panel based on gui.py structure"""
    
    def __init__(self, telemetry_model, connection_model, parent=None):
        super().__init__(parent)
        self.telemetry_model = telemetry_model
        self.connection_model = connection_model
        # self.launch_time = None # Not used from gui.py in this way
        self.start_time = time.time() # From gui.py for time calculations
        self.status_widgets = {} # From gui.py

        # Set styles from gui.py (simplified, can be expanded)
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex; /* Ensure space for title */
                font-weight: bold;
                color: #00ff00; /* GroupBox title color */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center; /* Center title */
                padding: 0 5px;
            }
            QLabel {
                color: #ffffff; /* Default label color */
            }
        """)
        
        # Connect to model signals
        self.telemetry_model.data_updated.connect(self.update_indicators_from_model)
        # self.connection_model.connection_changed.connect(self.update_connection_status) # MainWindow handles this

        # Setup UI
        self.setup_ui()
        
        # Timer for dynamic updates (e.g., mission clock if re-added, or other periodic updates)
        # self.timer = QTimer(self)
        # self.timer.timeout.connect(self.update_dynamic_displays)
        # self.timer.start(1000)

        # Initialize last altitude and time for vertical speed calculation
        self.last_altitude = None
        self.last_altitude_time = None

    def setup_ui(self):
        """Set up the dashboard UI based on gui.py."""
        main_layout = QGridLayout(self) # Changed to QGridLayout for better structure
        main_layout.setSpacing(10)
        
        # Navigation Data Section (top left in gui.py)
        nav_group = QGroupBox("Navigation")
        nav_layout = QGridLayout(nav_group) # Use QGridLayout for more control
        nav_layout.setSpacing(15)
        
        # Add digital clock (GPS Time)
        clock_frame = QFrame()
        clock_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        clock_frame.setStyleSheet("QFrame { border: 1px solid #3a3a3a; border-radius: 6px; background-color: #2a2a2a; }")
        clock_layout_v = QVBoxLayout(clock_frame) # QVBoxLayout for the clock
        self.gps_clock = DigitalClockWidget()
        clock_layout_v.addWidget(self.gps_clock)
        nav_layout.addWidget(clock_frame, 0, 0, 1, 2) # Span 2 columns

        # Compass widgets
        compass_widgets_layout = QHBoxLayout() # Horizontal layout for two compasses
        
        # Vehicle heading compass
        vehicle_compass_frame = QFrame()
        vehicle_compass_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        vehicle_compass_frame.setStyleSheet("QFrame { border: 1px solid #3a3a3a; border-radius: 6px; background-color: #2a2a2a; padding: 5px; } QLabel { color: #00ff00; font-weight: bold; font-size: 12px; }")
        vehicle_compass_v_layout = QVBoxLayout(vehicle_compass_frame)
        vehicle_compass_v_layout.setSpacing(5)
        self.vehicle_compass = CompassWidget()
        vehicle_compass_label = QLabel("Vehicle Heading")
        vehicle_compass_label.setAlignment(Qt.AlignCenter)
        vehicle_compass_v_layout.addWidget(vehicle_compass_label)
        vehicle_compass_v_layout.addWidget(self.vehicle_compass)
        compass_widgets_layout.addWidget(vehicle_compass_frame)

        # Target bearing compass
        target_compass_frame = QFrame()
        target_compass_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        target_compass_frame.setStyleSheet("QFrame { border: 1px solid #3a3a3a; border-radius: 6px; background-color: #2a2a2a; padding: 5px; } QLabel { color: #00ff00; font-weight: bold; font-size: 12px; }")
        target_compass_v_layout = QVBoxLayout(target_compass_frame)
        target_compass_v_layout.setSpacing(5)
        self.target_compass = CompassWidget()
        target_compass_label = QLabel("Target Bearing")
        target_compass_label.setAlignment(Qt.AlignCenter)
        target_compass_v_layout.addWidget(target_compass_label)
        target_compass_v_layout.addWidget(self.target_compass)
        compass_widgets_layout.addWidget(target_compass_frame)
        
        nav_layout.addLayout(compass_widgets_layout, 1, 0, 1, 2) # Span 2 columns

        # Speed dials
        dials_frame = QFrame()
        dials_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        dials_frame.setStyleSheet("QFrame { border: 1px solid #3a3a3a; border-radius: 6px; background-color: #2a2a2a; padding: 5px; }")
        speed_dials_h_layout = QHBoxLayout(dials_frame)
        speed_dials_h_layout.setSpacing(20)
        
        self.ground_speed_dial = SpeedDialWidget("Ground Speed", "m/s", max_value=50)
        self.ground_speed_dial.setMinimumSize(150,150)
        self.vertical_speed_dial = SpeedDialWidget("Vertical Speed", "m/s", max_value=20, min_value=-20) # Assuming SpeedDial can handle min_value
        self.vertical_speed_dial.setMinimumSize(150,150)
        
        speed_dials_h_layout.addWidget(self.ground_speed_dial, stretch=1)
        speed_dials_h_layout.addWidget(self.vertical_speed_dial, stretch=1)
        nav_layout.addWidget(dials_frame, 2, 0, 1, 2) # Span 2 columns

        main_layout.addWidget(nav_group, 0, 0)

        # Flight Data Section (top right)
        flight_group = QGroupBox("Flight Data")
        flight_layout_grid = QGridLayout(flight_group) # Use QGridLayout
        flight_parameters = [
            ("Altitude", "m", 0, 0, "Current altitude (Barometric)"), # Changed tooltip
            ("Temperature", "°C", 0, 1, "Outside air temperature"),
            ("Pressure", "hPa", 1, 0, "Atmospheric pressure"),
            ("GPS Altitude", "m", 1, 1, "Current altitude (GPS MSL)") # Added GPS Altitude
        ]
        self.add_parameters_to_layout(flight_parameters, flight_layout_grid)
        main_layout.addWidget(flight_group, 0, 1)

        # Radio Status Section (bottom left)
        radio_group = QGroupBox("Radio Status")
        radio_layout_grid = QGridLayout(radio_group) # Use QGridLayout
        radio_parameters = [
            ("RSSI", "dBm", 0, 0, "Received Signal Strength Indicator"),
            ("SNR", "dB", 0, 1, "Signal-to-Noise Ratio"),
            ("ACK", "", 1, 0, "Packet Acknowledgement Status"),
            ("GPS Status", "", 1, 1, "GPS Fix Status") # Changed from "GPS" to "GPS Status"
        ]
        self.add_parameters_to_layout(radio_parameters, radio_layout_grid)
        main_layout.addWidget(radio_group, 1, 0)

        # System Status Section (bottom right)
        system_group = QGroupBox("System Status")
        system_layout_grid = QGridLayout(system_group) # Use QGridLayout
        system_parameters = [
            ("SD Status", "", 0, 0, "SD Card Status"),
            ("Actuator Status", "", 0, 1, "Actuator System Status"), # Changed position
            ("Roll", "°", 1, 0, "IMU Roll"), # Added IMU data
            ("Pitch", "°", 1, 1, "IMU Pitch"),
            ("Yaw", "°", 2, 0, "IMU Yaw") # Added IMU Yaw, span if needed
        ]
        self.add_parameters_to_layout(system_parameters, system_layout_grid)
        main_layout.addWidget(system_group, 1, 1)

        # Set row/column stretch factors for balanced resizing
        main_layout.setRowStretch(0, 1)
        main_layout.setRowStretch(1, 1)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)

    def add_parameters_to_layout(self, parameters, parent_layout):
        """Helper to add parameter displays, from gui.py"""
        for name, unit, row, col, tooltip in parameters:
            frame = QFrame()
            frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            frame.setLineWidth(1) # Thinner border
            frame.setToolTip(tooltip)
            frame.setStyleSheet("QFrame { border: 1px solid #444; border-radius: 5px; background-color: #2E2E2E; padding: 5px; }")
            
            layout = QVBoxLayout(frame)
            layout.setSpacing(3) # Reduced spacing
            layout.setContentsMargins(5,5,5,5) # Margins
            
            title_label = QLabel(name)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("font-weight: bold; font-size: 11pt; color: #00ff00;") # Smaller font
            layout.addWidget(title_label)
            
            value_label = QLabel("--")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff; background-color: #2a2a2a; border-radius: 4px; padding: 3px;") # Smaller font
            layout.addWidget(value_label)
            
            if unit:
                unit_label = QLabel(unit)
                unit_label.setAlignment(Qt.AlignCenter)
                unit_label.setStyleSheet("color: #aaaaaa; font-size: 9pt;") # Smaller font
                layout.addWidget(unit_label)
            
            parent_layout.addWidget(frame, row, col)
            self.status_widgets[name.lower().replace(" ", "_")] = value_label # Store with underscore for consistency

    def update_parameter(self, name, value, format_str="{:.1f}"):
        """Update a specific parameter display, from gui.py"""
        widget_key = name.lower().replace(" ", "_")
        if widget_key in self.status_widgets:
            widget = self.status_widgets[widget_key]
            try:
                if isinstance(value, str): # If value is already a string (e.g. "Active", "No Fix")
                    formatted_value = value
                else:
                    formatted_value = format_str.format(float(value))
                widget.setText(formatted_value)
            except ValueError:
                 widget.setText(str(value)) # Fallback for non-numeric or unformattable
            
            # Visual feedback for RSSI from gui.py
            if widget_key == "rssi":
                try:
                    v = float(value)
                    if v > -70:
                        widget.setStyleSheet("font-size: 16pt; font-weight: bold; color: #00ff00; background-color: #2a2a2a; border-radius: 4px; padding: 3px;")
                    elif v > -90:
                        widget.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffff00; background-color: #2a2a2a; border-radius: 4px; padding: 3px;")
                    else:
                        widget.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ff0000; background-color: #2a2a2a; border-radius: 4px; padding: 3px;")
                except ValueError:
                    pass # Non-numeric value, keep default style

    def calculate_vertical_speed(self, current_altitude):
        """Calculate vertical speed based on altitude changes, from gui.py"""
        if self.last_altitude is None or self.last_altitude_time is None:
            self.last_altitude = current_altitude
            self.last_altitude_time = time.time()
            return 0.0
        
        now = time.time()
        time_diff = now - self.last_altitude_time
        
        if time_diff < 0.1:  # Avoid division by very small numbers or if time hasn't advanced
            return getattr(self, 'last_vertical_speed', 0.0) # Return last known speed
            
        altitude_diff = current_altitude - self.last_altitude
        vertical_speed = altitude_diff / time_diff
        
        self.last_altitude = current_altitude
        self.last_altitude_time = now
        self.last_vertical_speed = vertical_speed # Store for next potential quick return
        
        return vertical_speed

    def update_indicators_from_model(self):
        """Update dashboard indicators with data from telemetry_model."""
        data = self.telemetry_model.get_latest_data()

        # Navigation
        if data.get('gps_valid') and data.get('gps_lat') != 0 and data.get('gps_lon') != 0:
            # Vehicle heading (yaw from IMU or calculated from GPS if available)
            self.vehicle_compass.setBearing(data.get('fYaw', 0.0)) # Prefer IMU Yaw
            # Target bearing would be calculated by MapController and signaled
        else:
            self.vehicle_compass.setBearing(0.0)

        self.ground_speed_dial.setValue(data.get('gps_speed', 0.0))
        
        # Calculate and set vertical speed
        baro_alt = data.get('altitude', None)
        if baro_alt is not None:
            vertical_speed = self.calculate_vertical_speed(baro_alt)
            self.vertical_speed_dial.setValue(vertical_speed)
            self.update_parameter("Vertical Speed", vertical_speed) # Also update label if exists
        else:
            self.vertical_speed_dial.setValue(0.0)
            self.update_parameter("Vertical Speed", 0.0)


        if data.get('gps_time', 0) > 0:
            self.gps_clock.setTime(data.get('gps_time'))

        # Flight Data
        self.update_parameter("Altitude", data.get('altitude', 0.0))
        self.update_parameter("Temperature", data.get('temperature', 0.0))
        self.update_parameter("Pressure", data.get('pressure', 0.0))
        self.update_parameter("GPS Altitude", data.get('gps_alt', 0.0))

        # Radio Status
        self.update_parameter("RSSI", data.get('rssi', 0), format_str="{:.0f}")
        self.update_parameter("SNR", data.get('snr', 0), format_str="{:.0f}")
        self.update_parameter("ACK", "Yes" if data.get('ack', 0) == 1 else "No", format_str="{}")
        self.update_parameter("GPS Status", "Fix" if data.get('gps_valid', False) else "No Fix", format_str="{}")

        # System Status
        self.update_parameter("SD Status", "Active" if data.get('sd_status', False) else "Inactive", format_str="{}")
        self.update_parameter("Actuator Status", "Active" if data.get('actuator_status', False) else "Inactive", format_str="{}")
        self.update_parameter("Roll", data.get('fRoll', 0.0))
        self.update_parameter("Pitch", data.get('fPitch', 0.0))
        self.update_parameter("Yaw", data.get('fYaw', 0.0))

    # Placeholder for target bearing updates if MapController signals it
    def update_target_bearing(self, bearing):
        self.target_compass.setBearing(bearing)

    # def update_dynamic_displays(self):
        # """Update displays that change over time, like mission clock."""
        # if self.launch_time:
        #     elapsed = time.time() - self.launch_time
        #     hours, rem = divmod(elapsed, 3600)
        #     minutes, seconds = divmod(rem, 60)
            # self.mission_clock.update_time(hours, minutes, seconds) # If mission clock is re-added
