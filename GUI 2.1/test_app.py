#!/usr/bin/env python3
"""Test script to run the application and test map functionality"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test if all imports work"""
    try:
        print("Testing imports...")
        from PyQt5.QtWidgets import QApplication
        print("✓ PyQt5.QtWidgets imported")
        
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        print("✓ PyQt5.QtWebEngineWidgets imported")
        
        from views.panels.map_panel import MapPanel
        print("✓ MapPanel imported")
        
        from main import GroundStationApp
        print("✓ GroundStationApp imported")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_application():
    """Test running the application"""
    try:
        print("\nTesting application startup...")
        from PyQt5.QtWidgets import QApplication
        from main import GroundStationApp
        
        # Create QApplication
        app = QApplication(sys.argv)
        print("✓ QApplication created")
        
        # Create main window
        window = GroundStationApp()
        print("✓ GroundStationApp created")
        
        # Show window
        window.show()
        print("✓ Window shown")
        
        # Test location detection
        print("Testing location detection...")
        window.map_controller.detect_user_location()
        print("✓ Location detection called")
        
        print("\n✓ All tests passed!")
        print("The application should now be running.")
        print("Try clicking 'Detect My Location' to test the map.")
        
        # Don't call app.exec_() so the script can exit
        return True
        
    except Exception as e:
        print(f"✗ Application error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Ground Station Test Script")
    print("=" * 30)
    
    if test_imports():
        test_application()
    else:
        print("Import test failed, cannot proceed.")
