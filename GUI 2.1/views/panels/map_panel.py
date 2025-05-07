import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QComboBox, QGroupBox, QSizePolicy, QCheckBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot, QUrl, Qt, QTimer, pyqtSignal
import webbrowser # For Open in Google Maps

# MAP_HTML from gui.py
MAP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        #map { height: 100vh; width: 100%; margin: 0; padding: 0; }
        body { margin: 0; padding: 0; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([0, 0], 2); // Default view
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        
        var vehicleIcon = L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
            iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
        });
        
        var userIcon = L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
            iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
        });
        
        var vehicleMarker = L.marker([0, 0], {icon: vehicleIcon}).addTo(map).bindPopup("Vehicle");
        var userMarker = L.marker([0,0], {icon: userIcon}).addTo(map).bindPopup("Ground Station");
        var pathLine = L.polyline([], { color: 'red', weight: 3, opacity: 0.7 }).addTo(map);
        
        var followVehicleMarker = true;
        var coordinates = [];
        var jsPyComm = null; // For QWebChannel

        // Initialize QWebChannel
        document.addEventListener('DOMContentLoaded', function () {
            if (typeof QWebChannel !== 'undefined') {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    jsPyComm = channel.objects.js_py_handler;
                    if (jsPyComm) {
                        jsPyComm.jsMapReady(); // Notify Python that map is ready
                    } else {
                        console.error("js_py_handler not found in QWebChannel objects.");
                    }
                });
            } else {
                console.error("QWebChannel is not defined. Ensure qwebchannel.js is loaded.");
            }
        });

        function updateVehicleMarker(lat, lon, alt) {
            var newLatLng = L.latLng(lat, lon);
            vehicleMarker.setLatLng(newLatLng);
            vehicleMarker.setPopupContent("Vehicle<br>Lat: " + lat.toFixed(6) + "<br>Lon: " + lon.toFixed(6) + "<br>Alt: " + alt.toFixed(1) + "m");
            coordinates.push(newLatLng);
            pathLine.setLatLngs(coordinates);
            
            if (followVehicleMarker) {
                map.setView(newLatLng);
            }
        }
        
        function updateUserMarker(lat, lon) {
            var newLatLng = L.latLng(lat, lon);
            userMarker.setLatLng(newLatLng);
            userMarker.setPopupContent("Ground Station<br>Lat: " + lat.toFixed(6) + "<br>Lon: " + lon.toFixed(6)).openPopup();
        }
        
        function setFollowVehicle(follow) {
            followVehicleMarker = follow;
        }
        
        function clearPath() {
            coordinates = [];
            pathLine.setLatLngs([]);
        }

        function centerMap(lat, lon, zoom) {
            map.setView([lat, lon], zoom);
        }
    </script>
</body>
</html>
"""

class JsPyHandler(QObject): # Renamed from LocationHandler for clarity
    """Handler for JavaScript-Python communication"""
    # Python to JavaScript signals (if needed)
    # pySignalUpdateVehicleMarker = pyqtSignal(float, float, float) 
    # pySignalUpdateUserMarker = pyqtSignal(float, float)

    # JavaScript to Python slots
    jsMapReady = pyqtSignal()
    jsUserLocationReceived = pyqtSignal(float, float)
    jsUserLocationError = pyqtSignal(str)
    
    def __init__(self, map_panel_ref):
        super().__init__()
        self.map_panel = map_panel_ref # Store a reference to MapPanel

    @pyqtSlot()
    def jsMapReadySlot(self): # Slot to connect to jsMapReady signal
        self.map_panel.on_map_ready()

    @pyqtSlot(float, float)
    def jsUserLocationReceivedSlot(self, lat, lon):
        self.map_panel.on_user_location_received(lat, lon)

    @pyqtSlot(str)
    def jsUserLocationErrorSlot(self, error_message):
        self.map_panel.on_user_location_error(error_message)


class MapPanel(QWidget):
    """Panel for displaying the map, based on gui.py"""
    
    def __init__(self, map_controller, telemetry_model, settings_model, parent=None):
        super().__init__(parent)
        self.map_controller = map_controller
        self.telemetry_model = telemetry_model
        self.settings_model = settings_model # Store settings_model
        
        self.user_lat = None
        self.user_lon = None
        self.last_gps_lat = None
        self.last_gps_lon = None

        self.setup_ui()

        # Connect signals from models/controllers
        self.telemetry_model.position_updated.connect(self.update_vehicle_on_map)
        self.map_controller.user_location_changed.connect(self.update_user_on_map)
        self.map_view.loadFinished.connect(self.initialize_map_interaction)


    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0) # Remove margins for map to fill
        
        # Map controls (similar to gui.py)
        map_controls_layout = QHBoxLayout()
        
        self.gps_label = QLabel("GPS: No Fix")
        self.gps_label.setStyleSheet("background-color: #2a2a2a; color: #ff6b6b; padding: 8px 12px; border: 1px solid #3a3a3a; border-radius: 6px; font-family: 'Courier New'; font-size: 10pt; font-weight: bold; min-width: 280px;")
        map_controls_layout.addWidget(self.gps_label)
        map_controls_layout.addStretch()
        
        self.follow_marker_checkbox = QCheckBox("Lock on Vehicle")
        self.follow_marker_checkbox.setChecked(True)
        self.follow_marker_checkbox.stateChanged.connect(self.toggle_map_follow)
        map_controls_layout.addWidget(self.follow_marker_checkbox)
        
        detect_location_button = QPushButton("Detect My Location")
        detect_location_button.clicked.connect(self.map_controller.detect_user_location) # Call controller
        map_controls_layout.addWidget(detect_location_button)

        open_gmaps_button = QPushButton("Open in Google Maps")
        open_gmaps_button.clicked.connect(self.open_vehicle_in_google_maps)
        map_controls_layout.addWidget(open_gmaps_button)
        
        layout.addLayout(map_controls_layout)
        
        # Web view for map
        self.map_view = QWebEngineView()
        layout.addWidget(self.map_view)

    def initialize_map_interaction(self, success):
        if (success):
            self.js_py_handler = JsPyHandler(self)
            self.js_py_handler.jsMapReady.connect(self.js_py_handler.jsMapReadySlot) # Connect signal to slot
            # self.js_py_handler.jsUserLocationReceived.connect(self.js_py_handler.jsUserLocationReceivedSlot)
            # self.js_py_handler.jsUserLocationError.connect(self.js_py_handler.jsUserLocationErrorSlot)


            self.web_channel = QWebChannel(self.map_view.page())
            self.map_view.page().setWebChannel(self.web_channel)
            self.web_channel.registerObject("js_py_handler", self.js_py_handler)
            
            # Load the HTML after channel is set up
            self.map_view.setHtml(MAP_HTML, QUrl("qrc:/")) # Base URL for qrc if using resources
            print("MapPanel: Map HTML loaded and WebChannel set up.")
        else:
            print("MapPanel: Map page failed to load.")

    def on_map_ready(self):
        print("MapPanel: Map JavaScript reported ready.")
        # Now safe to call JS functions if needed, e.g., initial user location
        self.map_controller.detect_user_location() 


    def update_vehicle_on_map(self, lat, lon, alt):
        if lat != 0 and lon != 0: # Valid coordinates
            self.last_gps_lat, self.last_gps_lon = lat, lon
            self.map_view.page().runJavaScript(f"updateVehicleMarker({lat}, {lon}, {alt});")
            
            lat_dir = "N" if lat >= 0 else "S"
            lon_dir = "E" if lon >= 0 else "W"
            self.gps_label.setText(f"Vehicle: {abs(lat):.5f}°{lat_dir}, {abs(lon):.5f}°{lon_dir} | Alt: {alt:.1f}m")
            self.gps_label.setStyleSheet("background-color: #2a2a2a; color: #00ff00; padding: 8px 12px; border: 1px solid #3a3a3a; border-radius: 6px; font-family: 'Courier New'; font-size: 10pt; font-weight: bold; min-width: 280px;")

        else:
            self.gps_label.setText("GPS: No Fix / Invalid Data")
            self.gps_label.setStyleSheet("background-color: #2a2a2a; color: #ff6b6b; padding: 8px 12px; border: 1px solid #3a3a3a; border-radius: 6px; font-family: 'Courier New'; font-size: 10pt; font-weight: bold; min-width: 280px;")


    def update_user_on_map(self, lat, lon):
        self.user_lat, self.user_lon = lat, lon
        self.map_view.page().runJavaScript(f"updateUserMarker({lat}, {lon});")
        # Optionally center map on user if it's the first time
        # self.map_view.page().runJavaScript(f"centerMap({lat}, {lon}, 13);")


    def toggle_map_follow(self, state):
        follow = "true" if state == Qt.Checked else "false"
        self.map_view.page().runJavaScript(f"setFollowVehicle({follow});")

    def open_vehicle_in_google_maps(self):
        if self.last_gps_lat is not None and self.last_gps_lon is not None:
            url = f"https://www.google.com/maps?q={self.last_gps_lat},{self.last_gps_lon}"
            webbrowser.open(url)
        else:
            print("MapPanel: No vehicle GPS data to open in Google Maps.")

    # Slots for JsPyHandler signals (if JsPyHandler emits signals to be caught by MapPanel)
    def on_user_location_received(self, lat, lon):
        self.map_controller.set_user_location(lat,lon)

    def on_user_location_error(self, error_message):
        print(f"MapPanel: User geolocation error: {error_message}")
        # Fallback or notify user