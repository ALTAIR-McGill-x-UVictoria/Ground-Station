import sys
import serial
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer, Qt, QUrl, QPoint, QRectF  # Add QPoint here
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import (
    QPalette, QColor, QTextCursor, QPainter, QBrush, 
    QPen, QFont
)
import pyqtgraph as pg
from datetime import datetime
import queue
import threading
import os
import random
from math import sin, cos, radians, atan2, degrees

# Add these imports at the top of the file
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PyQt5.QtCore import Qt, QRectF

class GroundStationGUI(QMainWindow):
    MAP_HTML = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <style>
            #map {
                height: 100vh;
                width: 100%;
            }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([0, 0], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
            
            var marker = L.marker([0, 0]).addTo(map);
            var pathLine = L.polyline([], {
                color: 'red',
                weight: 3,
                opacity: 0.7
            }).addTo(map);
            
            var followMarker = true;
            var coordinates = [];
            
            function updateMarker(lat, lon) {
                marker.setLatLng([lat, lon]);
                coordinates.push([lat, lon]);
                pathLine.setLatLngs(coordinates);
                
                if (followMarker) {
                    map.setView([lat, lon]);
                }
            }
            
            function setFollowMarker(follow) {
                followMarker = follow;
            }
            
            function clearPath() {
                coordinates = [];
                pathLine.setLatLngs([]);
            }
        </script>
    </body>
    </html>
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HAB Ground Station")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize serial connection
        self.serial_queue = queue.Queue()
        self.serial_port = None
        
        # Initialize status widgets dictionary
        self.status_widgets = {}  # Add this line
        
        # Setup UI
        self.setup_ui()
        
        # Setup data storage
        self.altitude_data = []
        self.time_data = []
        self.temperature_data = []
        self.pressure_data = []
        self.rssi_data = []
        self.snr_data = []
        self.ack_data = []

        # Add these lines after other initializations
        self.log_file = None
        self.is_logging = False
        
        # Setup update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(100)  # Update every 100ms

        # Check command line arguments for auto-connect
        for arg in sys.argv:
            if arg.upper().startswith('COM'):
                # Set the port selector to the specified COM port
                self.port_selector.setCurrentText(arg.upper())
                # Create a timer to connect after GUI is shown
                QTimer.singleShot(500, self.auto_connect)
                break

        self.gps_simulation = False
        self.sim_lat = 45.493643
        self.sim_lon = -73.583182
        self.sim_angle = 0
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.update_sim_gps)
        
        # Check if GPS simulation is enabled via command line
        if len(sys.argv) > 1 and sys.argv[1].lower() == 'testgps':
            self.gps_simulation = True
            self.sim_timer.start(1000)  # Update every second

        self.last_gps_lat = None
        self.last_gps_lon = None

    def setup_ui(self):
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)  # Changed to horizontal layout
        
        # Create left side layout for existing content
        left_layout = QVBoxLayout()
        
        # Create toolbar for controls
        toolbar = QHBoxLayout()
        
        # Serial port selection
        self.port_selector = QComboBox()
        self.refresh_ports()
        toolbar.addWidget(QLabel("Port:"))
        toolbar.addWidget(self.port_selector)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        toolbar.addWidget(self.connect_button)
        
        # Add toolbar to main layout
        left_layout.addLayout(toolbar)

        # Create tab widget
        self.tab_widget = QTabWidget()
        left_layout.addWidget(self.tab_widget)
        
        # Plots tab
        plots_tab = QWidget()
        plots_layout = QVBoxLayout(plots_tab)
        
        # Add plot selector
        plot_selector = QComboBox()
        plot_selector.addItems([
            "Flight Data",
            "Signal Strength",
            "All Plots"
        ])
        plot_selector.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                min-width: 150px;
            }
        """)
        plot_selector.currentIndexChanged.connect(self.switch_plot_view)
        plots_layout.addWidget(plot_selector)
        
        # Create stacked widget for different plot pages
        self.plot_stack = QStackedWidget()
        plots_layout.addWidget(self.plot_stack)
        
        # Flight Data page (GPS altitude, speeds, temp/pressure)
        flight_page = QWidget()
        flight_layout = QGridLayout(flight_page)
        
        # Altitude plot (top left)
        self.altitude_plot = pg.PlotWidget(title="GPS Altitude")
        self.altitude_plot.setLabel('left', 'Altitude', units='m')
        self.altitude_plot.setLabel('bottom', 'Time', units='s')
        self.altitude_plot.showGrid(x=True, y=True)
        flight_layout.addWidget(self.altitude_plot, 0, 0)
        
        # Speed plot (top right)
        self.speed_plot = pg.PlotWidget(title="Speed")
        self.speed_plot.setLabel('left', 'Speed', units='m/s')
        self.speed_plot.setLabel('bottom', 'Time', units='s')
        self.speed_plot.showGrid(x=True, y=True)
        self.speed_plot.addLegend()
        flight_layout.addWidget(self.speed_plot, 0, 1)
        
        # Temperature & Pressure plot (bottom)
        self.temp_press_plot = pg.PlotWidget(title="Temperature & Pressure")
        self.temp_press_plot.setLabel('left', 'Temperature', units='°C')
        self.temp_press_plot.setLabel('right', 'Pressure', units='hPa')
        self.temp_press_plot.setLabel('bottom', 'Time', units='s')
        self.temp_press_plot.showGrid(x=True, y=True)
        self.temp_press_plot.addLegend()
        flight_layout.addWidget(self.temp_press_plot, 1, 0, 1, 2)  # Span two columns
        
        # Signal Strength page
        signal_page = QWidget()
        signal_layout = QVBoxLayout(signal_page)
        
        self.signal_plot = pg.PlotWidget(title="Signal Strength")
        self.signal_plot.setLabel('left', 'Level')
        self.signal_plot.setLabel('bottom', 'Time', units='s')
        self.signal_plot.showGrid(x=True, y=True)
        self.signal_plot.addLegend()
        signal_layout.addWidget(self.signal_plot)
        
        # Signal Strength page
        signal_page = QWidget()
        signal_layout = QGridLayout(signal_page)
        
        self.signal_plot = pg.PlotWidget(title="Signal Strength")
        self.signal_plot.setLabel('left', 'Level')
        self.signal_plot.setLabel('bottom', 'Time', units='s')
        self.signal_plot.showGrid(x=True, y=True)
        self.signal_plot.addLegend()
        signal_layout.addWidget(self.signal_plot, 0, 0)
        
        self.temp_press_plot = pg.PlotWidget(title="Temperature & Pressure")
        self.temp_press_plot.setLabel('left', 'Temperature', units='°C')
        self.temp_press_plot.setLabel('right', 'Pressure', units='hPa')
        self.temp_press_plot.setLabel('bottom', 'Time', units='s')
        self.temp_press_plot.showGrid(x=True, y=True)
        self.temp_press_plot.addLegend()
        signal_layout.addWidget(self.temp_press_plot, 0, 1)
        
        # All Plots page
        all_plots_page = QWidget()
        all_layout = QGridLayout(all_plots_page)
        
        # Create new plot widgets for the all plots view
        altitude_plot_all = pg.PlotWidget(title="GPS Altitude")
        altitude_plot_all.setLabel('left', 'Altitude', units='m')
        altitude_plot_all.setLabel('bottom', 'Time', units='s')
        altitude_plot_all.showGrid(x=True, y=True)
        
        speed_plot_all = pg.PlotWidget(title="Speed")
        speed_plot_all.setLabel('left', 'Speed', units='m/s')
        speed_plot_all.setLabel('bottom', 'Time', units='s')
        speed_plot_all.showGrid(x=True, y=True)
        speed_plot_all.addLegend()
        
        signal_plot_all = pg.PlotWidget(title="Signal Strength")
        signal_plot_all.setLabel('left', 'Level')
        signal_plot_all.setLabel('bottom', 'Time', units='s')
        signal_plot_all.showGrid(x=True, y=True)
        signal_plot_all.addLegend()
        
        temp_press_plot_all = pg.PlotWidget(title="Temperature & Pressure")
        temp_press_plot_all.setLabel('left', 'Temperature', units='°C')
        temp_press_plot_all.setLabel('right', 'Pressure', units='hPa')
        temp_press_plot_all.setLabel('bottom', 'Time', units='s')
        temp_press_plot_all.showGrid(x=True, y=True)
        temp_press_plot_all.addLegend()
        
        # Add plots to layout
        all_layout.addWidget(altitude_plot_all, 0, 0)
        all_layout.addWidget(speed_plot_all, 0, 1)
        all_layout.addWidget(signal_plot_all, 1, 0)
        all_layout.addWidget(temp_press_plot_all, 1, 1)
        
        # Create curves for the all plots view
        self.altitude_curve_all = altitude_plot_all.plot(pen='g')
        self.speed_h_curve_all = speed_plot_all.plot(pen='y', name='Ground Speed')
        self.speed_v_curve_all = speed_plot_all.plot(pen='c', name='Vertical Speed')
        self.rssi_curve_all = signal_plot_all.plot(pen='r', name='RSSI')
        self.snr_curve_all = signal_plot_all.plot(pen='b', name='SNR')
        self.temp_curve_all = temp_press_plot_all.plot(pen='r', name='Temperature')
        self.press_curve_all = temp_press_plot_all.plot(pen='b', name='Pressure')
        
        # Add pages to stack
        self.plot_stack.addWidget(flight_page)
        self.plot_stack.addWidget(signal_page)
        self.plot_stack.addWidget(all_plots_page)
        
        # Initialize plot data
        self.speed_h_curve = self.speed_plot.plot(pen='y', name='Ground Speed')
        self.speed_v_curve = self.speed_plot.plot(pen='c', name='Vertical Speed')
        self.altitude_curve = self.altitude_plot.plot(pen='g')
        self.rssi_curve = self.signal_plot.plot(pen='r', name='RSSI')
        self.snr_curve = self.signal_plot.plot(pen='b', name='SNR')
        self.temp_curve = self.temp_press_plot.plot(pen='r', name='Temperature')
        self.press_curve = self.temp_press_plot.plot(pen='b', name='Pressure')
        
        plots_tab.setLayout(plots_layout)
        self.tab_widget.addTab(plots_tab, "Plots")
        
        # Create dashboard tab
        dashboard_tab = QWidget()
        dashboard_layout = QGridLayout(dashboard_tab)
        dashboard_layout.setSpacing(10)
        
        # Navigation Data Section (now top left)
        nav_group = QGroupBox("Navigation")
        nav_layout = QGridLayout()
        nav_layout.setSpacing(15)
        
        # Add digital clock at the top
        self.gps_clock = DigitalClockWidget()
        nav_layout.addWidget(self.gps_clock, 0, 0, 1, 2)
        
        # Add compass widget
        self.compass = CompassWidget()
        nav_layout.addWidget(self.compass, 1, 0, 2, 2)
        
        # Add speed dials
        speed_dials_layout = QHBoxLayout()
        speed_dials_layout.setSpacing(20)  # Add more spacing between dials
        
        # Create larger speed dials with increased minimum size
        self.ground_speed_dial = SpeedDialWidget("Ground Speed", "m/s", max_value=50)
        self.ground_speed_dial.setMinimumSize(150, 150)  # Increased from 100x100
        self.vertical_speed_dial = SpeedDialWidget("Vertical Speed", "m/s", max_value=20)
        self.vertical_speed_dial.setMinimumSize(150, 150)  # Increased from 100x100
        
        # Add dials to layout with stretch factors
        speed_dials_layout.addWidget(self.ground_speed_dial, stretch=1)
        speed_dials_layout.addWidget(self.vertical_speed_dial, stretch=1)
        
        nav_layout.addLayout(speed_dials_layout, 3, 0, 1, 2)
        
        # Add bearing display
        bearing_label = QLabel("Bearing")
        bearing_label.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        bearing_label.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(bearing_label, 4, 0, 1, 2)
        
        # Initialize bearing value display
        self.bearing_value = QLabel("--°")
        self.bearing_value.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        self.bearing_value.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(self.bearing_value, 5, 0, 1, 2)
        
        nav_group.setLayout(nav_layout)
        dashboard_layout.addWidget(nav_group, 0, 0)  # Move to top left
        
        # Flight Data Section (now top right)
        flight_group = QGroupBox("Flight Data")
        flight_layout = QGridLayout()
        flight_parameters = [
            ("Altitude", "m", 0, 0, "Current altitude above ground level"),
            ("Temperature", "°C", 0, 1, "Outside air temperature"),
            ("Pressure", "hPa", 1, 0, "Atmospheric pressure"),
            ("Vertical Speed", "m/s", 1, 1, "Current vertical velocity")
        ]
        self.add_parameters_to_layout(flight_parameters, flight_layout)
        flight_group.setLayout(flight_layout)
        dashboard_layout.addWidget(flight_group, 0, 1)  # Move to top right
        
        # Radio Status Section (now bottom left)
        radio_group = QGroupBox("Radio Status")
        radio_layout = QGridLayout()
        radio_parameters = [
            ("RSSI", "dBm", 0, 0, "Received Signal Strength Indicator"),
            ("SNR", "dB", 0, 1, "Signal-to-Noise Ratio"),
            ("ACK", "", 1, 0, "Packet Acknowledgement Status"),
            ("Connection", "", 1, 1, "Radio Link Status")
        ]
        self.add_parameters_to_layout(radio_parameters, radio_layout)
        radio_group.setLayout(radio_layout)
        dashboard_layout.addWidget(radio_group, 1, 0)  # Move to bottom left
        
        # System Status Section (now bottom right)
        system_group = QGroupBox("System Status")
        system_layout = QGridLayout()
        system_parameters = [
            ("SDStatus", "", 0, 0, "SD Card Status"),
            ("GPS", "", 0, 1, "GPS Fix Status"),
            ("ActuatorStatus", "", 1, 0, "Actuator System Status")
        ]
        self.add_parameters_to_layout(system_parameters, system_layout)
        
        # Add packet interval label
        self.last_packet_label = QLabel("Packet Interval: --")
        self.last_packet_label.setStyleSheet("""
            QLabel {
                color: #ff0000;
                font-family: 'Courier New';
                font-size: 12px;
                padding: 5px;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2a2a2a;
            }
        """)
        system_layout.addWidget(self.last_packet_label, 2, 0, 1, 2)
        
        system_group.setLayout(system_layout)
        dashboard_layout.addWidget(system_group, 1, 1)  # Move to bottom right
        
        # Add tabs to tab widget
        self.tab_widget.addTab(dashboard_tab, "Dashboard")
        
        
        # Add raw data section with title
        raw_data_group = QGroupBox("Raw Serial Data")
        raw_data_layout = QVBoxLayout()
        
        # Create raw data display
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00;
                font-family: 'Courier New';
                font-size: 12px;
            }
        """)
        self.data_display.setMinimumHeight(100)  # Set minimum height
        raw_data_layout.addWidget(self.data_display)
        
        # Add button layout
        button_layout = QHBoxLayout()
        
        # Add clear button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.data_display.clear)
        button_layout.addWidget(clear_button)
        
        # Add log button
        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self.toggle_logging)
        button_layout.addWidget(self.log_button)
        
        raw_data_layout.addLayout(button_layout)
        
        raw_data_group.setLayout(raw_data_layout)
        left_layout.addWidget(raw_data_group)

        # Create map tab
        map_tab = QWidget()
        map_layout = QVBoxLayout(map_tab)
        
        # Add map controls
        map_controls = QHBoxLayout()
        
        # Create left side controls for GPS info
        left_controls = QHBoxLayout()  # Changed to QHBoxLayout
        
        # Add GPS coordinates label first
        self.gps_label = QLabel("GPS: No Fix")
        self.gps_label.setStyleSheet("""
            QLabel {
                background-color: #2a2a2a;
                color: #ff6b6b;
                padding: 8px 12px;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-family: 'Courier New';
                font-size: 12px;
                font-weight: bold;
                min-width: 300px;
            }
        """)
        left_controls.addWidget(self.gps_label)
        
        # Add small spacing between coordinates and button
        left_controls.addSpacing(10)
        
        # Add Google Maps button on the right of coordinates
        self.google_maps_btn = QPushButton("Open in Maps")
        self.google_maps_btn.setEnabled(False)
        self.google_maps_btn.clicked.connect(self.open_google_maps)
        self.google_maps_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                padding: 5px 10px;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666666;
            }
        """)
        left_controls.addWidget(self.google_maps_btn)
        
        map_controls.addLayout(left_controls)
        map_controls.addStretch()
        
        # Add existing controls on the right
        self.follow_marker = QCheckBox("Lock on GPS")
        self.follow_marker.setChecked(True)
        self.follow_marker.stateChanged.connect(self.toggle_map_follow)
        map_controls.addWidget(self.follow_marker)
        
        map_controls.addStretch()
        map_layout.addLayout(map_controls)
        
        # Create web view for map
        self.map_view = QWebEngineView()
        self.map_view.setHtml(self.MAP_HTML)
        map_layout.addWidget(self.map_view)
        
        # Add map tab
        self.tab_widget.addTab(map_tab, "Map")

        # Create command panel on right side
        command_panel = QGroupBox("Command Panel")
        command_layout = QVBoxLayout()
        
        # SD Card Control
        sd_group = QGroupBox("SD Card Control")
        sd_layout = QVBoxLayout()
        sd_activate = QPushButton("Activate SD Card")
        sd_activate.clicked.connect(lambda: self.send_command("SD_ACTIVATE"))
        sd_layout.addWidget(sd_activate)
        sd_group.setLayout(sd_layout)
        command_layout.addWidget(sd_group)
        
        # LED Control
        led_group = QGroupBox("LED Control")
        led_layout = QVBoxLayout()
        
        # LED Intensity Control
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(QLabel("Intensity:"))
        self.led_intensity = QSpinBox()
        self.led_intensity.setRange(0, 255)
        intensity_layout.addWidget(self.led_intensity)
        led_activate = QPushButton("Set LED")
        led_activate.clicked.connect(self.send_led_command)
        intensity_layout.addWidget(led_activate)
        led_layout.addLayout(intensity_layout)
        
        # LED Blink Control
        blink_layout = QHBoxLayout()
        blink_layout.addWidget(QLabel("Delay (ms):"))
        self.blink_delay = QSpinBox()
        self.blink_delay.setRange(100, 2000)
        self.blink_delay.setSingleStep(100)
        self.blink_delay.setValue(500)
        blink_layout.addWidget(self.blink_delay)
        blink_activate = QPushButton("Blink LED")
        blink_activate.clicked.connect(self.send_blink_command)
        blink_layout.addWidget(blink_activate)
        led_layout.addLayout(blink_layout)
        
        led_group.setLayout(led_layout)
        command_layout.addWidget(led_group)
        
        # Ping Control
        ping_group = QGroupBox("System Control")
        ping_layout = QVBoxLayout()
        ping_button = QPushButton("Ping")
        ping_button.clicked.connect(lambda: self.send_command("ping"))
        ping_layout.addWidget(ping_button)
        ping_group.setLayout(ping_layout)
        command_layout.addWidget(ping_group)
        
        # Add stretch to push widgets to top
        command_layout.addStretch()
        
        command_panel.setLayout(command_layout)
        command_panel.setFixedWidth(250)  # Set fixed width for command panel
        
        # Add layouts to main layout
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addWidget(command_panel)

    def add_parameters_to_layout(self, parameters, parent_layout):
        for name, unit, row, col, tooltip in parameters:
            frame = QFrame()
            frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            frame.setLineWidth(2)
            frame.setToolTip(tooltip)
            
            layout = QVBoxLayout(frame)
            layout.setSpacing(5)
            
            # Parameter name with icon
            header = QHBoxLayout()
            title = QLabel(name)
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("""
                font-weight: bold;
                font-size: 14px;
                color: #00ff00;
            """)
            header.addWidget(title)
            layout.addLayout(header)
            
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
            
            parent_layout.addWidget(frame, row, col)
            self.status_widgets[name.lower()] = value

    def refresh_ports(self):
        import serial.tools.list_ports
        self.port_selector.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_selector.addItems(ports)

    def toggle_connection(self):
        """Toggle serial connection state."""
        if self.serial_port is None:
            try:
                port = self.port_selector.currentText()
                self.serial_port = serial.Serial(port, 115200, timeout=1)
                self.connect_button.setText("Disconnect")
                self.port_selector.setEnabled(False)
                
                # Start serial reading thread
                self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
                self.serial_thread.start()
                
                # Log connection
                self.update_status(f"Connected to {port}")
                
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", f"Could not open port: {str(e)}")
                self.serial_port = None
        else:
            try:
                self.serial_port.close()
            except:
                pass
            self.serial_port = None
            self.connect_button.setText("Connect")
            self.port_selector.setEnabled(True)
            self.update_status("Disconnected")

    def read_serial(self):
        while self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline()
                    # Try to decode as utf-8, skip if not valid
                    try:
                        decoded_line = line.decode('utf-8').strip()
                        # Check if line contains mostly printable ASCII characters
                        if any(ord(c) < 32 or ord(c) > 126 for c in decoded_line):
                            continue
                        # Only process lines that contain comma-separated values
                        if ',' in decoded_line:
                            self.serial_queue.put(decoded_line)
                    except UnicodeDecodeError:
                        continue
            except:
                break

    def update_plots(self):
        while not self.serial_queue.empty():
            try:
                line = self.serial_queue.get_nowait()
                
                # Log raw data to file if logging is enabled
                if self.is_logging and self.log_file:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    self.log_file.write(f"[{timestamp}] {line}\n")
                    self.log_file.flush()
                
                # Add to raw data display
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                self.data_display.append(f"[{timestamp}] {line}")
                
                # Split line into values
                values = line.strip().split(',')
                
                # Parse RSSI/SNR/Delta update (3 values)
                if len(values) == 3:
                    try:
                        rssi = float(values[0])
                        snr = float(values[1])
                        delta = float(values[2])
                        
                        # Update status widgets
                        self.update_parameter('rssi', rssi)
                        self.update_parameter('snr', snr)
                        
                    except ValueError:
                        print(f"Error parsing RSSI/SNR/Delta values: {line}")
                        
                # Process main telemetry packet (18 values)
                elif len(values) == 18:
                    try:
                        # Keep only the last 100 lines in raw data display
                        doc = self.data_display.document()
                        while doc.blockCount() > 100:
                            cursor = QTextCursor(doc.firstBlock())
                            cursor.select(QTextCursor.BlockUnderCursor)
                            cursor.removeSelectedText()
                            cursor.deleteChar()
                    
                        # Calculate vertical speed
                        vertical_speed = 0
                        if len(self.altitude_data) >= 2:
                            time_diff = self.time_data[-1] - self.time_data[-2]
                            if time_diff > 0:
                                vertical_speed = (self.altitude_data[-1] - self.altitude_data[-2]) / time_diff
                        
                        # Store new data points
                        current_time = (time.time() - self.start_time) if hasattr(self, 'start_time') else 0
                        self.ground_speed_data.append(gps_speed)
                        self.vertical_speed_data.append(vertical_speed)
                        self.gps_altitude_data.append(gps_alt)
                        self.rssi_data.append(rssi)
                        self.snr_data.append(snr)
                        
                        # Update plots in both views
                        self.speed_h_curve.setData(self.time_data, self.ground_speed_data)
                        self.speed_v_curve.setData(self.time_data, self.vertical_speed_data)
                        self.altitude_curve.setData(self.time_data, self.gps_altitude_data)
                        self.rssi_curve.setData(self.time_data, self.rssi_data)
                        self.snr_curve.setData(self.time_data, self.snr_data)
                        
                        # Update all plots view
                        self.speed_h_curve_all.setData(self.time_data, self.ground_speed_data)
                        self.speed_v_curve_all.setData(self.time_data, self.vertical_speed_data)
                        self.altitude_curve_all.setData(self.time_data, self.gps_altitude_data)
                        self.rssi_curve_all.setData(self.time_data, self.rssi_data)
                        self.snr_curve_all.setData(self.time_data, self.snr_data)
                        
                        # Trim data arrays if they get too long
                        max_points = 100
                        if len(self.time_data) > max_points:
                            self.time_data = self.time_data[-max_points:]
                            self.ground_speed_data = self.ground_speed_data[-max_points:]
                            self.vertical_speed_data = self.vertical_speed_data[-max_points:]
                            self.gps_altitude_data = self.gps_altitude_data[-max_points:]
                            self.rssi_data = self.rssi_data[-max_points:]
                            self.snr_data = self.snr_data[-max_points:]
                    except Exception as e:
                        print(f"Error processing telemetry packet: {str(e)}")
                        
            except Exception as e:
                print(f"Error processing data: {str(e)}")

    def update_parameter(self, name, value, format_str="{:.1f}"):
        if name.lower() in self.status_widgets:
            widget = self.status_widgets[name.lower()]
            formatted_value = format_str.format(value)
            widget.setText(formatted_value)
            
            # Add visual feedback based on value ranges
            if name.lower() == "rssi":
                if value > -70:
                    widget.setStyleSheet("font-size: 24px; color: #00ff00;")  # Good signal
                elif value > -90:
                    widget.setStyleSheet("font-size: 24px; color: #ffff00;")  # Medium signal
                else:
                    widget.setStyleSheet("font-size: 24px; color: #ff0000;")  # Poor signal

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate bearing between two points using GPS coordinates."""
        try:
            # Convert to radians
            lat1 = radians(float(lat1))
            lon1 = radians(float(lon1))
            lat2 = radians(float(lat2))
            lon2 = radians(float(lon2))
            
            # Calculate bearing using Great Circle formula
            d_lon = lon2 - lon1
            x = sin(d_lon) * cos(lat2)
            y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(d_lon)
            
            initial_bearing = atan2(x, y)
            
            # Convert to degrees and normalize
            initial_bearing = degrees(initial_bearing)
            compass_bearing = (initial_bearing + 360) % 360
            
            return compass_bearing
        except Exception as e:
            print(f"Error calculating bearing: {str(e)}")
            return 0.0

    def update_map_marker(self, lat, lon, alt=0):
        """Update map marker position and bearing calculation."""
        if (lat != 0 and lon != 0):  # Only update if we have valid coordinates
            # Calculate bearing if we have previous coordinates
            if self.last_gps_lat is not None and self.last_gps_lon is not None:
                # Only calculate new bearing if we've moved more than a minimal distance
                min_distance = 0.0001  # About 10 meters
                if abs(lat - self.last_gps_lat) > min_distance or abs(lon - self.last_gps_lon) > min_distance:
                    bearing = self.calculate_bearing(self.last_gps_lat, self.last_gps_lon, lat, lon)
                    self.compass.setBearing(bearing)
                    self.bearing_value.setText(f"{bearing:.1f}°")
            
            # Store current coordinates for next calculation
            self.last_gps_lat = lat
            self.last_gps_lon = lon
            
            # Update map marker
            js_code = f"updateMarker({lat}, {lon});"
            self.map_view.page().runJavaScript(js_code)
            
            # Update GPS label
            lat_direction = "N" if lat >= 0 else "S"
            lon_direction = "E" if lon >= 0 else "W"
            coord_text = (
                f"Lat: {abs(lat):.6f}° {lat_direction}  •  "
                f"Lon: {abs(lon):.6f}° {lon_direction}\n"
                f"Altitude: {alt:.1f} m MSL"
            )
            self.gps_label.setText(coord_text)
            self.gps_label.setStyleSheet("""
                QLabel {
                    background-color: #2a2a2a;
                    color: #00ff00;
                    padding: 8px 12px;
                    border: 1px solid #3a3a3a;
                    border-radius: 6px;
                    font-family: 'Courier New';
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            self.google_maps_btn.setEnabled(True)
            
        else:
            self.gps_label.setText("GPS: Waiting for fix...")
            self.gps_label.setStyleSheet("""
                QLabel {
                    background-color: #3a2a2a;
                    color: #ff6b6b;
                    padding: 8px 12px;
                    border: 1px solid #4a3a3a;
                    border-radius: 6px;
                    font-family: 'Courier New';
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            self.google_maps_btn.setEnabled(False)

    def send_command(self, command):
        """Send a generic command over serial."""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(f"{command}\n".encode())
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                self.data_display.append(f"[{timestamp}] Sent: {command}")
            except Exception as e:
                self.data_display.append(f"Error sending command: {str(e)}")
                print(f"Error sending command: {str(e)}")

    def send_led_command(self):
        """Send LED intensity command."""
        try:
            intensity = self.led_intensity.value()
            self.send_command(f"LED_SET {intensity}")
        except Exception as e:
            print(f"Error sending LED command: {str(e)}")

    def send_blink_command(self):
        """Send LED blink command."""
        try:
            delay = self.blink_delay.value()
            self.send_command(f"LED_BLINK {delay}")
        except Exception as e:
            print(f"Error sending blink command: {str(e)}")

    def update_status(self, message):
        """Update status display with timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        self.data_display.append(f"[{timestamp}] {message}")

    def toggle_logging(self):
        """Toggle serial data logging to file."""
        if not self.is_logging:
            try:
                # Create logs directory if it doesn't exist
                path = "logs"
                if not os.path.exists(path):
                    os.makedirs(path)
                
                # Create filename with human-readable timestamp
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                filename = f"{path}/flight_log_{timestamp}.txt"
                
                self.log_file = open(filename, 'w')
                self.log_file.write(f"HAB Ground Station Log\n")
                self.log_file.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.log_file.write(f"----------------------------------------\n\n")
                
                self.is_logging = True
                self.log_button.setText("Stop Logging")
                self.data_display.append(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Started logging to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Logging Error", f"Could not create log file: {str(e)}")
        else:
            if self.log_file:
                self.log_file.write(f"\n----------------------------------------\n")
                self.log_file.write(f"Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.log_file.close()
                self.log_file = None
            self.is_logging = False
            self.log_button.setText("Start Logging")
            self.data_display.append(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Stopped logging")

    def update_sim_gps(self):
        """Simulate GPS movement in a random path."""
        if not self.gps_simulation:
            return
            
        # Store previous position for bearing calculation
        prev_lat = self.sim_lat
        prev_lon = self.sim_lon
        
        # Randomly adjust direction (-30 to +30 degrees)
        self.sim_angle += random.uniform(-30, 30)
        
        # Calculate new position based on angle
        lat_change = cos(radians(self.sim_angle)) * 0.001
        lon_change = sin(radians(self.sim_angle)) * 0.001
        
        self.sim_lat += lat_change
        self.sim_lon += lon_change
        
        # Calculate actual bearing from position change
        if prev_lat != self.sim_lat or prev_lon != self.sim_lon:  # Only update if position changed
            bearing = self.calculate_bearing(prev_lat, prev_lon, self.sim_lat, self.sim_lon)
            # Update compass widget and bearing display
            self.compass.setBearing(bearing)
            self.bearing_value.setText(f"{bearing:.1f}°")
        
        # Simulate ground speed (5-15 m/s)
        ground_speed = random.uniform(5, 15)
        
        # Simulate altitude changes
        if not hasattr(self, 'sim_alt'):
            self.sim_alt = 100  # Initial altitude
            self.sim_vertical_speed = random.uniform(-2, 2)  # Initial vertical speed
        
        # Update vertical speed with small random changes
        self.sim_vertical_speed += random.uniform(-0.5, 0.5)
        # Clamp vertical speed between -5 and 5 m/s
        self.sim_vertical_speed = max(-5, min(5, self.sim_vertical_speed))
        
        # Update altitude based on vertical speed
        self.sim_alt += self.sim_vertical_speed
        # Keep altitude between 50 and 500 meters
        if self.sim_alt < 50 or self.sim_alt > 500:
            self.sim_vertical_speed *= -0.5  # Reverse direction when hitting limits
        
        # Update map marker with simulated values
        self.update_map_marker(self.sim_lat, self.sim_lon, self.sim_alt)
        
        # Update speed dials
        self.ground_speed_dial.setValue(ground_speed)
        self.vertical_speed_dial.setValue(self.sim_vertical_speed)
        
        # Add to data display
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        self.data_display.append(
            f"[{timestamp}] Sim GPS: {self.sim_lat:.6f}, {self.sim_lon:.6f}, "
            f"Alt: {self.sim_alt:.1f}m, GS: {ground_speed:.1f}m/s, VS: {self.sim_vertical_speed:.1f}m/s"
        )
        
        # Log if enabled
        if self.is_logging and self.log_file:
            self.log_file.write(
                f"[{timestamp}] Simulated GPS: {self.sim_lat:.6f}, {self.sim_lon:.6f}, "
                f"Alt: {self.sim_alt:.1f}m, GS: {ground_speed:.1f}m/s, VS: {self.sim_vertical_speed:.1f}m/s\n"
            )
            self.log_file.flush()

        # Simulate GPS time (seconds since midnight)
        current_time = datetime.now().time()
        gps_time = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
        self.gps_clock.setTime(gps_time)

    def toggle_map_follow(self, state):
        """Toggle whether map follows the GPS marker."""
        js_code = f"setFollowMarker({str(state == Qt.Checked).lower()});"
        self.map_view.page().runJavaScript(js_code)

    def clear_map_path(self):
        """Clear the GPS path trace on the map."""
        self.map_view.page().runJavaScript("clearPath();")
        self.data_display.append(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Cleared GPS path")

    def open_google_maps(self):
        """Open current coordinates in Google Maps."""
        if hasattr(self, 'current_lat') and hasattr(self, 'current_lon'):
            url = f"https://www.google.com/maps?q={self.current_lat},{self.current_lon}"
            import webbrowser
            webbrowser.open(url)

    def clear_plots(self):
        """Clear all plot data."""
        # Clear data arrays
        self.time_data = []
        self.altitude_data = []
        self.temperature_data = []
        self.pressure_data = []
        
        # Update plots
        self.altitude_line.setData([], [])
        self.temp_line.setData([], [])
        self.pressure_line.setData([], [])
        
        # Add log entry
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        self.data_display.append(f"[{timestamp}] Cleared all plots")

    def auto_connect(self):
        """Automatically connect to the selected COM port."""
        if self.serial_port is None:  # Only connect if not already connected
            self.toggle_connection()
            if self.serial_port and self.serial_port.is_open:
                self.data_display.append(
                    f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] "
                    f"Auto-connected to {self.port_selector.currentText()}"
                )

    def switch_plot_view(self, index):
        """Switch between different plot views."""
        self.plot_stack.setCurrentIndex(index)

# Add this new widget class
class CompassWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bearing = 0
        self.setMinimumSize(150, 150)
        
    def setBearing(self, bearing):
        self.bearing = bearing
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate center and radius
            center_x = self.width() // 2
            center_y = self.height() // 2
            radius = min(center_x, center_y) - 10
            
            # Draw outer circle
            painter.setPen(QPen(QColor('#3a3a3a'), 2))
            painter.setBrush(QBrush(QColor('#2a2a2a')))
            painter.drawEllipse(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
            
            # Draw cardinal points
            painter.setPen(QPen(QColor('#666666'), 1))
            font = QFont('Arial', 10)
            font.setBold(True)
            painter.setFont(font)
            
            points = [('N', 0), ('E', 90), ('S', 180), ('W', 270)]
            for label, angle in points:
                x = int(center_x + (radius - 20) * sin(radians(angle)))
                y = int(center_y - (radius - 20) * cos(radians(angle)))
                # Create a QRect for text placement
                text_rect = QRectF(x - 10, y - 10, 20, 20)
                painter.drawText(text_rect, Qt.AlignCenter, label)
            
            # Draw direction arrow instead of simple line
            painter.setPen(QPen(QColor('#00ff00'), 2))
            painter.setBrush(QBrush(QColor('#00ff00')))
            
            # Calculate arrow points
            needle_length = radius - 15
            arrow_width = 10
            
            # Arrow tip
            tip_x = center_x + needle_length * sin(radians(self.bearing))
            tip_y = center_y - needle_length * cos(radians(self.bearing))
            
            # Arrow base points
            base1_x = center_x + arrow_width * sin(radians(self.bearing + 90))
            base1_y = center_y - arrow_width * cos(radians(self.bearing + 90))
            base2_x = center_x + arrow_width * sin(radians(self.bearing - 90))
            base2_y = center_y - arrow_width * cos(radians(self.bearing - 90))
            
            # Draw arrow
            points = [
                QPoint(int(tip_x), int(tip_y)),
                QPoint(int(base1_x), int(base1_y)),
                QPoint(int(base2_x), int(base2_y))
            ]
            painter.drawPolygon(points)
            
            # Draw bearing value
            painter.setPen(QPen(QColor('#00ff00'), 1))
            font = QFont('Arial', 12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, center_y + radius/2, self.width(), 30),
                            Qt.AlignHCenter,
                            f"{self.bearing:.1f}°")
        finally:
            painter.end()

# Add this new widget class after the CompassWidget class
class SpeedDialWidget(QWidget):
    def __init__(self, title, unit, max_value=100, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.value = 0
        self.max_value = max_value
        self.setMinimumSize(100, 100)
        
    def setValue(self, value):
        self.value = min(value, self.max_value)  # Clamp to max value
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate center and radius
            center_x = self.width() // 2
            center_y = self.height() // 2
            radius = min(center_x, center_y) - 10
            
            # Draw outer circle
            painter.setPen(QPen(QColor('#3a3a3a'), 2))
            painter.setBrush(QBrush(QColor('#2a2a2a')))
            painter.drawEllipse(QRectF(center_x - radius, center_y - radius, 
                                     radius * 2, radius * 2))
            
            # Draw title
            painter.setPen(QPen(QColor('#00ff00'), 1))
            font = QFont('Arial', 12)  # Increased from 9
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, 8, self.width(), 25),  # Adjusted spacing
                           Qt.AlignHCenter, self.title)
            
            # Draw scale markers
            painter.setPen(QPen(QColor('#666666'), 1))
            for i in range(11):  # 0 to max_value in 10 steps
                angle = -120 + (i * 240 / 10)  # -120° to +120°
                inner_x = center_x + (radius - 15) * cos(radians(angle))
                inner_y = center_y + (radius - 15) * sin(radians(angle))
                outer_x = center_x + (radius - 5) * cos(radians(angle))
                outer_y = center_y + (radius - 5) * sin(radians(angle))
                painter.drawLine(int(inner_x), int(inner_y), 
                               int(outer_x), int(outer_y))
            
            # Draw value needle
            painter.setPen(QPen(QColor('#ff0000'), 2))
            value_angle = -120 + (self.value * 240 / self.max_value)
            needle_length = radius - 10
            end_x = center_x + needle_length * cos(radians(value_angle))
            end_y = center_y + needle_length * sin(radians(value_angle))
            painter.drawLine(center_x, center_y, int(end_x), int(end_y))
            
            # Draw center dot
            painter.setBrush(QBrush(QColor('#ff0000')))
            painter.drawEllipse(QPoint(center_x, center_y), 5, 5)
            
            # Draw value text
            painter.setPen(QPen(QColor('#ffffff'), 1))
            font = QFont('Arial', 14)  # Increased from 11
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, center_y + 15, self.width(), 30),  # Adjusted spacing
                           Qt.AlignHCenter,
                           f"{self.value:.1f} {self.unit}")
        finally:
            painter.end()

# Add this new widget class after the SpeedDialWidget class
class DigitalClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hours = 0
        self.minutes = 0
        self.seconds = 0
        self.setMinimumSize(200, 80)
        
    def setTime(self, gps_time):
        """Update time from GPS time (seconds since midnight)"""
        total_seconds = int(gps_time)
        self.hours = total_seconds // 3600
        self.minutes = (total_seconds % 3600) // 60
        self.seconds = total_seconds % 60
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw background
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor('#1a1a1a')))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)
            
            # Draw time text
            time_str = f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}"
            painter.setPen(QPen(QColor('#00ff00')))
            font = QFont('Courier New', 24)
            font.setBold(True)
            painter.setFont(font)
            
            # Draw label
            label_font = QFont('Arial', 10)
            label_font.setBold(True)
            painter.setFont(label_font)
            painter.drawText(QRectF(0, 5, self.width(), 20),
                           Qt.AlignHCenter, "GPS Time (UTC)")
            
            # Draw time
            painter.setFont(font)
            painter.drawText(QRectF(0, 20, self.width(), self.height()-20),
                           Qt.AlignCenter, time_str)
            
        finally:
            painter.end()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern looking style
    
    # Set dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, Qt.black)
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, Qt.darkGray)
    palette.setColor(QPalette.AlternateBase, Qt.black)
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, Qt.darkGray)
    palette.setColor(QPalette.ButtonText, Qt.white)
    app.setPalette(palette)

    window = GroundStationGUI()
    window.show()
    sys.exit(app.exec_())
