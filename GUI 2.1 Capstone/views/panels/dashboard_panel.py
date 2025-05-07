import time
import math
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                           QLabel, QFrame, QSizePolicy, QSpacerItem, QProgressBar,
                           QGroupBox)
from PyQt5.QtCore import Qt, QTimer, QSize, QRect, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QPainter, QBrush, QPen, QRadialGradient

from views.widgets.compass_widget import CompassWidget
from views.widgets.dial_widget import SpeedDialWidget
from views.widgets.clock_widget import DigitalClockWidget

class GaugeWidget(QFrame):
    """An analog-style gauge widget for displaying values within a range."""
    
    def __init__(self, title, min_value=0, max_value=100, units="", start_angle=-140, end_angle=140, parent=None):
        super().__init__(parent)
        self.title = title
        self.min_value = min_value
        self.max_value = max_value
        self.units = units
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.value = min_value
        self.warning_threshold = None
        self.critical_threshold = None
        
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Title label
        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # Value label
        self.value_label = QLabel("--")
        value_font = QFont()
        value_font.setPointSize(14)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        self.value_label.setAlignment(Qt.AlignCenter)
        
        # Units label
        self.units_label = QLabel(units)
        self.units_label.setAlignment(Qt.AlignCenter)
        
        # Add to layout
        layout.addWidget(self.title_label)
        # Gauge will be drawn in paintEvent
        layout.addSpacing(70)  # Space for the gauge
        layout.addWidget(self.value_label)
        layout.addWidget(self.units_label)
    
    def set_warning_threshold(self, threshold):
        """Set warning threshold value"""
        self.warning_threshold = threshold
    
    def set_critical_threshold(self, threshold):
        """Set critical threshold value"""
        self.critical_threshold = threshold
    
    def update_value(self, value):
        """Update the displayed value"""
        self.value = max(self.min_value, min(self.max_value, value))
        self.value_label.setText(f"{self.value:.1f}")
        
        # Set text color based on thresholds
        if self.critical_threshold is not None and self.value >= self.critical_threshold:
            self.value_label.setStyleSheet("color: #ff3333;")
        elif self.warning_threshold is not None and self.value >= self.warning_threshold:
            self.value_label.setStyleSheet("color: #ffaa00;")
        else:
            self.value_label.setStyleSheet("color: #33ff33;")
        
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Define drawing area
        rect = self.rect()
        rect.setTop(rect.top() + 30)  # Account for title
        rect.setBottom(rect.top() + 70)  # Height of gauge
        rect.adjust(10, 0, -10, 0)  # Margins
        
        center = rect.center()
        radius = int(min(rect.width(), rect.height()) / 2)  # Convert radius to int
        
        # Create a QRect for the arc
        arc_rect = QRect(
            int(center.x() - radius),
            int(center.y() - radius),
            int(radius * 2),
            int(radius * 2)
        )
        
        # Draw background arc using QRect
        painter.setPen(QPen(QColor(50, 50, 50), 10))
        painter.drawArc(arc_rect, self.start_angle * 16, (self.end_angle - self.start_angle) * 16)
        
        # Draw value arc
        span_angle = self.end_angle - self.start_angle
        value_angle = self.start_angle + span_angle * (self.value - self.min_value) / (self.max_value - self.min_value)
        
        # Determine color based on thresholds
        if self.critical_threshold is not None and self.value >= self.critical_threshold:
            arc_color = QColor(255, 50, 50)
        elif self.warning_threshold is not None and self.value >= self.warning_threshold:
            arc_color = QColor(255, 170, 0)
        else:
            arc_color = QColor(50, 255, 50)
        
        painter.setPen(QPen(arc_color, 10))
        painter.drawArc(arc_rect, self.start_angle * 16, int((value_angle - self.start_angle) * 16))
        
        # Draw needle
        painter.save()
        painter.translate(center)
        painter.rotate(value_angle)
        
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.setBrush(QBrush(QColor(200, 200, 200)))
        
        # Needle points
        needle_points = []
        needle_points.append(QPoint(0, int(-radius + 10)))
        needle_points.append(QPoint(-4, 0))
        needle_points.append(QPoint(4, 0))
        
        painter.drawConvexPolygon(needle_points)
        
        # Draw center cap
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(0, 0), 5, 5)
        
        painter.restore()
        
        # End the painter explicitly
        painter.end()


class ModernIndicator(QFrame):
    """A modern-looking indicator for telemetry values"""
    
    def __init__(self, title, units="", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(60)
        self.setStyleSheet("background-color: #1E1E1E; border-radius: 8px; padding: 4px;")
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header layout
        header_layout = QHBoxLayout()
        
        # Title label
        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        
        # Units label
        self.units_label = QLabel(units)
        self.units_label.setStyleSheet("color: #888888;")
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.units_label)
        
        # Value label
        self.value_label = QLabel("--")
        value_font = QFont()
        value_font.setPointSize(16)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        
        # Add to layout
        layout.addLayout(header_layout)
        layout.addWidget(self.value_label)
    
    def update_value(self, value, color=None):
        """Update the displayed value and optionally set text color."""
        self.value_label.setText(str(value))
        if color:
            self.value_label.setStyleSheet(f"color: {color.name()};")
        else:
            self.value_label.setStyleSheet("color: white;")


class StatusCard(QFrame):
    """A card-style status indicator"""
    
    def __init__(self, title, icon=None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet("background-color: #1E1E1E; border-radius: 8px;")
        
        # Create layout
        layout = QHBoxLayout(self)
        
        # Icon (if provided)
        if icon:
            icon_label = QLabel()
            icon_pixmap = QPixmap(icon)
            icon_label.setPixmap(icon_pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout.addWidget(icon_label)
        
        # Title
        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        
        # Status
        self.status_label = QLabel("Unknown")
        status_font = QFont()
        status_font.setBold(True)
        status_font.setPointSize(10)
        self.status_label.setFont(status_font)
        
        # Add to layout
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.status_label)
    
    def update_status(self, status, color=None):
        """Update status text and color"""
        self.status_label.setText(status)
        if color:
            self.status_label.setStyleSheet(f"color: {color.name()};")
        else:
            self.status_label.setStyleSheet("color: white;")


class MissionClockWidget(QFrame):
    """Digital mission clock widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet("background-color: #1E1E1E; border-radius: 8px;")
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("MISSION TIME")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        
        # Clock digits
        self.time_display = QLabel("00:00:00")
        time_font = QFont("Arial", 16, QFont.Bold)
        self.time_display.setFont(time_font)
        self.time_display.setAlignment(Qt.AlignCenter)
        self.time_display.setStyleSheet("color: #33ff33;")
        
        # Add to layout
        layout.addWidget(title)
        layout.addWidget(self.time_display)
    
    def update_time(self, hours, minutes, seconds):
        """Update the displayed time"""
        self.time_display.setText(f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}")


class EventLogger(QFrame):
    """Simple event logger widget that displays timestamped events"""
    
    def __init__(self, max_events=6, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)
        self.setStyleSheet("background-color: #1a1a1a;")
        
        self.max_events = max_events
        self.events = []
        
        self.layout = QVBoxLayout(self)
        
        # Title label
        title = QLabel("Event Log")
        title.setFont(QFont("Arial", 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)
        
        # Event labels
        self.event_labels = []
        for i in range(max_events):
            label = QLabel("")
            label.setFont(QFont("Courier New", 8))
            label.setWordWrap(True)
            self.event_labels.append(label)
            self.layout.addWidget(label)
    
    def addEvent(self, event_text):
        """Add a new event to the log"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.events.insert(0, f"[{timestamp}] {event_text}")
        
        # Only keep max_events
        self.events = self.events[:self.max_events]
        
        # Update display
        for i, event in enumerate(self.events):
            if i < len(self.event_labels):
                self.event_labels[i].setText(event)
        
        # Clear any unused labels
        for i in range(len(self.events), len(self.event_labels)):
            self.event_labels[i].setText("")


class DashboardPanel(QWidget):
    """Enhanced dashboard panel with graphical indicators"""
    
    def __init__(self, telemetry_model, connection_model, parent=None):
        super().__init__(parent)
        self.telemetry_model = telemetry_model
        self.connection_model = connection_model
        self.launch_time = None
        
        # Set styles
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 12px;
                font-weight: bold;
                background-color: #222222;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        # Connect to model signals
        self.telemetry_model.data_updated.connect(self.update_indicators)
        self.connection_model.connection_changed.connect(self.update_connection_status)
        
        # Setup UI
        self.setup_ui()
        
        # Timer for dynamic updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dynamic_displays)
        self.timer.start(1000)  # Update every second
    
    def setup_ui(self):
        """Set up the enhanced dashboard UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Top row - Status cards
        status_layout = QHBoxLayout()
        
        # Flight status
        self.flight_status_card = StatusCard("FLIGHT STATUS")
        
        # Mission clock
        self.mission_clock = MissionClockWidget()
        
        # Connection status
        self.connection_status_card = StatusCard("CONNECTION")
        
        status_layout.addWidget(self.flight_status_card)
        status_layout.addWidget(self.mission_clock)
        status_layout.addWidget(self.connection_status_card)
        
        main_layout.addLayout(status_layout)
        
        # Middle section - Primary telemetry
        middle_layout = QHBoxLayout()
        
        # Left column - Flight gauges
        gauges_group = QGroupBox("FLIGHT DATA")
        gauges_layout = QGridLayout(gauges_group)
        
        # Altitude gauge
        self.altitude_gauge = GaugeWidget("ALTITUDE", 0, 30000, "m", -120, 120)
        self.altitude_gauge.set_warning_threshold(25000)
        self.altitude_gauge.set_critical_threshold(28000)
        
        # Vertical speed
        self.vspeed_gauge = GaugeWidget("VERTICAL SPEED", -20, 20, "m/s", -120, 120)
        
        # Ground speed from GPS
        self.hspeed_gauge = GaugeWidget("GROUND SPEED", 0, 100, "m/s", -120, 120)
        
        # IMU Orientation
        self.orientation_group = QGroupBox("ORIENTATION")
        orientation_layout = QGridLayout(self.orientation_group)
        
        self.roll_indicator = ModernIndicator("Roll", "°")
        self.pitch_indicator = ModernIndicator("Pitch", "°")
        self.yaw_indicator = ModernIndicator("Yaw", "°")
        
        orientation_layout.addWidget(self.roll_indicator, 0, 0)
        orientation_layout.addWidget(self.pitch_indicator, 0, 1)
        orientation_layout.addWidget(self.yaw_indicator, 1, 0, 1, 2)
        
        # Layout for flight data
        gauges_layout.addWidget(self.altitude_gauge, 0, 0)
        gauges_layout.addWidget(self.vspeed_gauge, 0, 1)
        gauges_layout.addWidget(self.hspeed_gauge, 1, 0)
        gauges_layout.addWidget(self.orientation_group, 1, 1)
        
        # Right column - GPS, Environment, and System Status
        data_layout = QVBoxLayout()
        
        # GPS panel
        gps_group = QGroupBox("GPS DATA")
        gps_layout = QGridLayout(gps_group)
        
        self.latitude_indicator = ModernIndicator("Latitude", "°")
        self.longitude_indicator = ModernIndicator("Longitude", "°")
        self.gps_altitude_indicator = ModernIndicator("GPS Altitude", "m")
        self.gps_time_indicator = ModernIndicator("GPS Time", "UTC")
        self.gps_status_indicator = StatusCard("GPS STATUS")
        
        gps_layout.addWidget(self.latitude_indicator, 0, 0)
        gps_layout.addWidget(self.longitude_indicator, 0, 1)
        gps_layout.addWidget(self.gps_altitude_indicator, 1, 0)
        gps_layout.addWidget(self.gps_time_indicator, 1, 1)
        gps_layout.addWidget(self.gps_status_indicator, 2, 0, 1, 2)
        
        # Environmental panel
        env_group = QGroupBox("ENVIRONMENT")
        env_layout = QGridLayout(env_group)
        
        self.temp_indicator = ModernIndicator("Temperature", "°C")
        self.pressure_indicator = ModernIndicator("Pressure", "hPa")
        self.baro_altitude_indicator = ModernIndicator("Barometric Alt", "m")
        
        env_layout.addWidget(self.temp_indicator, 0, 0)
        env_layout.addWidget(self.pressure_indicator, 0, 1)
        env_layout.addWidget(self.baro_altitude_indicator, 1, 0, 1, 2)
        
        # System status panel
        sys_group = QGroupBox("SYSTEM STATUS")
        sys_layout = QGridLayout(sys_group)
        
        self.signal_indicator = ModernIndicator("RSSI", "dBm")
        self.snr_indicator = ModernIndicator("SNR", "dB")
        self.sd_status_indicator = StatusCard("SD CARD")
        self.actuator_status_indicator = StatusCard("ACTUATOR")
        
        # Add photodiode indicators
        self.photodiode1_indicator = ModernIndicator("Photodiode 1", "")
        self.photodiode2_indicator = ModernIndicator("Photodiode 2", "")
        
        sys_layout.addWidget(self.signal_indicator, 0, 0)
        sys_layout.addWidget(self.snr_indicator, 0, 1)
        sys_layout.addWidget(self.sd_status_indicator, 1, 0)
        sys_layout.addWidget(self.actuator_status_indicator, 1, 1)
        sys_layout.addWidget(self.photodiode1_indicator, 2, 0)
        sys_layout.addWidget(self.photodiode2_indicator, 2, 1)
        
        # Add panels to data layout
        data_layout.addWidget(gps_group)
        data_layout.addWidget(env_group)
        data_layout.addWidget(sys_group)
        
        # Add columns to middle layout
        middle_layout.addWidget(gauges_group, 1)
        middle_layout.addLayout(data_layout, 1)
        
        main_layout.addLayout(middle_layout, 1)
        
        # Bottom row - Predictions and event log
        bottom_layout = QHBoxLayout()
        
        # Event log
        self.event_log = EventLogger(8)
        
        bottom_layout.addWidget(self.event_log, 1)
        
        main_layout.addLayout(bottom_layout)
        
        # Initialize with default values
        self.update_connection_status(False)
        self.update_flight_status("Pre-Launch")
    
    def update_indicators(self):
        """Update all indicators with current telemetry data."""
        # Retrieve data from telemetry model
        telemetry = self.telemetry_model.get_latest_telemetry()
        if not telemetry:
            return
        
        # Update altitude and speed gauges
        if "altitude" in telemetry:
            altitude = telemetry["altitude"]
            self.altitude_gauge.update_value(altitude)
            
            # Log significant altitude changes
            if hasattr(self, 'last_altitude'):
                if altitude > self.last_altitude + 1000:  # Log every 1000m gain
                    self.event_log.addEvent(f"Altitude: {altitude:.0f}m")
            self.last_altitude = altitude
        
        if "vertical_speed" in telemetry:
            vert_speed = telemetry["vertical_speed"]
            self.vspeed_gauge.update_value(vert_speed)
            
            # Color for vertical speed
            if vert_speed > 0:
                color = QColor("#33ff33")  # Green for ascending
            elif vert_speed < 0:
                color = QColor("#ff3333")  # Red for descending
            else:
                color = QColor("#ffffff")  # White for neutral
        
        if "horizontal_speed" in telemetry:
            self.hspeed_gauge.update_value(telemetry["horizontal_speed"])
        
        if "heading" in telemetry:
            self.compass.set_heading(telemetry["heading"])
        
        # Update GPS indicators
        if "latitude" in telemetry:
            self.latitude_indicator.update_value(f"{telemetry['latitude']:.6f}")
        if "longitude" in telemetry:
            self.longitude_indicator.update_value(f"{telemetry['longitude']:.6f}")
        
        # Update environmental indicators
        if "external_temp" in telemetry:
            ext_temp = telemetry["external_temp"]
            # Colorize temperature
            if ext_temp < -20:
                color = QColor("#33aaff")  # Cold blue
            elif ext_temp > 40:
                color = QColor("#ff3333")  # Hot red
            else:
                color = QColor("#ffffff")  # Normal white
            self.temp_ext_indicator.update_value(f"{ext_temp:.1f}", color)
        
        if "internal_temp" in telemetry:
            int_temp = telemetry["internal_temp"]
            # Colorize temperature with warnings
            if int_temp > 60:
                color = QColor("#ff3333")  # Critical hot
            elif int_temp > 45:
                color = QColor("#ffaa33")  # Warning hot
            elif int_temp < -10:
                color = QColor("#33aaff")  # Warning cold
            else:
                color = QColor("#ffffff")  # Normal
            self.temp_int_indicator.update_value(f"{int_temp:.1f}", color)
        
        if "pressure" in telemetry:
            self.pressure_indicator.update_value(f"{telemetry['pressure']:.1f}")
        
        # Update system status
        if "battery" in telemetry:
            bat_value = telemetry["battery"]
            # Set color based on battery level
            if bat_value > 3.7:
                color = QColor("#33ff33")  # Good
            elif bat_value > 3.5:
                color = QColor("#ffaa33")  # Warning
            else:
                color = QColor("#ff3333")  # Critical
            self.battery_indicator.update_value(f"{bat_value:.2f}", color)
            
            # Log battery events
            if bat_value < 3.5 and (not hasattr(self, 'last_battery') or self.last_battery >= 3.5):
                self.event_log.addEvent(f"LOW BATTERY: {bat_value:.2f}V")
            self.last_battery = bat_value
        
        if "rssi" in telemetry:
            rssi = telemetry["rssi"]
            # Set color based on signal strength
            if rssi > -70:
                color = QColor("#33ff33")  # Good
            elif rssi > -90:
                color = QColor("#ffaa33")  # Warning
            else:
                color = QColor("#ff3333")  # Critical
            self.signal_indicator.update_value(f"{rssi}", color)
        
        if "packet_count" in telemetry:
            self.packets_indicator.update_value(telemetry["packet_count"])
        
        # Update flight status based on vertical movement
        if "vertical_speed" in telemetry and "altitude" in telemetry:
            altitude = telemetry["altitude"]
            vert_speed = telemetry["vertical_speed"]
            
            # Set launch time if we detect takeoff
            if not self.launch_time and altitude > 10 and vert_speed > 0.5:
                self.launch_time = time.time()
                self.event_log.addEvent("LAUNCH DETECTED")
            
            # Determine flight status
            prev_status = getattr(self, 'current_flight_status', None)
            
            if altitude < 10:
                new_status = "Pre-Launch" if vert_speed < 0.5 else "Launching"
            elif vert_speed > 0.5:
                new_status = "Ascending"
            elif vert_speed < -0.5:
                new_status = "Descending"
            elif altitude > 10 and abs(vert_speed) < 0.5:
                new_status = "Floating"
            else:
                new_status = prev_status
            
            # Log status changes
            if new_status != prev_status:
                self.event_log.addEvent(f"STATUS: {new_status}")
                self.current_flight_status = new_status
            
            self.update_flight_status(new_status)
        
        # Update predictions
        if "max_altitude" in telemetry:
            self.max_altitude_indicator.update_status(f"{telemetry['max_altitude']:.1f} m", QColor("#33aaff"))
        
        if "predicted_landing" in telemetry:
            lat = telemetry["predicted_landing"]["latitude"]
            lon = telemetry["predicted_landing"]["longitude"]
            self.predicted_landing_indicator.update_status(f"{lat:.6f}, {lon:.6f}")
        
        if "time_to_landing" in telemetry:
            minutes = int(telemetry["time_to_landing"] / 60)
            seconds = int(telemetry["time_to_landing"] % 60)
            self.landing_time_indicator.update_status(f"{minutes:02d}:{seconds:02d}")
    
    def update_connection_status(self, connected, port=None):
        """Update connection status indicator."""
        if connected:
            self.connection_status_card.update_status(f"Connected ({port})", QColor("#33ff33"))
            self.event_log.addEvent(f"Connected to {port}")
        else:
            self.connection_status_card.update_status("Disconnected", QColor("#ff3333"))
            if hasattr(self, 'was_connected') and self.was_connected:
                self.event_log.addEvent("Connection lost")
        self.was_connected = connected
    
    def update_flight_status(self, status):
        """Update flight status indicator."""
        status_colors = {
            "Pre-Launch": QColor("#888888"),
            "Launching": QColor("#ffaa33"),
            "Ascending": QColor("#33ff33"),
            "Floating": QColor("#33aaff"),
            "Descending": QColor("#ffaa33"),
            "Landed": QColor("#3333ff")
        }
        
        color = status_colors.get(status, QColor("#888888"))
        self.flight_status_card.update_status(status, color)
    
    def update_dynamic_displays(self):
        """Update displays that change even without new telemetry"""
        # Update mission time
        if self.launch_time:
            elapsed = time.time() - self.launch_time
            hours = elapsed / 3600
            minutes = (elapsed % 3600) / 60
            seconds = elapsed % 60
            self.mission_clock.update_time(hours, minutes, seconds)
        else:
            self.mission_clock.update_time(0, 0, 0)

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QGroupBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

class DashboardPanel(QWidget):
    def __init__(self, telemetry_model, connection_model=None, parent=None):
        super().__init__(parent)
        self.telemetry_model = telemetry_model
        self.connection_model = connection_model
        self.parent = parent
        self.telemetry_model.register_callback(self.update_telemetry)
        self.was_connected = False
        self.launch_time = None
        
        self.init_ui()
    
    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        
        # Flight Data Group
        flight_group = QGroupBox("Flight Data")
        flight_layout = QGridLayout()
        
        self.timestamp_label = QLabel("Timestamp: --")
        self.pressure_label = QLabel("Pressure: -- Pa")
        self.altitude_label = QLabel("Altitude: -- m")
        self.temperature_label = QLabel("Temperature: -- °C")
        
        flight_layout.addWidget(self.timestamp_label, 0, 0)
        flight_layout.addWidget(self.pressure_label, 0, 1)
        flight_layout.addWidget(self.altitude_label, 1, 0)
        flight_layout.addWidget(self.temperature_label, 1, 1)
        
        flight_group.setLayout(flight_layout)
        main_layout.addWidget(flight_group)
        
        # IMU Data Group
        imu_group = QGroupBox("IMU Data")
        imu_layout = QGridLayout()
        
        self.accel_x_label = QLabel("Accel X: -- m/s²")
        self.accel_y_label = QLabel("Accel Y: -- m/s²")
        self.accel_z_label = QLabel("Accel Z: -- m/s²")
        self.gyro_x_label = QLabel("Gyro X: -- deg/s")
        self.gyro_y_label = QLabel("Gyro Y: -- deg/s")
        self.gyro_z_label = QLabel("Gyro Z: -- deg/s")
        self.yaw_label = QLabel("Yaw: -- deg")
        self.pitch_label = QLabel("Pitch: -- deg")
        self.roll_label = QLabel("Roll: -- deg")
        
        imu_layout.addWidget(self.accel_x_label, 0, 0)
        imu_layout.addWidget(self.accel_y_label, 0, 1)
        imu_layout.addWidget(self.accel_z_label, 0, 2)
        imu_layout.addWidget(self.gyro_x_label, 1, 0)
        imu_layout.addWidget(self.gyro_y_label, 1, 1)
        imu_layout.addWidget(self.gyro_z_label, 1, 2)
        imu_layout.addWidget(self.yaw_label, 2, 0)
        imu_layout.addWidget(self.pitch_label, 2, 1)
        imu_layout.addWidget(self.roll_label, 2, 2)
        
        imu_group.setLayout(imu_layout)
        main_layout.addWidget(imu_group)
        
        # GPS & Power Group
        gps_power_group = QGroupBox("GPS & Power")
        gps_power_layout = QGridLayout()
        
        self.battery_label = QLabel("Battery: -- V")
        self.gps_lat_label = QLabel("Latitude: --")
        self.gps_lon_label = QLabel("Longitude: --")
        self.abort_label = QLabel("Abort Status: No")
        
        gps_power_layout.addWidget(self.battery_label, 0, 0)
        gps_power_layout.addWidget(self.gps_lat_label, 0, 1)
        gps_power_layout.addWidget(self.gps_lon_label, 1, 0)
        gps_power_layout.addWidget(self.abort_label, 1, 1)
        
        gps_power_group.setLayout(gps_power_layout)
        main_layout.addWidget(gps_power_group)
        
        # Status Group
        status_group = QGroupBox("Status Messages")
        status_layout = QVBoxLayout()
        
        self.status_msg_label = QLabel("Status: --")
        self.status_heartbeat_label = QLabel("Heartbeat: --")
        
        status_layout.addWidget(self.status_msg_label)
        status_layout.addWidget(self.status_heartbeat_label)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Set main layout
        self.setLayout(main_layout)
    
    def update_telemetry(self, telemetry_data):
        """Update the dashboard with new telemetry data"""
        # Update Flight Data
        if "timestamp" in telemetry_data:
            self.timestamp_label.setText(f"Timestamp: {telemetry_data['timestamp']}")
        
        if "pressure" in telemetry_data:
            self.pressure_label.setText(f"Pressure: {telemetry_data['pressure']} Pa")
        
        if "altitude" in telemetry_data:
            self.altitude_label.setText(f"Altitude: {telemetry_data['altitude']} m")
        
        if "temperature" in telemetry_data:
            self.temperature_label.setText(f"Temperature: {telemetry_data['temperature']} °C")
        
        # Update IMU Data
        if "linear_accel_x" in telemetry_data:
            self.accel_x_label.setText(f"Accel X: {telemetry_data['linear_accel_x']:.2f} m/s²")
        
        if "linear_accel_y" in telemetry_data:
            self.accel_y_label.setText(f"Accel Y: {telemetry_data['linear_accel_y']:.2f} m/s²")
        
        if "linear_accel_z" in telemetry_data:
            self.accel_z_label.setText(f"Accel Z: {telemetry_data['linear_accel_z']:.2f} m/s²")
        
        if "angular_vel_x" in telemetry_data:
            self.gyro_x_label.setText(f"Gyro X: {telemetry_data['angular_vel_x']:.2f} deg/s")
        
        if "angular_vel_y" in telemetry_data:
            self.gyro_y_label.setText(f"Gyro Y: {telemetry_data['angular_vel_y']:.2f} deg/s")
        
        if "angular_vel_z" in telemetry_data:
            self.gyro_z_label.setText(f"Gyro Z: {telemetry_data['angular_vel_z']:.2f} deg/s")
        
        if "orientation_yaw" in telemetry_data:
            self.yaw_label.setText(f"Yaw: {telemetry_data['orientation_yaw']:.2f} deg")
        
        if "orientation_pitch" in telemetry_data:
            self.pitch_label.setText(f"Pitch: {telemetry_data['orientation_pitch']:.2f} deg")
        
        if "orientation_roll" in telemetry_data:
            self.roll_label.setText(f"Roll: {telemetry_data['orientation_roll']:.2f} deg")
        
        # Update GPS & Power Data
        if "battery_voltage" in telemetry_data:
            self.battery_label.setText(f"Battery: {telemetry_data['battery_voltage']:.2f} V")
        
        if "latitude" in telemetry_data:
            self.gps_lat_label.setText(f"Latitude: {telemetry_data['latitude']:.6f}")
        
        if "longitude" in telemetry_data:
            self.gps_lon_label.setText(f"Longitude: {telemetry_data['longitude']:.6f}")
        
        if "abort_command" in telemetry_data:
            self.abort_label.setText(f"Abort Status: {'Yes' if telemetry_data['abort_command'] else 'No'}")
        
        # Update Status Messages
        if "status_msg" in telemetry_data:
            self.status_msg_label.setText(f"Status: {telemetry_data['status_msg']}")
        
        if "status_heartbeat" in telemetry_data:
            self.status_heartbeat_label.setText(f"Heartbeat: {telemetry_data['status_heartbeat']}")
    
    def update_connection_status(self, connected, port=None):
        """Update connection status indicator"""
        # This method is called by the radio controller
        # In a real implementation, you might update a status indicator here
        if connected:
            print(f"Dashboard: Connected to {port}")
        else:
            print("Dashboard: Disconnected")
        self.was_connected = connected
