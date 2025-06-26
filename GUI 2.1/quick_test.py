#!/usr/bin/env python3
"""Test the main application quickly"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    from main import GroundStationApp
    from PyQt5.QtWidgets import QApplication
    
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    
    print("Creating GroundStationApp...")
    window = GroundStationApp()
    window.show()
    
    print("Testing map controller location detection...")
    window.map_controller.detect_user_location()
    
    print("Application ready. Use the 'Detect My Location' button to test the map.")
    print("The map should now display even if it was blank before.")
    
    # Don't call exec_() so we can return control quickly for testing
    print("Application window shown, check the GUI")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
