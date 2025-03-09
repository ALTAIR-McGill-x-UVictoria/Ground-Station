import sys
import serial
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QPalette, QColor, QTextCursor  # Add QTextCursor here
import pyqtgraph as pg
from datetime import datetime
import queue
import threading
import os

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
            
            function updateMarker(lat, lon) {
                marker.setLatLng([lat, lon]);
                map.setView([lat, lon]);
            }
        </script>
    </body>
    </html>
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flight Computer Ground Station")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize serial connection
        self.serial_queue = queue.Queue()
        self.serial_port = None
        
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
        
        # Create plots tab
        plots_tab = QWidget()
        plots_layout = QGridLayout(plots_tab)
        
        # Add existing plots to the plots tab
        self.altitude_plot = pg.PlotWidget(title="Altitude")
        self.altitude_plot.setLabel('left', "Altitude", units='m')
        self.altitude_plot.setLabel('bottom', "Time", units='s')
        self.altitude_line = self.altitude_plot.plot(pen='b')
        plots_layout.addWidget(self.altitude_plot, 0, 0)
        
        self.temp_plot = pg.PlotWidget(title="Temperature")
        self.temp_plot.setLabel('left', "Temperature", units='°C')
        self.temp_plot.setLabel('bottom', "Time", units='s')
        self.temp_line = self.temp_plot.plot(pen='r')
        plots_layout.addWidget(self.temp_plot, 0, 1)
        
        self.pressure_plot = pg.PlotWidget(title="Pressure")
        self.pressure_plot.setLabel('left', "Pressure", units='hPa')
        self.pressure_plot.setLabel('bottom', "Time", units='s')
        self.pressure_line = self.pressure_plot.plot(pen='g')
        plots_layout.addWidget(self.pressure_plot, 1, 0)
        
        # Create dashboard tab
        dashboard_tab = QWidget()
        dashboard_layout = QGridLayout(dashboard_tab)
        
        # Create categorized status indicators
        self.status_widgets = {}
        
        # Flight Data Section
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
        dashboard_layout.addWidget(flight_group, 0, 0)
        
        # Radio Status Section
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
        dashboard_layout.addWidget(radio_group, 0, 1)
        
        # System Status Section
        system_group = QGroupBox("System Status")
        system_layout = QGridLayout()
        system_parameters = [
            ("SDStatus", "", 0, 0, "SD Card Status"),
            ("GPS", "", 0, 1, "GPS Fix Status"),
            ("ActuatorStatus", "", 1, 0, "Actuator System Status")
        ]
        self.add_parameters_to_layout(system_parameters, system_layout)
        system_group.setLayout(system_layout)
        dashboard_layout.addWidget(system_group, 1, 0)
        
        # Add tabs to tab widget
        self.tab_widget.addTab(plots_tab, "Plots")
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
        if self.serial_port is None:
            try:
                port = self.port_selector.currentText()
                self.serial_port = serial.Serial(port, 115200)
                self.connect_button.setText("Disconnect")
                self.port_selector.setEnabled(False)
                # Start reading thread
                self.reader_thread = threading.Thread(target=self.read_serial)
                self.reader_thread.daemon = True
                self.reader_thread.start()
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", str(e))
        else:
            self.serial_port.close()
            self.serial_port = None
            self.connect_button.setText("Connect")
            self.port_selector.setEnabled(True)

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
                    self.log_file.flush()  # Ensure data is written immediately
                
                # Validate and clean the data
                line = ''.join(c for c in line if c.isprintable() or c in [',', '.', '-'])
                
                # Split into main packet and RSSI/SNR update if present
                parts = line.strip().split('\n')
                
                # Parse main packet
                values = parts[0].split(',')
                # Remove any empty/null elements at the end of values
                while values and (not values[-1] or not values[-1].strip()):
                    values.pop()
                    
                # Validate all values are present and non-empty
                if any(not v.strip() for v in values):
                    continue

                # Handle RSSI/SNR only updates (2 values)
                if len(values) == 2:
                    try:
                        # Validate these are numbers
                        if not all(v.strip('-').replace('.','').isdigit() for v in values):
                            continue
                        rssi = int(values[0])
                        snr = int(values[1])
                        self.update_parameter('RSSI', rssi)
                        self.update_parameter('SNR', snr)
                    except ValueError:
                        continue
                    
                    # Add to raw data display
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    self.data_display.append(f"[{timestamp}] RSSI/SNR Update: {line}")
                    continue

                # Handle full telemetry packets (17 values)
                if len(values) == 17:
                    # Parse values directly without JSON
                    ack = int(values[0])
                    rssi = int(values[1])
                    snr = int(values[2])
                    roll = float(values[3])
                    pitch = float(values[4])
                    yaw = float(values[5])
                    pressure = float(values[6])
                    temperature = float(values[7])
                    altitude = float(values[8])
                    sd_status = bool(int(values[9]))
                    actuator_status = bool(int(values[10]))
                    gps_lat = float(values[11])
                    gps_lon = float(values[12])
                    gps_alt = float(values[13])
                    gps_speed = float(values[14])
                    gps_time = float(values[15])
                    gps_valid = bool(int(values[16]))
                    
                    # Update RSSI/SNR if new values received
                    if len(parts) > 1:
                        rssi_snr = parts[1].split(',')
                        if len(rssi_snr) == 2:
                            rssi = int(rssi_snr[0])
                            snr = int(rssi_snr[1])
                    
                    # Update data arrays
                    timestamp = len(self.time_data)
                    self.time_data.append(timestamp)
                    self.altitude_data.append(altitude)
                    self.temperature_data.append(temperature)
                    self.pressure_data.append(pressure)
                    
                    # Update plots
                    self.altitude_line.setData(self.time_data, self.altitude_data)
                    self.temp_line.setData(self.time_data, self.temperature_data)
                    self.pressure_line.setData(self.time_data, self.pressure_data)
                    
                    # Update dashboard values
                    self.update_parameter('Altitude', altitude)
                    self.update_parameter('Temperature', temperature)
                    self.update_parameter('Pressure', pressure)
                    self.update_parameter('Roll', roll)
                    self.update_parameter('Pitch', pitch)
                    self.update_parameter('Yaw', yaw)
                    self.update_parameter('RSSI', rssi)
                    self.update_parameter('SNR', snr)
                    self.update_parameter('ACK', ack)
                    
                    # Update status indicators
                    status_color = "#00ff00" if sd_status else "#ff0000"
                    self.status_widgets['sdstatus'].setStyleSheet(f"color: {status_color}")
                    
                    status_color = "#00ff00" if actuator_status else "#ff0000"
                    self.status_widgets['actuatorstatus'].setStyleSheet(f"color: {status_color}")
                    
                    # Update GPS data if valid
                    if gps_valid:
                        self.update_map_marker(gps_lat, gps_lon)
                        self.update_parameter('GPS Speed', gps_speed, "{:.1f}")
                        self.status_widgets['gps'].setStyleSheet("color: #00ff00")
                    else:
                        self.status_widgets['gps'].setStyleSheet("color: #ff0000")
                    
                    # Update raw data display with timestamp and both packet parts
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    if len(parts) > 1:
                        self.data_display.append(f"[{timestamp}] Main: {parts[0]}")
                        self.data_display.append(f"[{timestamp}] RSSI/SNR: {parts[1]}")
                    else:
                        self.data_display.append(f"[{timestamp}] {line}")
                    
                    # Keep only the last 100 lines
                    doc = self.data_display.document()
                    while doc.blockCount() > 100:
                        cursor = QTextCursor(doc.firstBlock())
                        cursor.select(QTextCursor.BlockUnderCursor)
                        cursor.removeSelectedText()
                        cursor.deleteChar()
                    
                # Handle extended packets (18 values - includes battery voltage)
                elif len(values) == 18:
                    # Parse values directly without JSON
                    ack = int(values[0])
                    rssi = int(values[1])
                    snr = int(values[2]) 
                    roll = float(values[3])
                    pitch = float(values[4])
                    yaw = float(values[5])
                    pressure = float(values[6])
                    temperature = float(values[7])
                    altitude = float(values[8])
                    sd_status = bool(int(values[9]))
                    actuator_status = bool(int(values[10]))
                    gps_lat = float(values[11])
                    gps_lon = float(values[12]) 
                    gps_alt = float(values[13])
                    gps_speed = float(values[14])
                    gps_time = float(values[15])
                    gps_valid = bool(int(values[16]))
                    battery_voltage = float(values[17])

                    # Update all parameters...
                    # Existing update code...
                    
                    # Add battery voltage display
                    self.update_parameter('Battery', battery_voltage, "{:.2f}")

                else:
                    print(f"Invalid packet length: {len(values)}")
                    
            except ValueError as e:
                print(f"Error parsing values: {str(e)}")
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

    def update_map_marker(self, lat, lon):
        if lat != 0 and lon != 0:  # Only update if we have valid coordinates
            js_code = f"updateMarker({lat}, {lon});"
            self.map_view.page().runJavaScript(js_code)

    # Add these methods to the GroundStationGUI class
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
                # Create filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                path = "logs"
                if not os.path.exists(path):
                    os.makedirs(path)
                filename = f"{path}/serial_log_{timestamp}.txt"
                self.log_file = open(filename, 'w')
                self.is_logging = True
                self.log_button.setText("Stop Logging")
                self.data_display.append(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Started logging to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Logging Error", f"Could not create log file: {str(e)}")
        else:
            if self.log_file:
                self.log_file.close()
                self.log_file = None
            self.is_logging = False
            self.log_button.setText("Start Logging")
            self.data_display.append(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Stopped logging")

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
