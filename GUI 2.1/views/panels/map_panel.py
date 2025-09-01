import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QComboBox, QGroupBox, QSizePolicy, QCheckBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot, QUrl, Qt, QTimer, pyqtSignal
import webbrowser  # For Open in Google Maps

# Working MAP_HTML from gui.py - proven to work
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
        var map = L.map('map').setView([45.5017, -73.5673], 13);
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
        
        var followMarker = false;  // Disable auto-follow by default
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
                        if (channel.objects.handler) {
                            channel.objects.handler.onLocationReceived(lat, lon);
                        }
                    });
                }, function(error) {
                    console.error("Geolocation error:", error);
                    // Notify Python of the error
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        if (channel.objects.handler) {
                            channel.objects.handler.onLocationError(error.message);
                        }
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
    </script>
</body>
</html>
"""

class LocationHandler(QObject):
    """Handler for JavaScript-Python communication - based on working gui.py implementation"""
    
    def __init__(self, map_panel_ref):
        super().__init__()
        self.map_panel = map_panel_ref
    
    @pyqtSlot(float, float)
    def onLocationReceived(self, lat, lon):
        """Callback when HTML5 geolocation succeeds"""
        print(f"LocationHandler: HTML5 geolocation received: {lat:.6f}, {lon:.6f}")
        self.map_panel.user_lat = lat
        self.map_panel.user_lon = lon
        self.map_panel.init_user_marker()
        # Notify the map controller
        self.map_panel.map_controller.set_user_location(lat, lon)
    
    @pyqtSlot(str)
    def onLocationError(self, error):
        """Callback when HTML5 geolocation fails"""
        print(f"LocationHandler: HTML5 geolocation error: {error}")
        # Fall back to IP geolocation
        self.map_panel.map_controller.detect_user_location()


class MapPanel(QWidget):
    """Panel for displaying the map, based on working gui.py implementation"""
    
    def __init__(self, map_controller, telemetry_model, settings_model, parent=None):
        super().__init__(parent)
        self.map_controller = map_controller
        self.telemetry_model = telemetry_model
        self.settings_model = settings_model
        
        # Initialize location variables
        self.user_lat = None
        self.user_lon = None
        self.last_gps_lat = None
        self.last_gps_lon = None
        
        self.setup_ui()
        
        # Connect signals from models/controllers
        self.telemetry_model.position_updated.connect(self.update_vehicle_marker)
        self.telemetry_model.ground_station_gps_updated.connect(self.update_ground_station_gps)
        self.map_controller.user_location_changed.connect(self.update_user_marker)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Map controls
        map_controls_layout = QHBoxLayout()
        
        # Vehicle GPS info
        self.gps_label = QLabel("Vehicle GPS: No Fix")
        self.gps_label.setStyleSheet(
            "background-color: #2a2a2a; color: #ff6b6b; padding: 8px 12px; "
            "border: 1px solid #3a3a3a; border-radius: 6px; font-family: 'Courier New'; "
            "font-size: 10pt; font-weight: bold; min-width: 280px;"
        )
        map_controls_layout.addWidget(self.gps_label)
        
        # Ground Station GPS info
        self.gs_gps_label = QLabel("Ground Station GPS: No Fix")
        self.gs_gps_label.setStyleSheet(
            "background-color: #2a2a2a; color: #ff6b6b; padding: 8px 12px; "
            "border: 1px solid #3a3a3a; border-radius: 6px; font-family: 'Courier New'; "
            "font-size: 10pt; font-weight: bold; min-width: 280px;"
        )
        map_controls_layout.addWidget(self.gs_gps_label)
        
        map_controls_layout.addStretch()
        
        self.follow_marker_checkbox = QCheckBox("Lock on Vehicle")
        self.follow_marker_checkbox.setChecked(False)  # Disable auto-follow by default
        self.follow_marker_checkbox.stateChanged.connect(self.toggle_map_follow)
        map_controls_layout.addWidget(self.follow_marker_checkbox)
        
        # Use HTML5 geolocation button
        detect_location_button = QPushButton("Detect My Location (HTML5)")
        detect_location_button.clicked.connect(self.detect_html5_location)
        map_controls_layout.addWidget(detect_location_button)
        
        # IP geolocation fallback button
        ip_location_button = QPushButton("Detect via IP")
        ip_location_button.clicked.connect(self.map_controller.detect_user_location)
        map_controls_layout.addWidget(ip_location_button)

        open_gmaps_button = QPushButton("Open in Google Maps")
        open_gmaps_button.clicked.connect(self.open_vehicle_in_google_maps)
        map_controls_layout.addWidget(open_gmaps_button)
        
        layout.addLayout(map_controls_layout)
        
        # Web view for map
        self.map_view = QWebEngineView()
        layout.addWidget(self.map_view)
        
        # Initialize map after UI is set up
        self.initialize_map()

    def initialize_map(self):
        """Initialize the map with WebChannel - based on working gui.py implementation"""
        try:
            # Set up web channel for JavaScript communication (like gui.py)
            self.channel = QWebChannel()
            self.location_handler = LocationHandler(self)
            self.channel.registerObject("handler", self.location_handler)
            self.map_view.page().setWebChannel(self.channel)
            
            # Load the HTML
            self.map_view.setHtml(MAP_HTML)
            print("MapPanel: Map HTML loaded with WebChannel")
            
        except Exception as e:
            print(f"MapPanel: Error initializing map: {e}")

    def detect_html5_location(self):
        """Trigger HTML5 geolocation"""
        js_code = "getCurrentPosition();"
        self.map_view.page().runJavaScript(js_code)
        print("MapPanel: HTML5 geolocation requested")

    def init_user_marker(self):
        """Initialize the user's location marker on the map - from gui.py"""
        if self.user_lat is not None and self.user_lon is not None:
            try:
                print(f"MapPanel: Setting user marker at: {self.user_lat:.6f}, {self.user_lon:.6f}")
                
                # Use runJavaScript as in gui.py
                js_code = f"updateUserMarker({self.user_lat}, {self.user_lon});"
                self.map_view.page().runJavaScript(js_code)
                
                # No longer automatically center map - let user control this
                # js_code = f"map.setView([{self.user_lat}, {self.user_lon}], 13);"
                # self.map_view.page().runJavaScript(js_code)
                
            except Exception as e:
                print(f"MapPanel: Error setting user marker: {e}")

    def update_vehicle_marker(self, lat, lon, alt):
        """Update vehicle marker position - based on gui.py update_map_marker"""
        if lat != 0 and lon != 0:  # Only update if we have valid coordinates
            # Only update if position actually changed
            if (self.last_gps_lat, self.last_gps_lon) != (lat, lon):
                self.last_gps_lat, self.last_gps_lon = lat, lon
                try:
                    # Update map marker using the working JavaScript function
                    js_code = f"updateMarker({lat}, {lon});"
                    self.map_view.page().runJavaScript(js_code)
                except Exception as e:
                    print(f"MapPanel: Error updating vehicle marker: {e}")
            # ...existing code for updating GPS label...
            lat_direction = "N" if lat >= 0 else "S"
            lon_direction = "E" if lon >= 0 else "W"
            self.gps_label.setText(
                f"Vehicle: {abs(lat):.5f}°{lat_direction}, {abs(lon):.5f}°{lon_direction} | Alt: {alt:.1f}m"
            )
            self.gps_label.setStyleSheet(
                "background-color: #2a2a2a; color: #00ff00; padding: 8px 12px; "
                "border: 1px solid #3a3a3a; border-radius: 6px; font-family: 'Courier New'; "
                "font-size: 10pt; font-weight: bold; min-width: 280px;"
            )
        else:
            self.gps_label.setText("Vehicle GPS: No Fix / Invalid Data")
            self.gps_label.setStyleSheet(
                "background-color: #2a2a2a; color: #ff6b6b; padding: 8px 12px; "
                "border: 1px solid #3a3a3a; border-radius: 6px; font-family: 'Courier New'; "
                "font-size: 10pt; font-weight: bold; min-width: 280px;"
            )

    def update_ground_station_gps(self, lat, lon, alt):
        """Update ground station GPS information display"""
        if lat != 0 and lon != 0:  # Only update if we have valid coordinates
            # Format coordinates with cardinal directions
            lat_direction = "N" if lat >= 0 else "S"
            lon_direction = "E" if lon >= 0 else "W"
            
            # Update display text
            self.gs_gps_label.setText(
                f"Ground Station: {abs(lat):.5f}°{lat_direction}, {abs(lon):.5f}°{lon_direction} | Alt: {alt:.1f}m"
            )
            # Green background for valid GPS
            self.gs_gps_label.setStyleSheet(
                "background-color: #2a2a2a; color: #00ff00; padding: 8px 12px; "
                "border: 1px solid #3a3a3a; border-radius: 6px; font-family: 'Courier New'; "
                "font-size: 10pt; font-weight: bold; min-width: 280px;"
            )
        else:
            self.gs_gps_label.setText("Ground Station GPS: No Fix / Invalid Data")
            # Red background for no GPS fix
            self.gs_gps_label.setStyleSheet(
                "background-color: #2a2a2a; color: #ff6b6b; padding: 8px 12px; "
                "border: 1px solid #3a3a3a; border-radius: 6px; font-family: 'Courier New'; "
                "font-size: 10pt; font-weight: bold; min-width: 280px;"
            )

    def update_user_marker(self, lat, lon):
        """Update user marker from map controller"""
        self.user_lat, self.user_lon = lat, lon
        self.init_user_marker()

    def toggle_map_follow(self, state):
        """Toggle map following mode"""
        follow = "true" if state == Qt.Checked else "false"
        js_code = f"setFollowMarker({follow});"
        self.map_view.page().runJavaScript(js_code)

    def open_vehicle_in_google_maps(self):
        """Open vehicle location in Google Maps"""
        if self.last_gps_lat is not None and self.last_gps_lon is not None:
            url = f"https://www.google.com/maps?q={self.last_gps_lat},{self.last_gps_lon}"
            webbrowser.open(url)
        else:
            print("MapPanel: No vehicle GPS data to open in Google Maps.")