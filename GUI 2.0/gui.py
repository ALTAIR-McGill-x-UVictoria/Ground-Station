import sys
import serial
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer, Qt, QUrl, QPoint, QRectF
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import (
    QPalette, QColor, QTextCursor, QPainter, QBrush, 
    QPen, QFont, QIcon
)
import pyqtgraph as pg
from datetime import datetime
import queue
import threading
import os
import random
from math import sin, cos, radians, atan2, degrees

from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PyQt5.QtCore import Qt, QRectF

from geopy.geocoders import Nominatim
import socket
import requests
import json

from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot

# Add this import at the top with other imports
import time

class LocationHandler(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
    
    @pyqtSlot(float, float)
    def onLocationReceived(self, lat, lon):
        """Callback when geolocation succeeds"""
        self.main_window.user_lat = lat
        self.main_window.user_lon = lon
        self.main_window.update_status(f"HTML5 Geolocation: {lat:.6f}, {lon:.6f}")
        self.main_window.init_user_marker()
    
    @pyqtSlot(str)
    def onLocationError(self, error):
        """Callback when geolocation fails"""
        self.main_window.update_status(f"Geolocation error: {error}")
        # Fall back to IP geolocation
        self.main_window.detect_user_location()

class GroundStationGUI(QMainWindow):
    # Update the MAP_HTML constant with the new marker functionality:
    MAP_HTML = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <style>
            #map { height: 100vh; width: 100%; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([0, 0], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
            
            // Create custom icons for different markers
            var vehicleIcon = L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            });
            
            var userIcon = L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            });
            
            var marker = L.marker([0, 0], {icon: vehicleIcon}).addTo(map);
            var userMarker = L.marker([0, 0], {icon: userIcon}).addTo(map);
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
            
            function updateUserMarker(lat, lon) {
                userMarker.setLatLng([lat, lon]);
                userMarker.bindPopup('Ground Station').openPopup();
            }
            
            function setFollowMarker(follow) {
                followMarker = follow;
            }
            
            function clearPath() {
                coordinates = [];
                pathLine.setLatLngs([]);
            }

            // Add HTML5 Geolocation support
            function getCurrentPosition() {
                if ("geolocation" in navigator) {
                    navigator.geolocation.getCurrentPosition(function(position) {
                        var lat = position.coords.latitude;
                        var lon = position.coords.longitude;
                        // Call back to Python with the coordinates
                        new QWebChannel(qt.webChannelTransport, function(channel) {
                            channel.objects.handler.onLocationReceived(lat, lon);
                        });
                    }, function(error) {
                        console.error("Geolocation error:", error);
                        // Notify Python of the error
                        new QWebChannel(qt.webChannelTransport, function(channel) {
                            channel.objects.handler.onLocationError(error.message);
                        });
                    }, {
                        enableHighAccuracy: true,
                        timeout: 5000,
                        maximumAge: 0
                    });
                }
            }
            // Initialize QWebChannel
            new QWebChannel(qt.webChannelTransport, function(channel) {
                window.handler = channel.objects.handler;
            });

            // Modified geolocation function
            function getCurrentPosition() {
                if ("geolocation" in navigator) {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            var lat = position.coords.latitude;
                            var lon = position.coords.longitude;
                            if (window.handler) {
                                window.handler.onLocationReceived(lat, lon);
                            }
                        },
                        function(error) {
                            console.error("Geolocation error:", error);
                            if (window.handler) {
                                window.handler.onLocationError(error.message);
                            }
                        },
                        {
                            enableHighAccuracy: true,
                            timeout: 5000,
                            maximumAge: 0
                        }
                    );
                }
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
        
        # Add this line after other initializations
        self.start_time = time.time()
        
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

        # Initialize user's location
        self.user_lat = None
        self.user_lon = None
        
        # Wait for map to load before detecting location
        self.map_view.loadFinished.connect(self.on_map_loaded)

        # Create separate arrays for short packets (RSSI/SNR)
        self.signal_time_data = []
        self.signal_rssi_data = []
        self.signal_snr_data = []
        
        # Create separate arrays for full telemetry packets
        self.telemetry_time_data = []
        self.telemetry_rssi_data = []
        self.telemetry_snr_data = []
        self.altitude_data = []
        self.temperature_data = []
        self.pressure_data = []
        self.ground_speed_data = []

    def on_map_loaded(self, ok):
        """Called when the map has finished loading"""
        if ok:
            # Wait a bit for JavaScript to initialize fully
            QTimer.singleShot(1500, self.detect_user_location)
        else:
            print("Map failed to load")

    def setup_ui(self):
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(main_widget)
        
        # Create left layout for main content
        left_layout = QVBoxLayout()
        
        # Create command layout for right panel
        command_layout = QVBoxLayout()
        
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
        
        # Flight Data page (GPS altitude, speeds, temp, pressure)
        flight_page = QWidget()
        flight_layout = QGridLayout(flight_page)
        
        # GPS Altitude plot (top left)
        self.altitude_plot = pg.PlotWidget(title="Altitude")
        self.altitude_plot.setLabel('left', 'Altitude', units='m')
        self.altitude_plot.setLabel('bottom', 'Time', units='s')
        self.altitude_plot.showGrid(x=True, y=True)
        self.altitude_plot.addLegend()  # Add legend for multiple curves
        flight_layout.addWidget(self.altitude_plot, 0, 0)
        
        # Initialize altitude curves
        self.altitude_gps_curve = self.altitude_plot.plot(pen='g', name='GPS Altitude')
        self.altitude_baro_curve = self.altitude_plot.plot(pen='y', name='Baro Altitude')
        
        # Speed plot (top right)
        self.speed_plot = pg.PlotWidget(title="Speed")
        self.speed_plot.setLabel('left', 'Speed', units='m/s')
        self.speed_plot.setLabel('bottom', 'Time', units='s')
        self.speed_plot.showGrid(x=True, y=True)
        self.speed_plot.addLegend()
        flight_layout.addWidget(self.speed_plot, 0, 1)
        
        # Temperature plot (bottom left)
        self.temp_plot = pg.PlotWidget(title="Temperature")
        self.temp_plot.setLabel('left', 'Temperature', units='°C')
        self.temp_plot.setLabel('bottom', 'Time', units='s')
        self.temp_plot.showGrid(x=True, y=True)
        flight_layout.addWidget(self.temp_plot, 1, 0)
        
        # Pressure plot (bottom right)
        self.press_plot = pg.PlotWidget(title="Pressure")
        self.press_plot.setLabel('left', 'Pressure', units='hPa')
        self.press_plot.setLabel('bottom', 'Time', units='s')
        self.press_plot.showGrid(x=True, y=True)
        flight_layout.addWidget(self.press_plot, 1, 1)
        
        # Initialize curves
        self.speed_h_curve = self.speed_plot.plot(pen='y', name='Ground Speed')
        self.speed_v_curve = self.speed_plot.plot(pen='c', name='Vertical Speed')
        self.altitude_curve = self.altitude_plot.plot(pen='g')
        self.temp_curve = self.temp_plot.plot(pen='r')
        self.press_curve = self.press_plot.plot(pen='b')
        
        # Signal Strength page
        signal_page = QWidget()
        signal_layout = QGridLayout(signal_page)
        
        # RSSI Plot
        self.rssi_plot = pg.PlotWidget(title="RSSI")
        self.rssi_plot.setLabel('left', 'RSSI', units='dBm')
        self.rssi_plot.setLabel('bottom', 'Time', units='s')
        self.rssi_plot.showGrid(x=True, y=True)
        signal_layout.addWidget(self.rssi_plot, 0, 0)
        
        # SNR Plot
        self.snr_plot = pg.PlotWidget(title="SNR")
        self.snr_plot.setLabel('left', 'SNR', units='dB')
        self.snr_plot.setLabel('bottom', 'Time', units='s')
        self.snr_plot.showGrid(x=True, y=True)
        signal_layout.addWidget(self.snr_plot, 1, 0)
        
        # Initialize curves for signal plots
        self.rssi_curve = self.rssi_plot.plot(pen='r')
        self.snr_curve = self.snr_plot.plot(pen='b')
        
        signal_page.setLayout(signal_layout)
        
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
        
        plots_tab.setLayout(plots_layout)
        
        
        # Create dashboard tab
        dashboard_tab = QWidget()
        dashboard_layout = QGridLayout(dashboard_tab)
        dashboard_layout.setSpacing(10)
        
        # Navigation Data Section (now top left)
        nav_group = QGroupBox("Navigation")
        nav_group.setStyleSheet("""
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
        
        nav_group.setLayout(nav_layout)
        dashboard_layout.addWidget(nav_group, 0, 0)
        
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
            ("GPS", "", 1, 1, "GPS Fix Status")  # Changed from "Connection" to "GPS"
        ]
        self.add_parameters_to_layout(radio_parameters, radio_layout)

        # Add packet interval label to radio status section
        # self.last_packet_label = QLabel("Packet Interval: --")
        # self.last_packet_label.setStyleSheet("""
        #     QLabel {
        #         color: #ff0000;
        #         font-family: 'Courier New';
        #         font-size: 12px;
        #         padding: 5px;
        #         border: 1px solid #3a3a3a;
        #         border-radius: 4px;
        #         background-color: #2a2a2a;
        #     }
        # """)
        # radio_layout.addWidget(self.last_packet_label, 2, 0, 1, 2)

        radio_group.setLayout(radio_layout)
        dashboard_layout.addWidget(radio_group, 1, 0)  # Move to bottom left
        
        # System Status Section (now bottom right)
        system_group = QGroupBox("System Status")
        system_layout = QGridLayout()
        system_parameters = [
            ("SD Status", "", 0, 0, "SD Card Status"),
            ("LED Status", "", 0, 1, "LED Status"),  # Add LED status indicator
            ("Actuator Status", "", 1, 0, "Actuator System Status"),
            ("Source", "", 1, 1, "Source Status")  # Add Source status indicator
        ]
        self.add_parameters_to_layout(system_parameters, system_layout)
        
        system_group.setLayout(system_layout)
        dashboard_layout.addWidget(system_group, 1, 1)  # Move to bottom right
        
        # Add tabs to tab widget
        self.tab_widget.addTab(dashboard_tab, "Dashboard")
        self.tab_widget.addTab(plots_tab, "Plots")
        
        
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
        left_controls = QHBoxLayout()
        
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
        
        map_controls.addLayout(left_controls)
        map_controls.addStretch()
        
        # Add existing controls on the right
        self.follow_marker = QCheckBox("Lock on GPS")
        self.follow_marker.setChecked(True)
        self.follow_marker.stateChanged.connect(self.toggle_map_follow)
        map_controls.addWidget(self.follow_marker)
        
        # Add refresh location button
        refresh_location = QPushButton("Detect Location")
        refresh_location.clicked.connect(self.detect_user_location)
        refresh_location.setStyleSheet("""
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
        map_controls.addWidget(refresh_location)
        
        # Add to the map controls in setup_ui() method
        # Add Google Maps button
        open_gmaps = QPushButton("Open in Google Maps")
        open_gmaps.clicked.connect(self.open_google_maps)
        open_gmaps.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                padding: 5px 10px;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666666;
            }
        """)
        map_controls.addWidget(open_gmaps)
        
        # Add controls to map layout
        map_layout.addLayout(map_controls)
        
        # Create web view for map
        self.map_view = QWebEngineView()
        self.map_view.setHtml(self.MAP_HTML)
        map_layout.addWidget(self.map_view)
        
        # Add map tab to tab widget
        self.tab_widget.addTab(map_tab, "Map")
        
        # Set up web channel for JavaScript communication
        self.channel = QWebChannel()
        self.location_handler = LocationHandler(self)
        self.channel.registerObject("handler", self.location_handler)
        self.map_view.page().setWebChannel(self.channel)
        
        self.map_view.setHtml(self.MAP_HTML)
        map_layout.addWidget(self.map_view)
        
        # Initialize user's location marker
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
        
        # Add this after the existing LED control section in setup_ui()
        # Source Control
        source_group = QGroupBox("Source Control")
        source_layout = QVBoxLayout()

        # LED Intensity Control for Source
        source_intensity_layout = QHBoxLayout()
        source_intensity_layout.addWidget(QLabel("Intensity:"))
        self.source_intensity = QSpinBox()
        self.source_intensity.setRange(0, 255)
        source_intensity_layout.addWidget(self.source_intensity)
        source_activate = QPushButton("Set LED")
        source_activate.clicked.connect(self.send_source_command)
        source_intensity_layout.addWidget(source_activate)
        source_layout.addLayout(source_intensity_layout)

        # LED Blink Control for Source
        source_blink_layout = QHBoxLayout()
        source_blink_layout.addWidget(QLabel("Delay (ms):"))
        self.source_blink_delay = QSpinBox()
        self.source_blink_delay.setRange(100, 2000)
        self.source_blink_delay.setSingleStep(100)
        self.source_blink_delay.setValue(500)
        source_blink_layout.addWidget(self.source_blink_delay)
        source_blink_activate = QPushButton("Blink LED")
        source_blink_activate.clicked.connect(self.send_source_blink_command)
        source_blink_layout.addWidget(source_blink_activate)
        source_layout.addLayout(source_blink_layout)

        source_group.setLayout(source_layout)
        command_layout.addWidget(source_group)
        
        # Ping Control
        ping_group = QGroupBox("System Control")
        ping_layout = QVBoxLayout()
        ping_button = QPushButton("Ping")
        ping_button.clicked.connect(lambda: self.send_command("ping"))
        ping_layout.addWidget(ping_button)
        ping_group.setLayout(ping_layout)
        command_layout.addWidget(ping_group)
        
        # Add this to setup_ui() after the other control groups in the command layout

        # Manual Command Group
        manual_command_group = QGroupBox("Manual Command")
        manual_command_layout = QVBoxLayout()

        # Text input and send button
        manual_input_layout = QHBoxLayout()
        self.manual_command_input = QLineEdit()
        self.manual_command_input.setPlaceholderText("Enter command")
        manual_input_layout.addWidget(self.manual_command_input)

        send_command_btn = QPushButton("Send")
        send_command_btn.clicked.connect(self.send_manual_command)
        manual_input_layout.addWidget(send_command_btn)

        manual_command_layout.addLayout(manual_input_layout)
        manual_command_group.setLayout(manual_command_layout)
        command_layout.addWidget(manual_command_group)
        
        # Add stretch to push widgets to top
        command_layout.addStretch()
        
        # Create command panel
        command_panel = QWidget()
        command_panel.setLayout(command_layout)
        command_panel.setFixedWidth(250)  # Set fixed width for command panel
        
        # Add layouts to main layout
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addWidget(command_panel)

        # Initialize data arrays
        self.time_data = []
        self.ground_speed_data = []
        self.vertical_speed_data = []
        self.gps_altitude_data = []
        self.rssi_data = []
        self.snr_data = []
        self.temperature_data = []
        self.pressure_data = []
        self.altitude_gps_data = []
        self.altitude_baro_data = []

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
        """Process received data and update plots."""
        while not self.serial_queue.empty():
            try:
                line = self.serial_queue.get_nowait()
                
                # Log raw data if logging is enabled
                if self.is_logging and self.log_file:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    self.log_file.write(f"[{timestamp}] {line}\n")
                    self.log_file.flush()
                
                # Add to raw data display
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                self.data_display.append(f"[{timestamp}] {line}")

                # Keep only the last 100 lines in raw data display
                doc = self.data_display.document()
                while (doc.blockCount() > 100):
                    cursor = QTextCursor(doc.firstBlock())
                    cursor.select(QTextCursor.BlockUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deleteChar()

                # Call parse_packet to process the data
                if not self.parse_packet(line):
                    print(f"Failed to parse packet: {line}")

            except Exception as e:
                print(f"Error in update_plots: {str(e)}")

    def update_parameter(self, name, value, format_str="{:.1f}"):
        if name.lower() in self.status_widgets:
            widget = self.status_widgets[name.lower()]
            formatted_value = format_str.format(value)
            widget.setText(formatted_value)
            
            # Add visual feedback based on value ranges
            if name.lower() == "rssi":
                if value > -70:
                    widget.setStyleSheet("font-size: 24px; font-weight: bold; color: #00ff00; background-color: #2a2a2a; border-radius: 5px; padding: 5px;")  # Good signal
                elif value > -90:
                    widget.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffff00; background-color: #2a2a2a; border-radius: 5px; padding: 5px;")  # Medium signal
                else:
                    widget.setStyleSheet("font-size: 24px; font-weight: bold; color: #ff0000; background-color: #2a2a2a; border-radius: 5px; padding: 5px;")  # Poor signal

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
        try:
            if (lat != 0 and lon != 0):  # Only update if we have valid coordinates
                # Calculate bearing if we have previous coordinates
                if self.last_gps_lat is not None and self.last_gps_lon is not None:
                    # Only calculate new bearing if we've moved more than a minimal distance
                    min_distance = 0.0001  # About 10 meters
                    if abs(lat - self.last_gps_lat) > min_distance or abs(lon - self.last_gps_lon) > min_distance:
                        bearing = self.calculate_bearing(self.last_gps_lat, self.last_gps_lon, lat, lon)
                        self.compass.setBearing(bearing)  # Update vehicle heading compass
                
                # Calculate bearing to target if we have user's location
                if hasattr(self, 'user_lat') and hasattr(self, 'user_lon'):
                    target_bearing = self.calculate_target_bearing(
                        self.user_lat, self.user_lon, lat, lon
                    )
                    self.target_compass.setBearing(target_bearing)  # Update target bearing compass
                
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
                
        except Exception as e:
            print(f"Error updating map marker: {str(e)}")

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

    def send_source_command(self):
        """Send Source LED intensity command."""
        try:
            intensity = self.source_intensity.value()
            self.send_command(f"SOURCE_LED_SET {intensity}")
        except Exception as e:
            print(f"Error sending source LED command: {str(e)}")

    def send_source_blink_command(self):
        """Send Source LED blink command."""
        try:
            delay = self.source_blink_delay.value()
            self.send_command(f"SOURCE_LED_BLINK {delay}")
        except Exception as e:
            print(f"Error sending source blink command: {str(e)}")

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
                
                self.log_file = open(f"{path}/flight_log_{timestamp}.txt", 'w')
                self.log_file.write(f"HAB Ground Station Log\n")
                self.log_file.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.log_file.write(f"----------------------------------------\n\n")
                
                self.is_logging = True
                self.log_button.setText("Stop Logging")
                self.data_display.append(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Started logging to {path}/flight_log_{timestamp}.txt")
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
            # Update compass widget only
            self.compass.setBearing(bearing)
        
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
        if hasattr(self, 'last_gps_lat') and hasattr(self, 'last_gps_lon') and self.last_gps_lat is not None and self.last_gps_lon is not None:
            url = f"https://www.google.com/maps?q={self.last_gps_lat},{self.last_gps_lon}"
            import webbrowser
            webbrowser.open(url)
            self.update_status(f"Opened coordinates in Google Maps: {self.last_gps_lat:.6f}, {self.last_gps_lon:.6f}")
        else:
            self.update_status("No valid GPS coordinates available")

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

    # Add this method to the GroundStationGUI class:
    def calculate_target_bearing(self, user_lat, user_lon, target_lat, target_lon):
        """Calculate bearing from user location to target GPS coordinates."""
        try:
            if user_lat is None or user_lon is None or target_lat is None or target_lon is None:
                return 0.0
                
            # Convert to radians
            user_lat = radians(float(user_lat))
            user_lon = radians(float(user_lon))  # Fixed: Changed lon1 to user_lon
            target_lat = radians(float(target_lat))
            target_lon = radians(float(target_lon))
            
            # Calculate bearing
            d_lon = target_lon - user_lon
            x = sin(d_lon) * cos(target_lat)
            y = cos(user_lat) * sin(target_lat) - sin(user_lat) * cos(target_lat) * cos(d_lon)
            
            initial_bearing = atan2(x, y)
            bearing = (degrees(initial_bearing) + 360) % 360
            
            return bearing
        except Exception as e:
            print(f"Error calculating target bearing: {str(e)}")
            return 0.0

    def init_user_marker(self):
        """Initialize the user's location marker on the map."""
        if hasattr(self, 'user_lat') and hasattr(self, 'user_lon') and self.user_lat is not None and self.user_lon is not None:
            try:
                # Add debug output
                print(f"Setting user marker at: {self.user_lat}, {self.user_lon}")
                
                # Use runJavaScript with callback to check for errors
                js_code = f"updateUserMarker({self.user_lat}, {self.user_lon});"
                self.map_view.page().runJavaScript(js_code, 0, lambda result: print(f"User marker update result: {result}" if result else "User marker updated"))
                
                # Center map on user's location initially
                js_code = f"map.setView([{self.user_lat}, {self.user_lon}], 13);"
                self.map_view.page().runJavaScript(js_code)
            except Exception as e:
                print(f"Error setting user marker: {e}")

    # Add this new method to the GroundStationGUI class:
    def detect_user_location(self):
        """Detect user's current location using various methods."""
        try:
            # Try IP geolocation first as it's more reliable
            response = requests.get('https://ipapi.co/json/')
            if response.status_code == 200:
                data = response.json()
                self.user_lat = float(data['latitude'])
                self.user_lon = float(data['longitude'])
                self.update_status(f"Location detected via IP: {self.user_lat:.6f}, {self.user_lon:.6f}")
                self.init_user_marker()
            else:
                # Fallback to default location
                self.user_lat = 45.5017  # Montreal
                self.user_lon = -73.5673
                self.update_status("Using default location (Montreal)")
                self.init_user_marker()
        except Exception as e:
            print(f"Error detecting location: {str(e)}")
            # Set default location
            self.user_lat = 45.5017
            self.user_lon = -73.5673
            self.update_status("Using default location (Montreal)")
            self.init_user_marker()

    def parse_packet(self, packet):
        try:
            # Split packet into values
            values = packet.strip().split(',')
            
            # Check for minimum length and CSV format
            if len(values) < 2:
                return False
            
            # Calculate current time once for this packet
            current_time = time.time() - self.start_time
            
            # For short packets with just RSSI/SNR
            if 2 <= len(values) < 17:
                try:
                    rssi = int(values[0])
                    snr = int(values[1])
                    
                    # Update signal strength indicators using update_parameter method
                    self.update_parameter("RSSI", rssi)
                    self.update_parameter("SNR", snr)
                    
                    # Update signal arrays
                    self.signal_time_data.append(current_time)
                    self.signal_rssi_data.append(rssi)
                    self.signal_snr_data.append(snr)
                    
                    # Update signal plots
                    self.rssi_curve.setData(self.signal_time_data, self.signal_rssi_data)
                    self.snr_curve.setData(self.signal_time_data, self.signal_snr_data)
                    
                    # Limit array sizes
                    max_points = 1000
                    if len(self.signal_time_data) > max_points:
                        self.signal_time_data = self.signal_time_data[-max_points:]
                        self.signal_rssi_data = self.signal_rssi_data[-max_points:]
                        self.signal_snr_data = self.signal_snr_data[-max_points:]
                    
                    return True
                except ValueError:
                    return False
                    
            # Full telemetry packets
            elif len(values) == 17:
                try:
                    # Parse packet values
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

                    # Update dashboard parameters
                    self.update_parameter("RSSI", rssi)
                    self.update_parameter("SNR", snr)
                    self.update_parameter("Altitude", altitude)
                    self.update_parameter("Temperature", temperature)
                    self.update_parameter("Pressure", pressure)
                    vertical_speed = self.calculate_vertical_speed(altitude)
                    self.update_parameter("Vertical Speed", vertical_speed)
                    
                    # Update status indicators
                    self.update_parameter("SD Status", "Active" if sd_status else "Inactive", "{}")
                    self.update_parameter("Actuator Status", "Active" if actuator_status else "Inactive", "{}")
                    self.update_parameter("GPS", "Fix" if gps_valid else "No Fix", "{}")
                    self.update_parameter("ACK", "Received" if ack == 1 else "No ACK", "{}")
                    
                    # LED and Source status 
                    led_on = (int(values[9]) & 0x02) != 0
                    source_on = (int(values[9]) & 0x04) != 0
                    self.update_parameter("LED Status", "Active" if led_on else "Inactive", "{}")
                    self.update_parameter("Source", "Active" if source_on else "Inactive", "{}")
                    
                    # Update ground speed dial
                    self.ground_speed_dial.setValue(gps_speed)
                    self.vertical_speed_dial.setValue(vertical_speed)
                    
                    # Update GPS clock
                    if gps_time > 0:
                        self.gps_clock.setTime(gps_time)
                    
                    # Update map if GPS is valid
                    if gps_valid and gps_lat != 0 and gps_lon != 0:
                        self.update_map_marker(gps_lat, gps_lon, gps_alt)
                    
                    # Update telemetry data arrays for plots
                    self.telemetry_time_data.append(current_time)
                    self.telemetry_rssi_data.append(rssi)
                    self.telemetry_snr_data.append(snr)
                    self.altitude_data.append(altitude)
                    self.temperature_data.append(temperature)
                    self.pressure_data.append(pressure)
                    self.ground_speed_data.append(gps_speed)
                    
                    # Update vertical speed data
                    if not hasattr(self, 'vertical_speed_data'):
                        self.vertical_speed_data = []
                    self.vertical_speed_data.append(vertical_speed)
                    
                    # Limit array sizes
                    max_points = 1000
                    if len(self.telemetry_time_data) > max_points:
                        self.telemetry_time_data = self.telemetry_time_data[-max_points:]
                        self.telemetry_rssi_data = self.telemetry_rssi_data[-max_points:]
                        self.telemetry_snr_data = self.telemetry_snr_data[-max_points:]
                        self.altitude_data = self.altitude_data[-max_points:]
                        self.temperature_data = self.temperature_data[-max_points:]
                        self.pressure_data = self.pressure_data[-max_points:]
                        self.ground_speed_data = self.ground_speed_data[-max_points:]
                        if hasattr(self, 'vertical_speed_data'):
                            self.vertical_speed_data = self.vertical_speed_data[-max_points:]
                    
                    # Update all plots
                    self.altitude_curve.setData(self.telemetry_time_data, self.altitude_data)
                    self.temp_curve.setData(self.telemetry_time_data, self.temperature_data)
                    self.press_curve.setData(self.telemetry_time_data, self.pressure_data)
                    self.speed_h_curve.setData(self.telemetry_time_data, self.ground_speed_data)
                    
                    if hasattr(self, 'vertical_speed_data') and len(self.vertical_speed_data) > 0:
                        self.speed_v_curve.setData(self.telemetry_time_data[-len(self.vertical_speed_data):], 
                                                 self.vertical_speed_data)
                    
                    # Update "all plots" view
                    self.altitude_curve_all.setData(self.telemetry_time_data, self.altitude_data)
                    self.temp_curve_all.setData(self.telemetry_time_data, self.temperature_data)
                    self.press_curve_all.setData(self.telemetry_time_data, self.pressure_data)
                    self.speed_h_curve_all.setData(self.telemetry_time_data, self.ground_speed_data)
                    self.rssi_curve_all.setData(self.telemetry_time_data, self.telemetry_rssi_data)
                    self.snr_curve_all.setData(self.telemetry_time_data, self.telemetry_snr_data)
                    
                    if hasattr(self, 'vertical_speed_data') and len(self.vertical_speed_data) > 0:
                        self.speed_v_curve_all.setData(self.telemetry_time_data[-len(self.vertical_speed_data):], 
                                                    self.vertical_speed_data)
                    
                    return True
                except Exception as e:
                    print(f"Error parsing telemetry: {str(e)}")
                    return False
            
            return False
        except Exception as e:
            print(f"Error parsing packet: {str(e)}")
            return False

    def calculate_vertical_speed(self, current_altitude):
        """Calculate vertical speed based on altitude changes"""
        if not hasattr(self, 'last_altitude_time') or not hasattr(self, 'last_altitude'):
            # First measurement
            self.last_altitude = current_altitude
            self.last_altitude_time = time.time()
            return 0
        
        # Calculate time difference and altitude change
        now = time.time()
        time_diff = now - self.last_altitude_time
        if time_diff < 0.1:  # Avoid division by very small numbers
            return 0
            
        altitude_diff = current_altitude - self.last_altitude
        vertical_speed = altitude_diff / time_diff
        
        # Update last values for next calculation
        self.last_altitude = current_altitude
        self.last_altitude_time = now
        
        return vertical_speed

    def send_manual_command(self):
        """Send a manual command entered by the user."""
        try:
            command_text = self.manual_command_input.text().strip()
            if not command_text:
                return
                
            self.send_command(command_text)
            self.update_status(f"Sent command: {command_text}")
            
            # Optionally clear the text field after sending
            # self.manual_command_input.clear()
        except Exception as e:
            print(f"Error sending manual command: {str(e)}")
            self.update_status(f"Command error: {str(e)}")

    def insert_common_command(self):
        """Insert selected common command into the manual command input."""
        self.manual_command_input.setText(self.common_commands.currentText())

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
            painter.drawEllipse(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
            
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
        """
        Set the time to display on the clock
        gps_time: Time string in format "HH:MM:SS" or numeric value in HHMMSS.SS format
        """
        try:
            # Check if we're receiving a formatted time string
            if isinstance(gps_time, str) and ":" in gps_time:
                # Parse HH:MM:SS format
                time_parts = gps_time.split(":")
                self.hours = int(time_parts[0])
                self.minutes = int(time_parts[1])
                self.seconds = int(time_parts[2])
            else:
                # Handle numeric time value
                if isinstance(gps_time, (int, float)):
                    # Parse HHMMSS.SS format
                    self.hours = int(gps_time / 10000)
                    self.minutes = int((gps_time - self.hours * 10000) / 100)
                    self.seconds = int(gps_time - self.hours * 10000 - self.minutes * 100)
                else:
                    print(f"Unknown time format: {type(gps_time)} - {gps_time}")
                
        except Exception as e:
            print(f"Error parsing time: {e}")
        
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
    
    # Set app icon
    app_icon = QIcon('balloon_icon.png')
    app.setWindowIcon(app_icon)
    
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
    window.setWindowIcon(app_icon)  # Also set icon for the window
    window.show()
    sys.exit(app.exec_())
