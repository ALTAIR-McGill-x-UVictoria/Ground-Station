import nexstar as ns
import time
import sys
import math

def simple_position_override(mount, target_azimuth, target_altitude):
    """
    Simple approach: Use the mount's current physical position as a reference
    and then move relative to where we want to "set" the coordinates
    """
    print(f"Setting position reference: Az={target_azimuth}°, Alt={target_altitude}°")
    
    # Get current physical position
    current_az, current_alt = mount.getPosition(
        coordinateMode=ns.NexstarCoordinateMode.AZM_ALT, 
        highPrecisionFlag=True
    )
    
    print(f"Current physical position: Az={current_az:.4f}°, Alt={current_alt:.4f}°")
    
    # Calculate offset
    az_offset = current_az - target_azimuth
    alt_offset = current_alt - target_altitude
    
    print(f"Calculated offset: Az={az_offset:.4f}°, Alt={alt_offset:.4f}°")
    print("Note: This offset can be used for subsequent relative movements")
    
    return az_offset, alt_offset

def move_to_azalt_position(mount, target_azimuth, target_altitude):
    """
    Direct movement to azimuth/altitude position
    """
    try:
        print(f"Moving directly to: Az={target_azimuth}°, Alt={target_altitude}°")
        
        # Use the azimuth/altitude goto command directly
        mount.gotoPosition(
            firstCoordinate=target_azimuth,
            secondCoordinate=target_altitude,
            coordinateMode=ns.NexstarCoordinateMode.AZM_ALT,
            highPrecisionFlag=True
        )
        
        print("✓ Movement command sent!")
        return True
        
    except Exception as e:
        print(f"Error moving to position: {e}")
        return False

def main():
    """
    Set arbitrary azimuth/altitude position without mount alignment
    """
    try:
        # Initialize the mount connection
        print("Initializing Nexstar mount on COM10...")
        mount = ns.NexstarHandController("COM10")
        print("✓ Mount connected successfully!")
        
        # Set arbitrary azimuth and altitude coordinates (in degrees)
        target_azimuth = 180.0    # 180 degrees (South)
        target_altitude = 45.0    # 45 degrees elevation
        
        print(f"\n--- Target Position ---")
        print(f"Target Azimuth: {target_azimuth}°")
        print(f"Target Altitude: {target_altitude}°")
        
        # Get current position
        print("\n--- Current Position ---")
        try:
            current_az, current_alt = mount.getPosition(
                coordinateMode=ns.NexstarCoordinateMode.AZM_ALT, 
                highPrecisionFlag=True
            )
            print(f"Current Azimuth: {current_az:.4f}°")
            print(f"Current Altitude: {current_alt:.4f}°")
            
        except Exception as e:
            print(f"Error getting current position: {e}")
            return
        
        # Method 1: Direct movement to azimuth/altitude
        print("\n--- Method 1: Direct AZM/ALT Movement ---")
        success = move_to_azalt_position(mount, target_azimuth, target_altitude)
        
        if success:
            # Monitor the movement
            print("\nMonitoring movement...")
            start_time = time.time()
            max_wait_time = 60  # Maximum 60 seconds
            
            while time.time() - start_time < max_wait_time:
                try:
                    az, alt = mount.getPosition(
                        coordinateMode=ns.NexstarCoordinateMode.AZM_ALT, 
                        highPrecisionFlag=True
                    )
                    goto_progress = mount.getGotoInProgress()
                    
                    print(f"  Position: Az={az:.2f}°, Alt={alt:.2f}° | Moving: {goto_progress}")
                    
                    # Check if we've reached the target (within tolerance)
                    az_diff = abs(az - target_azimuth)
                    alt_diff = abs(alt - target_altitude)
                    
                    if not goto_progress and az_diff < 1.0 and alt_diff < 1.0:
                        print(f"✓ Target reached! Final position: Az={az:.2f}°, Alt={alt:.2f}°")
                        break
                    elif not goto_progress:
                        print(f"⚠ Movement stopped. Final position: Az={az:.2f}°, Alt={alt:.2f}°")
                        print(f"  Difference from target: Az={az_diff:.2f}°, Alt={alt_diff:.2f}°")
                        break
                        
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error monitoring position: {e}")
                    break
        
        # Method 2: Position reference setting (for future relative movements)
        print("\n--- Method 2: Setting Position Reference ---")
        az_offset, alt_offset = simple_position_override(mount, target_azimuth, target_altitude)
        
        # Demonstrate relative movement
        print("\n--- Testing Relative Movement ---")
        try:
            # Get current position
            current_az, current_alt = mount.getPosition(
                coordinateMode=ns.NexstarCoordinateMode.AZM_ALT, 
                highPrecisionFlag=True
            )
            
            # Calculate a relative target (10 degrees east, 5 degrees up from our "reference")
            relative_target_az = target_azimuth + 10.0
            relative_target_alt = target_altitude + 5.0
            
            print(f"Moving relative to reference: Az={relative_target_az}°, Alt={relative_target_alt}°")
            
            success = move_to_azalt_position(mount, relative_target_az, relative_target_alt)
            
            if success:
                # Brief monitoring
                for i in range(10):
                    try:
                        az, alt = mount.getPosition(
                            coordinateMode=ns.NexstarCoordinateMode.AZM_ALT, 
                            highPrecisionFlag=True
                        )
                        goto_progress = mount.getGotoInProgress()
                        print(f"  Position: Az={az:.2f}°, Alt={alt:.2f}° | Moving: {goto_progress}")
                        
                        if not goto_progress:
                            break
                            
                        time.sleep(1)
                    except:
                        break
        
        except Exception as e:
            print(f"Error in relative movement test: {e}")
        
        print("\n✓ Position setting test completed!")
        print("\nSummary:")
        print("- Method 1 uses direct azimuth/altitude goto commands")
        print("- Method 2 establishes a position reference for relative movements")
        print("- The mount can move to specific azimuth/altitude coordinates directly")
        print("- No formal star alignment is required for basic positioning")
        
    except Exception as e:
        print(f"✗ Failed to connect to mount: {e}")
        print("Make sure the mount is connected to COM10 and powered on.")
        sys.exit(1)
    
    finally:
        # Clean up connection
        try:
            mount.close()
            print("Connection closed.")
        except:
            pass

def set_azalt_position(azimuth, altitude, port="COM10"):
    """
    Simple helper function to move mount to specific azimuth/altitude
    
    Args:
        azimuth (float): Target azimuth in degrees (0-360)
        altitude (float): Target altitude in degrees (-90 to 90)
        port (str): Serial port for mount connection
    """
    try:
        mount = ns.NexstarHandController(port)
        print(f"Moving to: Az={azimuth}°, Alt={altitude}°")
        
        mount.gotoPosition(
            firstCoordinate=azimuth,
            secondCoordinate=altitude,
            coordinateMode=ns.NexstarCoordinateMode.AZM_ALT,
            highPrecisionFlag=True
        )
        
        # Wait for movement to complete
        while mount.getGotoInProgress():
            az, alt = mount.getPosition(
                coordinateMode=ns.NexstarCoordinateMode.AZM_ALT, 
                highPrecisionFlag=True
            )
            print(f"  Current: Az={az:.1f}°, Alt={alt:.1f}°", end='\r')
            time.sleep(1)
        
        # Final position
        final_az, final_alt = mount.getPosition(
            coordinateMode=ns.NexstarCoordinateMode.AZM_ALT, 
            highPrecisionFlag=True
        )
        print(f"\n✓ Final position: Az={final_az:.2f}°, Alt={final_alt:.2f}°")
        
        mount.close()
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
        
        print("\n✓ Position setting test completed!")
        print("\nSummary:")
        print("- Method 1 uses direct azimuth/altitude goto commands")
        print("- Method 2 establishes a position reference for relative movements")
        print("- The mount can move to specific azimuth/altitude coordinates directly")
        print("- No formal star alignment is required for basic positioning")
        
    except Exception as e:
        print(f"✗ Failed to connect to mount: {e}")
        print("Make sure the mount is connected to COM10 and powered on.")
        sys.exit(1)
    
    finally:
        # Clean up connection
        try:
            mount.close()
            print("Connection closed.")
        except:
            pass

def set_azalt_position(azimuth, altitude, port="COM10"):
    """
    Simple helper function to move mount to specific azimuth/altitude
    
    Args:
        azimuth (float): Target azimuth in degrees (0-360)
        altitude (float): Target altitude in degrees (-90 to 90)
        port (str): Serial port for mount connection
    """
    try:
        mount = ns.NexstarHandController(port)
        print(f"Moving to: Az={azimuth}°, Alt={altitude}°")
        
        mount.gotoPosition(
            firstCoordinate=azimuth,
            secondCoordinate=altitude,
            coordinateMode=ns.NexstarCoordinateMode.AZM_ALT,
            highPrecisionFlag=True
        )
        
        # Wait for movement to complete
        while mount.getGotoInProgress():
            az, alt = mount.getPosition(
                coordinateMode=ns.NexstarCoordinateMode.AZM_ALT, 
                highPrecisionFlag=True
            )
            print(f"  Current: Az={az:.1f}°, Alt={alt:.1f}°", end='\r')
            time.sleep(1)
        
        # Final position
        final_az, final_alt = mount.getPosition(
            coordinateMode=ns.NexstarCoordinateMode.AZM_ALT, 
            highPrecisionFlag=True
        )
        print(f"\n✓ Final position: Az={final_az:.2f}°, Alt={final_alt:.2f}°")
        
        mount.close()
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    main()
