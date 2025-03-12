from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QFrame, QLabel, QSizePolicy, QSpacerItem, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, QPoint
from PyQt5.QtGui import QColor, QPalette, QFont, QBrush, QPainter, QPen, QPainterPath, QLinearGradient

from views.widgets.compass_widget import CompassWidget
from views.widgets.dial_widget import SpeedDialWidget
from views.widgets.clock_widget import DigitalClockWidget

class StatusIndicator(QFrame):
    """Small indicator widget that shows status with color"""
    
    def __init__(self, label="Status", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)
        self.setMinimumWidth(100)
        self.setMaximumHeight(30)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 2, 5, 2)
        
        self.label = QLabel(label)
        self.label.setFont(QFont("Arial", 8))
        
        self.indicator = QFrame()
        self.indicator.setFixedSize(16, 16)
        self.indicator.setFrameShape(QFrame.Box)
        self.updateStatus(False)
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.indicator, alignment=Qt.AlignRight)
    
    def updateStatus(self, status):
        """Update the indicator color based on status"""
        if status:
            self.indicator.setStyleSheet("background-color: #00ff00; border: 1px solid #00cc00;")
        else:
            self.indicator.setStyleSheet("background-color: #ff5500; border: 1px solid #cc4400;")


class ArtificialHorizon(QWidget):
    """Widget to display an artificial horizon"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.roll = 0.0
        self.pitch = 0.0
    
    def setPitchRoll(self, pitch, roll):
        """Set the pitch and roll values"""
        self.pitch = max(-90, min(90, pitch))  # Limit to +/- 90
        self.roll = roll % 360  # Normalize to 0-359
        self.update()
    
    def paintEvent(self, event):
        """Draw the artificial horizon"""
        size = min(self.width(), self.height())
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate radius
            radius = size / 2 - 10
            
            # Save current transform
            painter.save()
            
            # Move to center and rotate for roll
            painter.translate(center_x, center_y)
            painter.rotate(-self.roll)
            
            # Draw sky and ground
            pitch_offset = (self.pitch / 90.0) * radius
            
            # Sky - blue gradient
            sky_rect = QRectF(-radius, -radius - pitch_offset, radius * 2, radius * 2)
            sky_gradient = QLinearGradient(0, -radius - pitch_offset, 0, radius - pitch_offset)
            sky_gradient.setColorAt(0, QColor(100, 180, 255))
            sky_gradient.setColorAt(1, QColor(140, 210, 255))
            painter.setBrush(QBrush(sky_gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRect(sky_rect)
            
            # Ground - brown gradient
            ground_rect = QRectF(-radius, 0 - pitch_offset, radius * 2, radius * 2)
            ground_gradient = QLinearGradient(0, 0 - pitch_offset, 0, radius - pitch_offset)
            ground_gradient.setColorAt(0, QColor(130, 110, 60))
            ground_gradient.setColorAt(1, QColor(80, 70, 40))
            painter.setBrush(QBrush(ground_gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRect(ground_rect)
            
            # Draw horizon line
            painter.setPen(QPen(Qt.white, 2))
            painter.drawLine(QPointF(-radius, -pitch_offset), QPointF(radius, -pitch_offset))
            
            # Draw pitch lines
            painter.setPen(QPen(Qt.white, 1))
            for degrees in range(-90, 91, 10):
                if degrees == 0:
                    continue  # Skip horizon line (already drawn)
                    
                y_pos = (-degrees / 90.0) * radius - pitch_offset
                if abs(y_pos) < radius:
                    if degrees % 30 == 0:
                        # Longer lines for major angles
                        line_width = radius * 0.6
                        text_offset = radius * 0.7
                        painter.drawText(QPointF(text_offset, y_pos + 5), f"{abs(degrees)}")
                        painter.drawText(QPointF(-text_offset - 20, y_pos + 5), f"{abs(degrees)}")
                    else:
                        # Shorter lines for minor angles
                        line_width = radius * 0.3
                    
                    painter.drawLine(QPointF(-line_width, y_pos), QPointF(line_width, y_pos))
            
            painter.restore()
            
            # Draw the outer circle (bezel)
            painter.setPen(QPen(QColor(60, 60, 60), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(int(center_x - radius), int(center_y - radius), 
                               int(radius * 2), int(radius * 2))
            
            # Draw fixed reference aircraft symbol
            painter.setPen(QPen(QColor(255, 255, 255), 3))
            painter.translate(center_x, center_y)
            
            # Wings and nose
            wing_width = radius * 0.3
            painter.drawLine(QPointF(-wing_width, 0), QPointF(wing_width, 0))
            painter.drawLine(QPointF(0, 0), QPointF(0, -wing_width * 0.3))
            
            # Draw small circle in center
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(-3), int(-3), 6, 6)
            
        finally:
            painter.end()


class PercentBar(QWidget):
    """Custom percentage bar with label"""
    
    def __init__(self, label="Progress", min_val=0, max_val=100, parent=None):
        super().__init__(parent)
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.value = min_val
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        
        self.title = QLabel(label)
        self.title.setFont(QFont("Arial", 8))
        self.title.setAlignment(Qt.AlignLeft)
        
        self.progress = QProgressBar()
        self.progress.setRange(min_val, max_val)
        self.progress.setValue(min_val)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v / %m (%p%)")
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #222;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0a0, stop:1 #0f0);
            }
        """)
        
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.progress)
    
    def setValue(self, value):
        """Set the current value"""
        clamped_value = max(self.min_val, min(self.max_val, value))
        self.value = clamped_value
        self.progress.setValue(int(clamped_value))
        self.update()


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
    """Panel for displaying the flight computer dashboard"""
    
    def __init__(self, telemetry_model, settings_model, parent=None):
        super().__init__(parent)
        self.telemetry_model = telemetry_model
        self.settings_model = settings_model
        
        # Initialize important values before setup_ui
        self.mission_target_alt = 400
        self.mission_elapsed = 0
        
        # Setup UI components
        self.setup_ui()
        
        # Connect to model signals
        self.telemetry_model.data_updated.connect(self.update_telemetry_display)
        
        # Setup update timer for values that need constant updating
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_dynamic_displays)
        self.update_timer.start(100)  # Update every 100ms
        
        # Add test events to the log
        self.event_logger.addEvent("System initialized")
        self.event_logger.addEvent("Telemetry connection ready")
        self.event_logger.addEvent("Waiting for flight computer")
    
    def setup_ui(self):
        """Set up the dashboard panel UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # === TOP ROW ===
        top_row = QHBoxLayout()
        
        # Mission Status (Top Left)
        self.create_mission_status_group(top_row)
        
        # Quick System Status (Top Right)
        self.create_quick_status_group(top_row)
        
        main_layout.addLayout(top_row)
        
        # === MIDDLE SECTION (3x2 Grid) ===
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        
        # Primary Flight Display (Left Column)
        self.create_flight_display_group(grid_layout, 0, 0, 2, 1)  # Spans 2 rows
        
        # Navigation (Upper Right)
        self.create_navigation_group(grid_layout, 0, 1)
        
        # System Status (Lower Right)
        self.create_system_status_group(grid_layout, 1, 1)
        
        main_layout.addLayout(grid_layout)
        
        # === BOTTOM ROW ===
        bottom_row = QHBoxLayout()
        
        # Environmental Data (Bottom Left)
        self.create_environmental_group(bottom_row)
        
        # Event Log (Bottom Right)
        self.create_event_log_group(bottom_row)
        
        main_layout.addLayout(bottom_row)
    
    def create_mission_status_group(self, parent_layout):
        """Create the mission status section"""
        group_box = QGroupBox("Mission Status")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QHBoxLayout(group_box)
        
        # Mission clock
        clock_layout = QVBoxLayout()
        self.mission_clock_label = QLabel("Mission Time")
        self.mission_clock_label.setAlignment(Qt.AlignCenter)
        self.mission_clock_value = QLabel("00:00:00")
        self.mission_clock_value.setStyleSheet("color: #00ff00; font-size: 16pt; font-weight: bold;")
        self.mission_clock_value.setAlignment(Qt.AlignCenter)
        clock_layout.addWidget(self.mission_clock_label)
        clock_layout.addWidget(self.mission_clock_value)
        layout.addLayout(clock_layout)
        
        # GPS time
        self.gps_clock = DigitalClockWidget()
        self.gps_clock.setMinimumHeight(80)
        layout.addWidget(self.gps_clock)
        
        # Current mission phase
        phase_layout = QVBoxLayout()
        phase_title = QLabel("Phase")
        phase_title.setAlignment(Qt.AlignCenter)
        self.mission_phase = QLabel("PRE-LAUNCH")
        self.mission_phase.setStyleSheet("color: #ffff00; font-size: 14pt; font-weight: bold;")
        self.mission_phase.setAlignment(Qt.AlignCenter)
        phase_layout.addWidget(phase_title)
        phase_layout.addWidget(self.mission_phase)
        layout.addLayout(phase_layout)
        
        parent_layout.addWidget(group_box, 1)
    
    def create_quick_status_group(self, parent_layout):
        """Create the quick status indicators"""
        group_box = QGroupBox("Quick Status")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QGridLayout(group_box)
        layout.setSpacing(10)
        
        # Status indicators in a compact grid
        self.sd_status = StatusIndicator("SD Card")
        self.led_status = StatusIndicator("LED")
        self.actuator_status = StatusIndicator("Actuator")
        self.source_status = StatusIndicator("Source")
        self.gps_status = StatusIndicator("GPS Valid")
        
        layout.addWidget(self.sd_status, 0, 0)
        layout.addWidget(self.led_status, 0, 1)
        layout.addWidget(self.actuator_status, 1, 0)
        layout.addWidget(self.source_status, 1, 1)
        layout.addWidget(self.gps_status, 2, 0)
        
        # Signal strength
        signal_layout = QHBoxLayout()
        layout.addLayout(signal_layout, 2, 1)
        
        rssi_label = QLabel("RSSI:")
        self.rssi_value = QLabel("-100 dBm")
        self.rssi_value.setAlignment(Qt.AlignRight)
        signal_layout.addWidget(rssi_label)
        signal_layout.addWidget(self.rssi_value)
        
        parent_layout.addWidget(group_box, 1)
    
    def create_flight_display_group(self, parent_layout, row, col, rowspan, colspan):
        """Create the primary flight display group"""
        group_box = QGroupBox("Flight Data")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QGridLayout(group_box)
        layout.setSpacing(10)
        
        # Artificial horizon (center)
        self.horizon = ArtificialHorizon()
        self.horizon.setMinimumSize(200, 200)
        layout.addWidget(self.horizon, 0, 1, 2, 1)
        
        # Altitude and vertical speed (left column)
        self.altitude_dial = SpeedDialWidget("Altitude", "m", 500)
        self.altitude_dial.setMinimumSize(180, 180)
        layout.addWidget(self.altitude_dial, 0, 0)
        
        self.vertical_speed_dial = SpeedDialWidget("Vertical Speed", "m/s", 20)
        self.vertical_speed_dial.setMinimumSize(180, 180)
        layout.addWidget(self.vertical_speed_dial, 1, 0)
        
        # Ground speed and stats (right column)
        self.ground_speed_dial = SpeedDialWidget("Ground Speed", "m/s", 50)
        self.ground_speed_dial.setMinimumSize(180, 180)
        layout.addWidget(self.ground_speed_dial, 0, 2)
        
        # Mission progress stats
        stats_frame = QFrame()
        stats_frame.setFrameShape(QFrame.StyledPanel)
        stats_frame.setFrameShadow(QFrame.Sunken)
        stats_frame.setStyleSheet("background-color: #1a1a1a;")
        
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setSpacing(10)
        
        # Current altitude vs target
        self.altitude_progress = PercentBar("Altitude Progress", 0, self.mission_target_alt)
        stats_layout.addWidget(self.altitude_progress)
        
        # Stats/records
        records_layout = QGridLayout()
        records_layout.setColumnStretch(1, 1)
        self.max_altitude_label = self.add_labeled_value(records_layout, "Max Alt:", "0.0 m", 0, 0)
        self.max_speed_label = self.add_labeled_value(records_layout, "Max Speed:", "0.0 m/s", 1, 0)
        self.max_vspeed_label = self.add_labeled_value(records_layout, "Max V-Speed:", "0.0 m/s", 2, 0)
        stats_layout.addLayout(records_layout)
        
        layout.addWidget(stats_frame, 1, 2)
        
        parent_layout.addWidget(group_box, row, col, rowspan, colspan)
    
    def create_navigation_group(self, parent_layout, row, col):
        """Create the navigation section"""
        group_box = QGroupBox("Navigation")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QHBoxLayout(group_box)
        
        # Compass
        self.compass = CompassWidget()
        self.compass.setMinimumSize(180, 180)
        layout.addWidget(self.compass)
        
        # GPS coordinates
        coords_frame = QFrame()
        coords_frame.setFrameShape(QFrame.StyledPanel)
        coords_frame.setFrameShadow(QFrame.Sunken)
        coords_frame.setStyleSheet("background-color: #1a1a1a;")
        
        coords_layout = QGridLayout(coords_frame)
        coords_layout.setSpacing(5)
        
        # GPS position with larger font
        self.lat_label = self.add_labeled_value(coords_layout, "Latitude:", "0.000000°", 0, 0, True)
        self.lon_label = self.add_labeled_value(coords_layout, "Longitude:", "0.000000°", 1, 0, True)
        self.gps_alt_label = self.add_labeled_value(coords_layout, "GPS Alt:", "0.0 m", 2, 0, True)
        
        # Add separator
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.HLine)
        sep_line.setFrameShadow(QFrame.Sunken)
        coords_layout.addWidget(sep_line, 3, 0, 1, 2)
        
        # Attitude values
        self.roll_label = self.add_labeled_value(coords_layout, "Roll:", "0.0°", 4, 0)
        self.pitch_label = self.add_labeled_value(coords_layout, "Pitch:", "0.0°", 5, 0)
        self.heading_label = self.add_labeled_value(coords_layout, "Heading:", "0.0°", 6, 0, True)
        
        layout.addWidget(coords_frame)
        
        parent_layout.addWidget(group_box, row, col)
    
    def create_system_status_group(self, parent_layout, row, col):
        """Create the system status section"""
        group_box = QGroupBox("System Status")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QVBoxLayout(group_box)
        
        # Communication stats
        comm_frame = QFrame()
        comm_frame.setFrameShape(QFrame.StyledPanel)
        comm_frame.setFrameShadow(QFrame.Sunken)
        comm_frame.setStyleSheet("background-color: #1a1a1a;")
        
        comm_layout = QGridLayout(comm_frame)
        comm_layout.setSpacing(5)
        
        # Add communication stats
        self.rssi_full_label = self.add_labeled_value(comm_layout, "RSSI:", "-100 dBm", 0, 0)
        self.snr_label = self.add_labeled_value(comm_layout, "SNR:", "0 dB", 1, 0)
        self.packets_label = self.add_labeled_value(comm_layout, "Packets:", "0", 2, 0)
        self.last_packet_label = self.add_labeled_value(comm_layout, "Last Packet:", "Never", 3, 0)
        
        layout.addWidget(comm_frame)
        
        # Battery status - simulated for now
        battery_frame = QFrame()
        battery_frame.setFrameShape(QFrame.StyledPanel)
        battery_frame.setFrameShadow(QFrame.Sunken)
        battery_frame.setStyleSheet("background-color: #1a1a1a;")
        
        battery_layout = QVBoxLayout(battery_frame)
        
        # Add battery progress bar
        battery_title = QLabel("Battery Status")
        battery_title.setAlignment(Qt.AlignCenter)
        
        self.battery_progress = QProgressBar()
        self.battery_progress.setRange(0, 100)
        self.battery_progress.setValue(80)
        self.battery_progress.setFormat("80% (3.7V)")
        self.battery_progress.setStyleSheet("""
            QProgressBar {
                background-color: #222;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0a0, stop:1 #0f0);
            }
        """)
        
        battery_layout.addWidget(battery_title)
        battery_layout.addWidget(self.battery_progress)
        
        layout.addWidget(battery_frame)
        
        parent_layout.addWidget(group_box, row, col)
    
    def create_environmental_group(self, parent_layout):
        """Create the environmental data section"""
        group_box = QGroupBox("Environmental Data")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QHBoxLayout(group_box)
        
        # Temperature display
        temp_frame = QFrame()
        temp_frame.setFrameShape(QFrame.StyledPanel)
        temp_frame.setFrameShadow(QFrame.Sunken)
        temp_frame.setStyleSheet("background-color: #1a1a1a;")
        
        temp_layout = QVBoxLayout(temp_frame)
        temp_layout.setContentsMargins(10, 10, 10, 10)
        
        temp_title = QLabel("Temperature")
        temp_title.setFont(QFont("Arial", 10, QFont.Bold))
        temp_title.setAlignment(Qt.AlignCenter)
        
        self.temperature_value = QLabel("0.0 °C")
        self.temperature_value.setStyleSheet("color: #00ff00; font-size: 16pt; font-weight: bold;")
        self.temperature_value.setAlignment(Qt.AlignCenter)
        
        temp_layout.addWidget(temp_title)
        temp_layout.addWidget(self.temperature_value)
        
        layout.addWidget(temp_frame)
        
        # Pressure display
        pressure_frame = QFrame()
        pressure_frame.setFrameShape(QFrame.StyledPanel)
        pressure_frame.setFrameShadow(QFrame.Sunken)
        pressure_frame.setStyleSheet("background-color: #1a1a1a;")
        
        pressure_layout = QVBoxLayout(pressure_frame)
        pressure_layout.setContentsMargins(10, 10, 10, 10)
        
        pressure_title = QLabel("Pressure")
        pressure_title.setFont(QFont("Arial", 10, QFont.Bold))
        pressure_title.setAlignment(Qt.AlignCenter)
        
        self.pressure_value = QLabel("0.0 hPa")
        self.pressure_value.setStyleSheet("color: #00ff00; font-size: 16pt; font-weight: bold;")
        self.pressure_value.setAlignment(Qt.AlignCenter)
        
        pressure_layout.addWidget(pressure_title)
        pressure_layout.addWidget(self.pressure_value)
        
        layout.addWidget(pressure_frame)
        
        # Altitude estimate from pressure
        alt_frame = QFrame()
        alt_frame.setFrameShape(QFrame.StyledPanel)
        alt_frame.setFrameShadow(QFrame.Sunken)
        alt_frame.setStyleSheet("background-color: #1a1a1a;")
        
        alt_layout = QVBoxLayout(alt_frame)
        alt_layout.setContentsMargins(10, 10, 10, 10)
        
        alt_title = QLabel("Baro. Altitude")
        alt_title.setFont(QFont("Arial", 10, QFont.Bold))
        alt_title.setAlignment(Qt.AlignCenter)
        
        self.baro_altitude = QLabel("0.0 m")
        self.baro_altitude.setStyleSheet("color: #00ff00; font-size: 16pt; font-weight: bold;")
        self.baro_altitude.setAlignment(Qt.AlignCenter)
        
        alt_layout.addWidget(alt_title)
        alt_layout.addWidget(self.baro_altitude)
        
        layout.addWidget(alt_frame)
        
        parent_layout.addWidget(group_box, 1)
    
    def create_event_log_group(self, parent_layout):
        """Create the event log section"""
        group_box = QGroupBox("Mission Events")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QVBoxLayout(group_box)
        
        self.event_logger = EventLogger(6)
        layout.addWidget(self.event_logger)
        
        parent_layout.addWidget(group_box, 1)
    
    def add_labeled_value(self, parent_layout, label_text, value_text, row, col, is_highlight=False):
        """Add a label and value pair to a layout"""
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 9))
        
        value = QLabel(value_text)
        if is_highlight:
            value.setStyleSheet("color: #00ff00; font-weight: bold;")
        else:
            value.setStyleSheet("color: #ffffff;")
        value.setFont(QFont("Arial", 9))
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        parent_layout.addWidget(label, row, col * 2)
        parent_layout.addWidget(value, row, col * 2 + 1)
        
        return value
    
    def update_telemetry_display(self):
        """Update all telemetry displays with current data"""
        # Update flight data
        self.altitude_dial.setValue(self.telemetry_model.altitude)
        self.vertical_speed_dial.setValue(self.telemetry_model.vertical_speed)
        self.ground_speed_dial.setValue(self.telemetry_model.ground_speed)
        
        # Update artificial horizon
        self.horizon.setPitchRoll(self.telemetry_model.pitch, self.telemetry_model.roll)
        
        # Update altitude progress
        self.altitude_progress.setValue(self.telemetry_model.altitude)
        
        # Update compass
        self.compass.setHeading(self.telemetry_model.yaw)
        
        # Update GPS time
        if self.telemetry_model.gps_time:
            self.gps_clock.setTime(self.telemetry_model.gps_time)
        
        # Update environmental data
        self.temperature_value.setText(f"{self.telemetry_model.temperature:.1f} °C")
        self.pressure_value.setText(f"{self.telemetry_model.pressure:.1f} hPa")
        
        # Calculate barometric altitude (simplified)
        self.baro_altitude.setText(f"{self.telemetry_model.baro_altitude:.1f} m")
        
        # Update max values
        self.max_altitude_label.setText(f"{self.telemetry_model.max_altitude:.1f} m")
        self.max_speed_label.setText(f"{self.telemetry_model.max_speed:.1f} m/s")
        self.max_vspeed_label.setText(f"{self.telemetry_model.max_vertical_speed:.1f} m/s")
        
        # Update RSSI
        self.rssi_value.setText(f"{self.telemetry_model.rssi} dBm")
        self.rssi_full_label.setText(f"{self.telemetry_model.rssi} dBm")
        self.snr_label.setText(f"{self.telemetry_model.snr} dB")
        self.packets_label.setText(f"{self.telemetry_model.packets_received}")
        self.last_packet_label.setText(self.telemetry_model.last_packet_time)
        
        # Update status indicators
        self.sd_status.updateStatus(self.telemetry_model.sd_card_ok)
        self.led_status.updateStatus(self.telemetry_model.led_ok)
        self.actuator_status.updateStatus(self.telemetry_model.actuator_ok)
        self.source_status.updateStatus(self.telemetry_model.source_ok)
        self.gps_status.updateStatus(self.telemetry_model.gps_valid)
    
    def update_dynamic_displays(self):
        """Update displays that need constant updating"""
        # Update mission clock
        self.mission_elapsed += 0.1
        hours, rem = divmod(self.mission_elapsed, 3600)
        minutes, seconds = divmod(rem, 60)
        self.mission_clock_value.setText(f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}")
        
        # Update battery status (simulated)
        battery_level = 80 - (self.mission_elapsed / 3600) * 10  # Decrease 10% per hour
        battery_voltage = 3.7 - (self.mission_elapsed / 3600) * 0.1  # Decrease 0.1V per hour
        self.battery_progress.setValue(int(battery_level))
        self.battery_progress.setFormat(f"{int(battery_level)}% ({battery_voltage:.1f}V)")