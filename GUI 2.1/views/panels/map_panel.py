import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QComboBox, QGroupBox, QSizePolicy, QCheckBox  # Added QCheckBox here
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot, QUrl, Qt, QTimer  # Added QTimer here
import webbrowser

class LocationHandler(QObject):
    """Handler for JavaScript-Python communication"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.map_panel = parent
    
    @pyqtSlot(str, str)
    def handleMessage(self, msg_type, msg_data):
        """Handle messages from JavaScript"""
        if msg_type == "mapReady":
            self.map_panel.on_map_ready()
        elif msg_type == "markerClick":
            self.map_panel.on_marker_click(msg_data)
        elif msg_type == "mapClick":
            lat, lon = msg_data.split(',')
            self.map_panel.on_map_click(float(lat), float(lon))
        elif msg_type == "error":
            print(f"Map error: {msg_data}")

class MapPanel(QWidget):
    """Panel for displaying the map and location data"""
    
    def __init__(self, map_controller, telemetry_model, parent=None):
        super().__init__(parent)
        self.map_controller = map_controller
        self.telemetry_model = telemetry_model
        
        # Initialize member variables
        self.map_ready = False
        self.fc_path = []  # List of [lat, lon] points for flight path
        self.map_follows_fc = True  # Auto-center map on flight computer
        
        self.setup_ui()
        
        # Connect to model signals
        self.telemetry_model.position_updated.connect(self.update_fc_position)
    
    def setup_ui(self):
        """Set up the map panel UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create top control bar
        controls = QHBoxLayout()
        
        # Map type selector
        map_type_label = QLabel("Map Type:")
        self.map_type = QComboBox()
        self.map_type.addItems(["OpenStreetMap", "Satellite", "Terrain"])
        self.map_type.currentIndexChanged.connect(self.change_map_type)
        controls.addWidget(map_type_label)
        controls.addWidget(self.map_type)
        
        # Follow checkbox
        self.follow_cb = QCheckBox("Follow Flight Computer")
        self.follow_cb.setChecked(self.map_follows_fc)
        self.follow_cb.stateChanged.connect(self.toggle_follow)
        controls.addWidget(self.follow_cb)
        
        # Center on FC button
        self.center_fc_btn = QPushButton("Center on FC")
        self.center_fc_btn.clicked.connect(self.center_on_fc)
        controls.addWidget(self.center_fc_btn)
        
        # Center on user button
        self.center_user_btn = QPushButton("Center on Me")
        self.center_user_btn.clicked.connect(self.center_on_user)
        controls.addWidget(self.center_user_btn)
        
        # Clear path button
        self.clear_path_btn = QPushButton("Clear Path")
        self.clear_path_btn.clicked.connect(self.clear_flight_path)
        controls.addWidget(self.clear_path_btn)
        
        # Google Maps button
        self.gmaps_btn = QPushButton("Open in Google Maps")
        self.gmaps_btn.clicked.connect(self.open_google_maps)
        controls.addWidget(self.gmaps_btn)
        
        # Add controls to layout
        layout.addLayout(controls)
        
        # Create map view
        self.map_view = QWebEngineView()
        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.map_view, 1)
        
        # Set up web channel for communication with JavaScript
        self.channel = QWebChannel()
        self.handler = LocationHandler(self)
        self.channel.registerObject("handler", self.handler)
        self.map_view.page().setWebChannel(self.channel)
        
        # Load the map HTML
        self.load_map()
        
        # Create status bar
        status_bar = QHBoxLayout()
        self.status_label = QLabel("Map loading...")
        self.coordinate_label = QLabel("Coordinates: N/A")
        status_bar.addWidget(self.status_label)
        status_bar.addStretch(1)
        status_bar.addWidget(self.coordinate_label)
        layout.addLayout(status_bar)
    
    def load_map(self):
        """Load the map HTML template"""
        # Create the HTML file if it doesn't exist
        html_path = os.path.join('resources', 'map_template.html')
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        
        if not os.path.exists(html_path):
            self.create_map_template(html_path)
        
        # Load the HTML file
        self.map_view.load(QUrl.fromLocalFile(os.path.abspath(html_path)))
    
    def create_map_template(self, filepath):
        """Create the map HTML template file"""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Flight Computer Tracking</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        html, body, #map {
            height: 100%;
            margin: 0;
            padding: 0;
        }
    </style>
</head>
<body>
    <div id="map"></div>
    
    <script>
        // Initialize map
        var map = L.map('map').setView([45.5017, -73.5673], 13);
        
        // Add default tile layer (OpenStreetMap)
        var osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap contributors</a>'
        }).addTo(map);
        
        // Add satellite layer
        var satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19,
            attribution: 'Imagery &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        });
        
        // Add terrain layer
        var terrain = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
            maxZoom: 17,
            attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
        });
        
        // Create baseMaps object
        var baseMaps = {
            "OpenStreetMap": osm,
            "Satellite": satellite,
            "Terrain": terrain
        };
        
        // Initialize markers
        var fcMarker = null;
        var userMarker = null;
        var flightPath = L.polyline([], {color: 'red', weight: 3}).addTo(map);
        
        // Initialize QWebChannel
        new QWebChannel(qt.webChannelTransport, function(channel) {
            window.handler = channel.objects.handler;
            
            // Send message that map is ready
            handler.handleMessage("mapReady", "");
        });
        
        // Update flight computer marker
        function updateFCMarker(lat, lon, alt, heading) {
            if (fcMarker === null) {
                // Create marker if it doesn't exist
                fcMarker = L.marker([lat, lon]).addTo(map);
                fcMarker.bindPopup("Flight Computer<br>Alt: " + alt.toFixed(1) + "m");
            } else {
                // Update marker position
                fcMarker.setLatLng([lat, lon]);
                fcMarker.getPopup().setContent("Flight Computer<br>Alt: " + alt.toFixed(1) + "m");
            }
            
            // Add point to flight path
            flightPath.addLatLng([lat, lon]);
        }
        
        // Update user marker
        function updateUserMarker(lat, lon) {
            if (userMarker === null) {
                // Create marker if it doesn't exist
                userMarker = L.marker([lat, lon], {
                    icon: L.icon({
                        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34],
                        shadowSize: [41, 41]
                    })
                }).addTo(map);
                userMarker.bindPopup("Ground Station");
            } else {
                // Update marker position
                userMarker.setLatLng([lat, lon]);
            }
            
            return true;
        }
        
        // Change map type
        function setMapType(type) {
            map.removeLayer(osm);
            map.removeLayer(satellite);
            map.removeLayer(terrain);
            
            if (type === "OpenStreetMap") {
                osm.addTo(map);
            } else if (type === "Satellite") {
                satellite.addTo(map);
            } else if (type === "Terrain") {
                terrain.addTo(map);
            }
        }
        
        // Center map on a point
        function centerMap(lat, lon, zoom) {
            map.setView([lat, lon], zoom || map.getZoom());
        }
        
        // Clear flight path
        function clearFlightPath() {
            flightPath.setLatLngs([]);
        }
        
        // Handle map clicks
        map.on('click', function(e) {
            handler.handleMessage("mapClick", e.latlng.lat + "," + e.latlng.lng);
        });
    </script>
</body>
</html>"""
        
        with open(filepath, 'w') as f:
            f.write(html_content)
    
    def on_map_ready(self):
        """Called when the map has finished loading"""
        self.map_ready = True
        self.status_label.setText("Map ready")
        
        # Detect user location
        QTimer.singleShot(500, self.detect_location)
    
    def detect_location(self):
        """Detect user's current location"""
        self.status_label.setText("Detecting location...")
        
        # Use the map controller to detect location
        if self.map_controller.detect_user_location():
            self.status_label.setText("Location detected")
            self.update_user_marker(
                self.map_controller.user_lat,
                self.map_controller.user_lon
            )
        else:
            self.status_label.setText("Using default location (Montreal)")
            # Use default location
            self.update_user_marker(45.5017, -73.5673)
    
    def update_user_marker(self, lat, lon):
        """Update the user's location marker on the map"""
        if not self.map_ready:
            return
            
        js_code = f"updateUserMarker({lat}, {lon});"
        self.map_view.page().runJavaScript(js_code)
    
    def update_fc_position(self, lat, lon, alt):
        """Update the flight computer's position on the map"""
        if not self.map_ready or lat == 0 or lon == 0:
            return
            
        # Add to flight path if valid coordinates
        if lat != 0 and lon != 0:
            self.fc_path.append([lat, lon])
            
        # Update the marker on the map
        js_code = f"updateFCMarker({lat}, {lon}, {alt}, 0);"
        self.map_view.page().runJavaScript(js_code)
        
        # Update coordinate display
        self.coordinate_label.setText(
            f"FC: {lat:.6f}, {lon:.6f}, Alt: {alt:.1f}m"
        )
        
        # Center map on flight computer if follow is enabled
        if self.map_follows_fc:
            self.center_on_fc()
    
    def change_map_type(self, index):
        """Change the map type based on combo box selection"""
        map_type = self.map_type.currentText()
        js_code = f"setMapType('{map_type}');"
        self.map_view.page().runJavaScript(js_code)
    
    def toggle_follow(self, state):
        """Toggle whether map follows the flight computer"""
        self.map_follows_fc = bool(state)
        if self.map_follows_fc:
            self.center_on_fc()
    
    def center_on_fc(self):
        """Center the map on the flight computer"""
        if self.telemetry_model.gps_lat != 0 and self.telemetry_model.gps_lon != 0:
            js_code = f"centerMap({self.telemetry_model.gps_lat}, {self.telemetry_model.gps_lon}, 15);"
            self.map_view.page().runJavaScript(js_code)
    
    def center_on_user(self):
        """Center the map on the user's location"""
        js_code = f"centerMap({self.map_controller.user_lat}, {self.map_controller.user_lon}, 15);"
        self.map_view.page().runJavaScript(js_code)
    
    def clear_flight_path(self):
        """Clear the flight path polyline"""
        self.fc_path = []
        js_code = "clearFlightPath();"
        self.map_view.page().runJavaScript(js_code)
    
    def on_marker_click(self, marker_id):
        """Handle marker click events from JavaScript"""
        # Nothing to do yet
        pass
    
    def on_map_click(self, lat, lon):
        """Handle map click events from JavaScript"""
        self.coordinate_label.setText(f"Selected: {lat:.6f}, {lon:.6f}")
    
    def open_google_maps(self):
        """Open the current flight computer location in Google Maps"""
        if self.telemetry_model.gps_lat != 0 and self.telemetry_model.gps_lon != 0:
            url = f"https://www.google.com/maps?q={self.telemetry_model.gps_lat},{self.telemetry_model.gps_lon}"
            webbrowser.open(url)
            self.status_label.setText("Opened in Google Maps")