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
        
        # Create event logger first before using it
        self.event_logger = EventLogger(6)
        
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
        top_row = QGridLayout()
        top_row.setSpacing(10)
        
        # Navigation Data Section (top left)
        self.create_navigation_group(top_row, 0, 0)
        
        # Flight Data Section (top right)
        self.create_flight_data_group(top_row, 0, 1)
        
        main_layout.addLayout(top_row)
        
        # === BOTTOM ROW ===
        bottom_row = QGridLayout()
        bottom_row.setSpacing(10)
        
        # Radio Status Section (bottom left)
        self.create_radio_status_group(bottom_row, 0, 0)
        
        # System Status Section (bottom right)
        self.create_system_status_group(bottom_row, 0, 1)
        
        main_layout.addLayout(bottom_row)
        
        # Create event log at the bottom
        bottom_section = QHBoxLayout()
        self.create_event_log_group(bottom_section)
        main_layout.addLayout(bottom_section)
    
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
        
        # Replace artificial horizon with attitude display
        attitude_frame = QFrame()
        attitude_frame.setFrameShape(QFrame.StyledPanel)
        attitude_frame.setFrameShadow(QFrame.Sunken)
        attitude_frame.setStyleSheet("background-color: #1a1a1a;")
        attitude_layout = QVBoxLayout(attitude_frame)
        
        # Add title
        attitude_title = QLabel("Attitude Data")
        attitude_title.setFont(QFont("Arial", 12, QFont.Bold))
        attitude_title.setAlignment(Qt.AlignCenter)
        attitude_layout.addWidget(attitude_title)
        
        # Add numeric attitude values in a grid
        values_layout = QGridLayout()
        values_layout.setSpacing(10)
        
        self.roll_value = self.add_digital_value(values_layout, "Roll", "0.0°", 0)
        self.pitch_value = self.add_digital_value(values_layout, "Pitch", "0.0°", 1)
        self.heading_value = self.add_digital_value(values_layout, "Heading", "0.0°", 2)
        
        attitude_layout.addLayout(values_layout)
        attitude_layout.addStretch()
        
        layout.addWidget(attitude_frame, 0, 1, 2, 1)
        
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
    
    def create_flight_data_group(self, parent_layout, row, col):
        """Create the flight data section (top right)"""
        group_box = QGroupBox("Flight Data")
        group_box.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                font-weight: bold;
                color: #00ff00;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        flight_layout = QGridLayout()
        
        # Define parameters to display
        flight_parameters = [
            ("Altitude", "m", 0, 0, "Current altitude above ground level"),
            ("Temperature", "°C", 0, 1, "Outside air temperature"),
            ("Pressure", "hPa", 1, 0, "Atmospheric pressure"),
            ("Vertical Speed", "m/s", 1, 1, "Current vertical velocity")
        ]
        
        # Add parameter displays
        for name, unit, row, col, tooltip in flight_parameters:
            frame = QFrame()
            frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            frame.setLineWidth(2)
            frame.setToolTip(tooltip)
            
            layout = QVBoxLayout(frame)
            layout.setSpacing(5)
            
            # Parameter name
            title = QLabel(name)
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("""
                font-weight: bold;
                font-size: 14px;
                color: #00ff00;
            """)
            layout.addWidget(title)
            
            # Value display
            value = QLabel("--")
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet("""
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                background-color: #2a2a2a;
                border-radius: 5px;
                padding: 5px;
            """)
            layout.addWidget(value)
            
            # Unit label
            if unit:
                unit_label = QLabel(unit)
                unit_label.setAlignment(Qt.AlignCenter)
                unit_label.setStyleSheet("color: #888888;")
                layout.addWidget(unit_label)
            
            flight_layout.addWidget(frame, row, col)
            
            # Store reference to the value label
            key = name.lower().replace(" ", "_")
            setattr(self, f"{key}_display", value)
        
        group_box.setLayout(flight_layout)
        parent_layout.addWidget(group_box, row, col)
    
    def create_navigation_group(self, parent_layout, row, col):
        """Create the navigation section (top left)"""
        group_box = QGroupBox("Navigation")
        group_box.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                font-weight: bold;
                color: #00ff00;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        nav_layout = QGridLayout()
        nav_layout.setSpacing(15)
        
        # Add digital clock at the top
        clock_frame = QFrame()
        clock_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        clock_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #2a2a2a;
            }
        """)
        clock_layout = QVBoxLayout(clock_frame)
        self.gps_clock = DigitalClockWidget()
        clock_layout.addWidget(self.gps_clock)
        nav_layout.addWidget(clock_frame, 0, 0, 1, 2)
        
        # Add compass widgets in a horizontal layout
        compass_layout = QHBoxLayout()
        
        # Vehicle heading compass
        compass_frame = QFrame()
        compass_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        compass_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #2a2a2a;
                padding: 5px;
            }
            QLabel {
                color: #00ff00;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        compass_layout_1 = QVBoxLayout(compass_frame)
        compass_layout_1.setSpacing(5)
        self.compass = CompassWidget()
        compass_label = QLabel("Vehicle Heading")
        compass_label.setAlignment(Qt.AlignCenter)
        compass_layout_1.addWidget(compass_label)
        compass_layout_1.addWidget(self.compass)
        
        # Target bearing compass
        target_frame = QFrame()
        target_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        target_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #2a2a2a;
                padding: 5px;
            }
            QLabel {
                color: #00ff00;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        compass_layout_2 = QVBoxLayout(target_frame)
        compass_layout_2.setSpacing(5)
        self.target_compass = CompassWidget()
        target_label = QLabel("Target Bearing")
        target_label.setAlignment(Qt.AlignCenter)
        compass_layout_2.addWidget(target_label)
        compass_layout_2.addWidget(self.target_compass)
        
        compass_layout.addWidget(compass_frame)
        compass_layout.addWidget(target_frame)
        nav_layout.addLayout(compass_layout, 1, 0, 2, 2)
        
        # Add speed dials in a frame
        dials_frame = QFrame()
        dials_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        dials_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background-color: #2a2a2a;
                padding: 5px;
            }
        """)
        speed_dials_layout = QHBoxLayout(dials_frame)
        speed_dials_layout.setSpacing(20)
        
        self.ground_speed_dial = SpeedDialWidget("Ground Speed", "m/s", max_value=50)
        self.ground_speed_dial.setMinimumSize(150, 150)
        self.vertical_speed_dial = SpeedDialWidget("Vertical Speed", "m/s", max_value=20)
        self.vertical_speed_dial.setMinimumSize(150, 150)
        
        speed_dials_layout.addWidget(self.ground_speed_dial, stretch=1)
        speed_dials_layout.addWidget(self.vertical_speed_dial, stretch=1)
        
        nav_layout.addWidget(dials_frame, 3, 0, 1, 2)
        
        group_box.setLayout(nav_layout)
        parent_layout.addWidget(group_box, row, col)
    
    def create_system_status_group(self, parent_layout, row, col):
        """Create the system status section (bottom right)"""
        group_box = QGroupBox("System Status")
        group_box.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                font-weight: bold;
                color: #00ff00;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        system_layout = QGridLayout()
        
        # Define parameters to display
        system_parameters = [
            ("SD Status", "", 0, 0, "SD Card Status"),
            ("LED Status", "", 0, 1, "LED Status"),
            ("Actuator Status", "", 1, 0, "Actuator System Status"),
            ("Source", "", 1, 1, "Source Status")
        ]
        
        # Add parameter displays
        for name, unit, row, col, tooltip in system_parameters:
            frame = QFrame()
            frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            frame.setLineWidth(2)
            frame.setToolTip(tooltip)
            
            layout = QVBoxLayout(frame)
            layout.setSpacing(5)
            
            # Parameter name
            title = QLabel(name)
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("""
                font-weight: bold;
                font-size: 14px;
                color: #00ff00;
            """)
            layout.addWidget(title)
            
            # Value display
            value = QLabel("--")
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet("""
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                background-color: #2a2a2a;
                border-radius: 5px;
                padding: 5px;
            """)
            layout.addWidget(value)
            
            # Unit label if provided
            if unit:
                unit_label = QLabel(unit)
                unit_label.setAlignment(Qt.AlignCenter)
                unit_label.setStyleSheet("color: #888888;")
                layout.addWidget(unit_label)
            
            system_layout.addWidget(frame, row, col)
            
            # Store reference to the value label
            key = name.lower().replace(" ", "_")
            setattr(self, f"{key}_display", value)
        
        group_box.setLayout(system_layout)
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
        group_box.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                font-weight: bold;
                color: #00ff00;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        layout = QVBoxLayout(group_box)
        
        # Use the existing event logger instead of creating a new one
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
    
    def add_large_value(self, parent_layout, label_text, initial_value, row):
        """Add a label with a larger value display below it"""
        container = QVBoxLayout()
        
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 10))
        
        value = QLabel(initial_value)
        value.setAlignment(Qt.AlignCenter)
        value.setStyleSheet("color: #00ff00; font-size: 18pt; font-weight: bold;")
        
        container.addWidget(label)
        container.addWidget(value)
        
        parent_layout.addLayout(container, row, 0)
        return value
    
    def add_digital_value(self, parent_layout, label_text, initial_value, row):
        """Add a label with a digital-looking value display below it"""
        container = QVBoxLayout()
        
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 10))
        
        value = QLabel(initial_value)
        value.setAlignment(Qt.AlignCenter)
        value.setStyleSheet("""
            color: #00ff00; 
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 22pt; 
            font-weight: bold;
            background-color: #121212;
            border: 1px solid #333333;
            border-radius: 4px;
            padding: 3px 8px;
            letter-spacing: 1px;
        """)
        
        container.addWidget(label)
        container.addWidget(value)
        
        parent_layout.addLayout(container, row, 0)
        return value
    
    def update_telemetry_display(self):
        """Update all telemetry displays with current data"""
        # Update speed dials
        self.ground_speed_dial.setValue(self.telemetry_model.ground_speed)
        self.vertical_speed_dial.setValue(self.telemetry_model.vertical_speed)
        
        # Update compass
        self.compass.setBearing(self.telemetry_model.yaw)
        
        # Update GPS time
        if self.telemetry_model.gps_time:
            self.gps_clock.setTime(self.telemetry_model.gps_time)
        
        # Update flight data
        self.altitude_display.setText(f"{self.telemetry_model.altitude:.1f}")
        self.temperature_display.setText(f"{self.telemetry_model.temperature:.1f}")
        self.pressure_display.setText(f"{self.telemetry_model.pressure:.1f}")
        self.vertical_speed_display.setText(f"{self.telemetry_model.vertical_speed:.1f}")
        
        # Update radio status
        self.rssi_display.setText(f"{self.telemetry_model.rssi}")
        self.snr_display.setText(f"{self.telemetry_model.snr}")
        self.ack_display.setText("Received" if self.telemetry_model.ack_received else "No ACK")
        self.gps_display.setText("Fix" if self.telemetry_model.gps_valid else "No Fix")
        
        # Update system status
        self.sd_status_display.setText("Active" if self.telemetry_model.sd_card_ok else "Inactive")
        self.led_status_display.setText("Active" if self.telemetry_model.led_ok else "Inactive")
        self.actuator_status_display.setText("Active" if self.telemetry_model.actuator_ok else "Inactive")
        self.source_display.setText("Active" if self.telemetry_model.source_ok else "Inactive")
        
        # Update target bearing if we have both user location and vehicle location
        if hasattr(self, 'user_lat') and hasattr(self, 'user_lon') and self.telemetry_model.gps_valid:
            bearing = self.calculate_target_bearing(
                self.user_lat, self.user_lon, 
                self.telemetry_model.gps_lat, self.telemetry_model.gps_lon
            )
            self.target_compass.setBearing(bearing)
    
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
    
    def create_radio_status_group(self, parent_layout, row, col):
        """Create the radio status section (bottom left)"""
        group_box = QGroupBox("Radio Status")
        group_box.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                font-weight: bold;
                color: #00ff00;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        radio_layout = QGridLayout()
        
        # Define parameters to display
        radio_parameters = [
            ("RSSI", "dBm", 0, 0, "Received Signal Strength Indicator"),
            ("SNR", "dB", 0, 1, "Signal-to-Noise Ratio"),
            ("ACK", "", 1, 0, "Packet Acknowledgement Status"),
            ("GPS", "", 1, 1, "GPS Fix Status")
        ]
        
        # Add parameter displays
        for name, unit, row, col, tooltip in radio_parameters:
            frame = QFrame()
            frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            frame.setLineWidth(2)
            frame.setToolTip(tooltip)
            
            layout = QVBoxLayout(frame)
            layout.setSpacing(5)
            
            # Parameter name
            title = QLabel(name)
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("""
                font-weight: bold;
                font-size: 14px;
                color: #00ff00;
            """)
            layout.addWidget(title)
            
            # Value display
            value = QLabel("--")
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet("""
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                background-color: #2a2a2a;
                border-radius: 5px;
                padding: 5px;
            """)
            layout.addWidget(value)
            
            # Unit label
            if unit:
                unit_label = QLabel(unit)
                unit_label.setAlignment(Qt.AlignCenter)
                unit_label.setStyleSheet("color: #888888;")
                layout.addWidget(unit_label)
            
            radio_layout.addWidget(frame, row, col)
            
            # Store reference to the value label
            key = name.lower().replace(" ", "_")
            setattr(self, f"{key}_display", value)
        
        # Add packet interval display if needed
        # self.last_packet_label = QLabel("Packet Interval: --")
        # self.last_packet_label.setStyleSheet(...)
        # radio_layout.addWidget(self.last_packet_label, 2, 0, 1, 2)
        
        group_box.setLayout(radio_layout)
        parent_layout.addWidget(group_box, row, col)
