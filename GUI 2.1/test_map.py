#!/usr/bin/env python3
"""Simple test script to debug map initialization"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot, QUrl, QTimer, pyqtSignal

class TestMapHandler(QObject):
    jsMapReady = pyqtSignal()
    
    @pyqtSlot()
    def jsMapReady(self):
        print("TestMapHandler: Map ready signal received!")

class TestMapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Test")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Test button
        test_btn = QPushButton("Test Map Functions")
        test_btn.clicked.connect(self.test_map_functions)
        layout.addWidget(test_btn)
        
        # Web view
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        # Setup map
        self.map_ready = False
        self.setup_map()
        
    def setup_map(self):
        # Simple map HTML
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                html, body, #map { height: 100%; margin: 0; padding: 0; }
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                console.log('Starting map initialization...');
                var map = L.map('map').setView([45.5, -73.6], 13);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
                
                var handler = null;
                
                function initWebChannel() {
                    console.log('initWebChannel called');
                    console.log('QWebChannel:', typeof QWebChannel);
                    console.log('qt:', typeof qt);
                    
                    if (typeof QWebChannel !== 'undefined' && typeof qt !== 'undefined') {
                        new QWebChannel(qt.webChannelTransport, function(channel) {
                            console.log('WebChannel connected, objects:', Object.keys(channel.objects));
                            handler = channel.objects.test_handler;
                            if (handler && handler.jsMapReady) {
                                console.log('Calling jsMapReady');
                                handler.jsMapReady();
                            }
                        });
                    } else {
                        console.error('WebChannel not available');
                    }
                }
                
                function testFunction() {
                    console.log('Test function called from Python!');
                    return 'success';
                }
                
                setTimeout(initWebChannel, 100);
                setTimeout(initWebChannel, 1000);
                
                console.log('Map setup complete');
            </script>
        </body>
        </html>
        """
        
        # Setup WebChannel
        self.handler = TestMapHandler()
        self.handler.jsMapReady.connect(self.on_map_ready)
        
        self.web_channel = QWebChannel()
        self.web_view.page().setWebChannel(self.web_channel)
        self.web_channel.registerObject("test_handler", self.handler)
        
        # Load HTML
        self.web_view.setHtml(html, QUrl("qrc://"))
        
        # Force ready after timeout
        QTimer.singleShot(3000, self.force_ready)
    
    def on_map_ready(self):
        print("Map ready callback triggered!")
        self.map_ready = True
    
    def force_ready(self):
        if not self.map_ready:
            print("Forcing map ready state...")
            self.map_ready = True
    
    def test_map_functions(self):
        print("Testing map functions...")
        js_code = """
            console.log('Running test from Python');
            if (typeof testFunction === 'function') {
                console.log('testFunction result:', testFunction());
            } else {
                console.log('testFunction not available');
            }
            console.log('Map object:', typeof map);
            console.log('L object:', typeof L);
        """
        self.web_view.page().runJavaScript(js_code, self.js_callback)
    
    def js_callback(self, result):
        print(f"JavaScript callback result: {result}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestMapWindow()
    window.show()
    sys.exit(app.exec_())
