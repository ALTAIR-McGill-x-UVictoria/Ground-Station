"""
Mount Controller for Celestron telescope mounts
Handles all mount communication and positioning operations
"""
import time
import threading
import math

# Celestron mount control
try:
    import nexstar as ns
    NEXSTAR_AVAILABLE = True
    print("Nexstar module imported successfully in MountController")
except ImportError as e:
    print(f"Nexstar module not available in MountController: {e}")
    NEXSTAR_AVAILABLE = False


class MountController:
    """Handles all Celestron mount operations"""
    
    def __init__(self, default_port="COM10"):
        self.mount = None
        self.default_port = default_port
        self.current_port = default_port
        self.connected = False
        
        # Position tracking
        self.current_azimuth = 0.0
        self.current_altitude = 0.0
        self.target_azimuth = 0.0
        self.target_altitude = 0.0
        
        # Smart positioning to prevent oscillation
        self.last_sent_azimuth = None
        self.last_sent_altitude = None
        self.position_tolerance = 0.5  # degrees - minimum change required to send new position
        self.mount_settled_tolerance = 0.2  # degrees - tolerance for considering mount "at target"
        self.mount_at_target = False
        
        # Port getter function (set by parent)
        self.port_getter_func = None
        
        # Initialize connection
        self.connect()
    
    def set_port_getter(self, port_getter_func):
        """Set a function that returns the currently selected mount port"""
        self.port_getter_func = port_getter_func
    
    def get_current_port(self):
        """Get the current mount port, either from the getter function or the default"""
        if self.port_getter_func:
            try:
                return self.port_getter_func()
            except:
                pass
        return self.current_port
    
    def connect(self):
        """Connect to Celestron mount"""
        if not NEXSTAR_AVAILABLE:
            print("Nexstar module not available - mount control disabled")
            return False
            
        try:
            self.current_port = self.get_current_port()
            print(f"Attempting to connect to Celestron mount on {self.current_port}...")
            self.mount = ns.NexstarHandController(self.current_port)
            
            # Test connection by getting mount model
            try:
                model = self.mount.getModel()
                print(f"✓ Mount connected successfully! Model: {model}")
                self.connected = True
                return True
            except Exception as e:
                print(f"✗ Mount connection test failed: {e}")
                self.connected = False
                self.mount = None
                return False
                
        except Exception as e:
            print(f"✗ Failed to connect to mount: {e}")
            self.connected = False
            self.mount = None
            return False
    
    def reconnect(self):
        """Reconnect to mount with current port selection"""
        if self.connected and self.mount:
            try:
                # Close current connection
                self.mount.close() if hasattr(self.mount, 'close') else None
            except:
                pass
        
        self.mount = None
        self.connected = False
        return self.connect()
    
    def is_connected(self):
        """Check if mount is connected"""
        return self.connected and self.mount is not None
    
    def get_position(self):
        """Get current mount position"""
        if not self.is_connected():
            return None, None
            
        try:
            az, alt = self.mount.getPosition(
                coordinateMode=ns.NexstarCoordinateMode.AZM_ALT,
                highPrecisionFlag=True
            )
            self.current_azimuth = az
            self.current_altitude = alt
            return az, alt
            
        except Exception as e:
            print(f"Error getting mount position: {e}")
            return None, None
    
    def is_moving(self):
        """Check if mount is currently moving"""
        if not self.is_connected():
            return False
            
        try:
            return self.mount.getGotoInProgress()
        except Exception as e:
            print(f"Error checking mount movement: {e}")
            return False
    
    def move_to_position(self, azimuth, altitude):
        """Move mount to specific azimuth/altitude position"""
        if not self.is_connected():
            print("Mount not connected - cannot move")
            return False
            
        try:
            print(f"Moving mount to: Az={azimuth:.2f}°, Alt={altitude:.2f}°")
            
            self.mount.gotoPosition(
                firstCoordinate=azimuth,
                secondCoordinate=altitude,
                coordinateMode=ns.NexstarCoordinateMode.AZM_ALT,
                highPrecisionFlag=True
            )
            
            self.target_azimuth = azimuth
            self.target_altitude = altitude
            return True
            
        except Exception as e:
            print(f"Error moving mount: {e}")
            return False
    
    def move_to_position_precise(self, azimuth, altitude, precision_threshold=1.0):
        """
        Move mount to specific azimuth/altitude position with precision control
        Uses optimized approach to reduce overshooting without blocking UI
        """
        if not self.is_connected():
            print("Mount not connected - cannot move")
            return False
        
        try:
            # Get current position
            current_az, current_alt = self.get_position()
            if current_az is None or current_alt is None:
                print("Cannot get current position - using direct move")
                return self.move_to_position(azimuth, altitude)
            
            # Calculate distance to target
            az_diff = azimuth - current_az
            alt_diff = altitude - current_alt
            
            # Handle azimuth wraparound
            if az_diff > 180:
                az_diff -= 360
            elif az_diff < -180:
                az_diff += 360
            
            total_distance = math.sqrt(az_diff**2 + alt_diff**2)
            print(f"Current: Az={current_az:.2f}°, Alt={current_alt:.2f}°")
            print(f"Target: Az={azimuth:.2f}°, Alt={altitude:.2f}°")
            print(f"Distance: {total_distance:.2f}°")
            
            # If we're already close enough, don't move
            if total_distance < 0.1:
                print("Already at target position")
                return True
            
            # For large movements (>15°), use a single intermediate step approach
            if total_distance > 15.0:
                print("Large movement detected - using intermediate positioning")
                return self._intermediate_movement(current_az, current_alt, azimuth, altitude)
            
            # For medium movements (5-15°), use approach with lower precision
            elif total_distance > 5.0:
                print("Medium movement detected - using reduced precision")
                return self._reduced_precision_movement(azimuth, altitude)
            
            # For small movements (<5°), use direct precise movement
            else:
                print("Small movement detected - using direct precise movement")
                return self._direct_precise_movement(azimuth, altitude)
                
        except Exception as e:
            print(f"Error in precise movement: {e}")
            # Fallback to direct movement
            return self.move_to_position(azimuth, altitude)
    
    def _intermediate_movement(self, start_az, start_alt, target_az, target_alt):
        """Move to intermediate point then final target (non-blocking)"""
        try:
            az_diff = target_az - start_az
            alt_diff = target_alt - start_alt
            
            # Handle azimuth wraparound
            if az_diff > 180:
                az_diff -= 360
            elif az_diff < -180:
                az_diff += 360
            
            # Move to 80% of the way to reduce final overshoot
            intermediate_az = start_az + (az_diff * 0.8)
            intermediate_alt = start_alt + (alt_diff * 0.8)
            
            # Normalize azimuth
            while intermediate_az < 0:
                intermediate_az += 360
            while intermediate_az >= 360:
                intermediate_az -= 360
            
            # Clamp altitude
            intermediate_alt = max(-90, min(90, intermediate_alt))
            
            print(f"Intermediate positioning to Az={intermediate_az:.2f}°, Alt={intermediate_alt:.2f}°")
            
            # Move to intermediate position first
            success = self.move_to_position(intermediate_az, intermediate_alt)
            if not success:
                return False
            
            # Schedule final movement after a delay (non-blocking)
            def final_move():
                time.sleep(3)  # Wait for intermediate movement to settle
                print(f"Final positioning to Az={target_az:.2f}°, Alt={target_alt:.2f}°")
                self._reduced_precision_movement(target_az, target_alt)
            
            # Run final movement in separate thread to avoid blocking UI
            threading.Thread(target=final_move, daemon=True).start()
            return True
            
        except Exception as e:
            print(f"Error in intermediate movement: {e}")
            return False
    
    def _reduced_precision_movement(self, azimuth, altitude):
        """Movement with reduced precision to minimize overshoot"""
        try:
            print(f"Reduced precision movement to Az={azimuth:.2f}°, Alt={altitude:.2f}°")
            
            self.mount.gotoPosition(
                firstCoordinate=azimuth,
                secondCoordinate=altitude,
                coordinateMode=ns.NexstarCoordinateMode.AZM_ALT,
                highPrecisionFlag=False  # Use lower precision to reduce overshoot
            )
            
            self.target_azimuth = azimuth
            self.target_altitude = altitude
            return True
            
        except Exception as e:
            print(f"Error in reduced precision movement: {e}")
            return False
    
    def _direct_precise_movement(self, azimuth, altitude):
        """Direct movement for small adjustments with verification"""
        try:
            # Use lower precision flag for small movements to reduce overshooting
            print(f"Direct precise movement to Az={azimuth:.2f}°, Alt={altitude:.2f}°")
            
            self.mount.gotoPosition(
                firstCoordinate=azimuth,
                secondCoordinate=altitude,
                coordinateMode=ns.NexstarCoordinateMode.AZM_ALT,
                highPrecisionFlag=False  # Use lower precision for small movements
            )
            
            self.target_azimuth = azimuth
            self.target_altitude = altitude
            return True
            
        except Exception as e:
            print(f"Error in direct precise movement: {e}")
            return False
    
    def should_send_new_position(self, target_az, target_alt):
        """Determine if we should send a new position to the mount"""
        # If we've never sent a position, send it
        if self.last_sent_azimuth is None or self.last_sent_altitude is None:
            return True
        
        # Calculate change from last sent position
        az_change = abs(target_az - self.last_sent_azimuth)
        alt_change = abs(target_alt - self.last_sent_altitude)
        
        # Handle azimuth wraparound (359° to 1° is only 2° change, not 358°)
        if az_change > 180:
            az_change = 360 - az_change
        
        # Check if change is significant enough
        significant_change = (az_change >= self.position_tolerance or 
                            alt_change >= self.position_tolerance)
        
        if significant_change:
            print(f"Significant position change detected: Az Δ{az_change:.2f}°, Alt Δ{alt_change:.2f}°")
            return True
        
        # Check if mount is still moving to the last target
        if self.is_moving():
            return False  # Don't send new position while moving
        
        # Check if mount is at the target position
        current_az, current_alt = self.get_position()
        if current_az is not None and current_alt is not None:
            az_error = abs(current_az - target_az)
            alt_error = abs(current_alt - target_alt)
            
            # Handle azimuth wraparound
            if az_error > 180:
                az_error = 360 - az_error
                
            if az_error <= self.mount_settled_tolerance and alt_error <= self.mount_settled_tolerance:
                if not self.mount_at_target:
                    print(f"Mount reached target position within tolerance (Az±{az_error:.2f}°, Alt±{alt_error:.2f}°)")
                    self.mount_at_target = True
                return False  # Mount is at target, don't send again
            else:
                self.mount_at_target = False
        
        return False
    
    def update_last_sent_position(self, azimuth, altitude):
        """Update the last sent position tracking"""
        self.last_sent_azimuth = azimuth
        self.last_sent_altitude = altitude
        self.mount_at_target = False  # Reset since we're sending a new position
    
    def set_position_tolerance(self, tolerance_degrees):
        """Set the minimum position change required to send new coordinates"""
        self.position_tolerance = max(0.1, tolerance_degrees)  # Minimum 0.1 degrees
        print(f"Position tolerance set to {self.position_tolerance:.1f}°")
    
    def set_settled_tolerance(self, tolerance_degrees):
        """Set the tolerance for considering the mount 'at target'"""
        self.mount_settled_tolerance = max(0.1, tolerance_degrees)  # Minimum 0.1 degrees
        print(f"Mount settled tolerance set to {self.mount_settled_tolerance:.1f}°")
    
    def force_move_to_position(self, azimuth, altitude):
        """Force the mount to move to a new position regardless of tolerances"""
        print(f"Force positioning to Az={azimuth:.2f}°, Alt={altitude:.2f}°")
        self.last_sent_azimuth = azimuth  # Reset to force movement
        self.last_sent_altitude = altitude
        return self.move_to_position(azimuth, altitude)
    
    def get_status_info(self):
        """Get comprehensive status information"""
        if not self.is_connected():
            return {
                'connected': False,
                'status': 'Disconnected',
                'current_az': None,
                'current_alt': None,
                'target_az': self.target_azimuth,
                'target_alt': self.target_altitude,
                'is_moving': False,
                'at_target': False
            }
        
        current_az, current_alt = self.get_position()
        is_moving = self.is_moving()
        
        return {
            'connected': True,
            'status': 'Moving' if is_moving else 'Ready',
            'current_az': current_az,
            'current_alt': current_alt,
            'target_az': self.target_azimuth,
            'target_alt': self.target_altitude,
            'is_moving': is_moving,
            'at_target': self.mount_at_target,
            'port': self.current_port
        }
