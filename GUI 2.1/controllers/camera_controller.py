"""
Camera Controller for ZWO ASI cameras
Handles all camera initialization, configuration, and image capture operations
"""
import os
import sys
import time
import threading
from datetime import datetime

# Import ZWO camera functionality
try:
    import zwoasi
    
    # Initialize camera properly following Camera_Trigger.py pattern
    dll_path = os.path.join(os.path.dirname(__file__), 'ZWO_Trigger', 'ZWO_ASI_LIB', 'lib', 'x64', 'ASICamera2.dll')
    print(f"Attempting to load DLL from: {dll_path}")
    
    # Check if DLL exists
    if not os.path.exists(dll_path):
        print(f"❌ DLL not found at: {dll_path}")
        # List directory contents for debugging
        dll_dir = os.path.dirname(dll_path)
        if os.path.exists(dll_dir):
            print(f"Contents of {dll_dir}: {os.listdir(dll_dir)}")
        else:
            print(f"Directory {dll_dir} does not exist")
        raise ImportError(f"Camera DLL not found at {dll_path}")
    
    try:
        # Check if SDK is already initialized by trying to get camera count
        try:
            num_cameras = zwoasi.get_num_cameras()
            print(f"SDK already initialized, found {num_cameras} cameras")
        except:
            # SDK not initialized yet, initialize it
            print(f"Initializing SDK with DLL: {dll_path}")
            zwoasi.init(dll_path)
            print("✅ ASICamera2.dll loaded successfully in CameraController")
    except Exception as e:
        print(f"❌ Failed to load SDK in CameraController: {e}")
        raise ImportError("Camera SDK not available")
    
    CAMERA_AVAILABLE = True
    print("ZWO Camera module imported successfully in CameraController")

except ImportError as e:
    print(f"ZWO Camera module not available in CameraController: {e}")
    CAMERA_AVAILABLE = False
    zwoasi = None


class CameraController:
    """Handles all ZWO camera operations"""
    
    def __init__(self):
        self.camera = None
        self.camera_info = None
        self.controls = None
        self.available = False
        self.image_counter = 0
        
        # Default camera settings
        self.gain = 150
        self.exposure = 30000  # microseconds
        
        # Initialize camera if available
        if CAMERA_AVAILABLE:
            self.initialize()
    
    def initialize(self):
        """Initialize camera connection and settings"""
        if not CAMERA_AVAILABLE:
            print("Camera SDK not available")
            return False
        
        try:
            # Check for cameras
            num_cameras = zwoasi.get_num_cameras()
            if num_cameras == 0:
                print('No cameras found')
                return False
            
            cameras_found = zwoasi.list_cameras()
            camera_id = 0  # Use first camera
            print(f'CameraController: Using camera #{camera_id}: {cameras_found[camera_id]}')
            
            # Initialize camera object
            self.camera = zwoasi.Camera(camera_id)
            self.camera_info = self.camera.get_camera_property()
            self.controls = self.camera.get_controls()
            
            # Set optimal settings following Camera_Trigger.py
            self.camera.set_control_value(zwoasi.ASI_BANDWIDTHOVERLOAD, 
                                        self.camera.get_controls()['BandWidth']['MinValue'])
            self.camera.disable_dark_subtract()
            
            # Set default control values
            self.apply_settings()
            
            self.available = True
            print("Camera initialized successfully")
            return True
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.available = False
            return False
    
    def apply_settings(self):
        """Apply current gain and exposure settings to camera"""
        if not self.is_available():
            return False
        
        try:
            self.camera.set_control_value(zwoasi.ASI_GAIN, self.gain)
            self.camera.set_control_value(zwoasi.ASI_EXPOSURE, self.exposure)
            self.camera.set_control_value(zwoasi.ASI_WB_B, 99)
            self.camera.set_control_value(zwoasi.ASI_WB_R, 75)
            self.camera.set_control_value(zwoasi.ASI_GAMMA, 50)
            self.camera.set_control_value(zwoasi.ASI_BRIGHTNESS, 50)
            self.camera.set_control_value(zwoasi.ASI_FLIP, 0)
            print(f"Camera settings applied: Gain={self.gain}, Exposure={self.exposure}μs")
            return True
        except Exception as e:
            print(f"Error applying camera settings: {e}")
            return False
    
    def is_available(self):
        """Check if camera is available and initialized"""
        return self.available and self.camera is not None
    
    def set_gain(self, gain):
        """Set camera gain"""
        self.gain = gain
        if self.is_available():
            try:
                self.camera.set_control_value(zwoasi.ASI_GAIN, gain)
                print(f"Camera gain set to: {gain}")
                return True
            except Exception as e:
                print(f"Error setting camera gain: {e}")
                return False
        return False
    
    def set_exposure(self, exposure_microseconds):
        """Set camera exposure in microseconds"""
        self.exposure = exposure_microseconds
        if self.is_available():
            try:
                self.camera.set_control_value(zwoasi.ASI_EXPOSURE, exposure_microseconds)
                print(f"Camera exposure set to: {exposure_microseconds}μs")
                return True
            except Exception as e:
                print(f"Error setting camera exposure: {e}")
                return False
        return False
    
    def set_exposure_ms(self, exposure_milliseconds):
        """Set camera exposure in milliseconds (convenience method)"""
        return self.set_exposure(int(exposure_milliseconds * 1000))
    
    def prepare_for_capture(self):
        """Prepare camera for image capture"""
        if not self.is_available():
            return False
            
        try:
            # Ensure stills mode is enabled
            self.camera.stop_video_capture()
            self.camera.stop_exposure()
            
            # Apply current settings
            self.apply_settings()
            
            # Set image type for RGB capture
            self.camera.set_image_type(zwoasi.ASI_IMG_RGB24)
            
            print("Camera prepared for capture")
            return True
            
        except Exception as e:
            print(f"Error preparing camera for capture: {e}")
            return False
    
    def generate_filename(self, prefix="image"):
        """Generate a unique filename for camera capture"""
        current_time = datetime.utcnow()
        timestamp = current_time.strftime("%Y%m%d_%H-%M-%S")
        self.image_counter += 1
        filename = f"{prefix}_{timestamp}_{self.image_counter:04d}.tiff"
        return filename
    
    def save_control_values(self, filename):
        """Save camera control values to a text file"""
        if not self.is_available():
            return False
            
        try:
            settings = self.camera.get_control_values()
            settings_filename = filename + '.txt'
            with open(settings_filename, 'w') as f:
                for k in sorted(settings.keys()):
                    f.write('%s: %s\n' % (k, str(settings[k])))
            print('Camera settings saved to %s' % settings_filename)
            return True
        except Exception as e:
            print(f'Error saving camera settings: {e}')
            return False
    
    def capture_rgb_image(self, filename=None):
        """Capture RGB image with current settings"""
        if not self.is_available():
            print("Camera not available for capture")
            return False
        
        if filename is None:
            filename = self.generate_filename("balloon_tracking")
        
        try:
            if not self.prepare_for_capture():
                print("Failed to prepare camera for capture")
                return False
            
            print(f"Capturing RGB image: {filename}")
            print(f"Camera settings - Gain: {self.gain}, Exposure: {self.exposure}μs")
            
            # Capture the image
            self.camera.capture(filename=filename)
            
            # Save settings
            self.save_control_values(filename)
            
            print(f"✅ Image captured successfully: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error during image capture: {e}")
            return False
    
    def capture_rgb_image_async(self, filename=None, callback=None):
        """Capture RGB image asynchronously to avoid blocking UI"""
        def capture_thread():
            try:
                success = self.capture_rgb_image(filename)
                if callback:
                    callback(success, filename)
            except Exception as e:
                print(f"Error in async capture: {e}")
                if callback:
                    callback(False, filename)
        
        # Start capture in new thread
        threading.Thread(target=capture_thread, daemon=True).start()
    
    def get_camera_info(self):
        """Get camera information"""
        if not self.is_available():
            return {
                'available': False,
                'name': 'No Camera',
                'status': 'Not Available'
            }
        
        try:
            return {
                'available': True,
                'name': self.camera_info.get('Name', 'Unknown Camera'),
                'status': 'Ready',
                'gain': self.gain,
                'exposure_us': self.exposure,
                'exposure_ms': self.exposure / 1000.0,
                'controls': self.controls
            }
        except Exception as e:
            return {
                'available': False,
                'name': 'Camera Error',
                'status': f'Error: {e}'
            }
    
    def test_capture(self):
        """Perform a test capture with current settings"""
        filename = self.generate_filename("test_capture")
        print(f"Performing test capture: {filename}")
        return self.capture_rgb_image(filename)
    
    def get_available_controls(self):
        """Get available camera controls"""
        if not self.is_available():
            return {}
        
        try:
            return self.camera.get_controls()
        except Exception as e:
            print(f"Error getting camera controls: {e}")
            return {}
    
    def set_control_value(self, control_type, value):
        """Set a specific camera control value"""
        if not self.is_available():
            return False
        
        try:
            self.camera.set_control_value(control_type, value)
            print(f"Camera control {control_type} set to {value}")
            return True
        except Exception as e:
            print(f"Error setting camera control {control_type}: {e}")
            return False


# Create a dummy function for when camera is not available
def RGB_photo(filename, gain, exposure):
    """Dummy function for when camera is not available"""
    if CAMERA_AVAILABLE:
        # This shouldn't be called if we're using the controller properly
        print(f"Warning: RGB_photo called directly instead of using CameraController")
        print(f"Would capture RGB: {filename} with gain={gain}, exposure={exposure}")
    else:
        print(f"CAMERA NOT AVAILABLE - Would capture RGB: {filename} with gain={gain}, exposure={exposure}")
