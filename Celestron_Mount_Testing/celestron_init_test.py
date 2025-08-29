import nexstar as ns
import time
import sys

def main():
    """
    Test program for Nexstar mount communication on COM10
    """
    try:
        # Initialize the mount connection
        print("Initializing Nexstar mount on COM10...")
        mount = ns.NexstarHandController("COM10")
        print("✓ Mount connected successfully!")
        
        # Test 1: Get mount model
        print("\n--- Test 1: Getting mount model ---")
        try:
            model = mount.getModel()
            print(f"Mount model: {model}")
            # Try to map to known models
            try:
                model_name = ns.NexstarModel(model).name
                print(f"Model name: {model_name}")
            except ValueError:
                print(f"Unknown model ID: {model}")
        except Exception as e:
            print(f"Error getting model: {e}")
        
        # Test 2: Get firmware version
        print("\n--- Test 2: Getting firmware version ---")
        try:
            version_major, version_minor = mount.getVersion()
            print(f"Firmware version: {version_major}.{version_minor}")
        except Exception as e:
            print(f"Error getting version: {e}")
        
        # Test 3: Get current position (RA/DEC)
        print("\n--- Test 3: Getting current position (RA/DEC) ---")
        try:
            ra, dec = mount.getPosition(ns.NexstarCoordinateMode.RA_DEC, highPrecisionFlag=True)
            print(f"Current RA: {ra:.6f} degrees")
            print(f"Current Dec: {dec:.6f} degrees")
        except Exception as e:
            print(f"Error getting RA/DEC position: {e}")
        
        # Test 4: Get current position (AZM/ALT)
        print("\n--- Test 4: Getting current position (AZM/ALT) ---")
        try:
            azm, alt = mount.getPosition(ns.NexstarCoordinateMode.AZM_ALT, highPrecisionFlag=True)
            print(f"Current Azimuth: {azm:.6f} degrees")
            print(f"Current Altitude: {alt:.6f} degrees")
        except Exception as e:
            print(f"Error getting AZM/ALT position: {e}")
        
        # Test 5: Get tracking mode
        print("\n--- Test 5: Getting tracking mode ---")
        try:
            tracking_mode = mount.getTrackingMode()
            print(f"Tracking mode: {tracking_mode}")
            try:
                mode_name = ns.NexstarTrackingMode(tracking_mode).name
                print(f"Tracking mode name: {mode_name}")
            except ValueError:
                print(f"Unknown tracking mode: {tracking_mode}")
        except Exception as e:
            print(f"Error getting tracking mode: {e}")
        
        # Test 6: Check if mount is aligned
        print("\n--- Test 6: Checking alignment status ---")
        try:
            is_aligned = mount.getAlignmentComplete()
            print(f"Mount aligned: {is_aligned}")
        except Exception as e:
            print(f"Error checking alignment: {e}")
        
        # Test 7: Check if goto is in progress
        print("\n--- Test 7: Checking goto status ---")
        try:
            goto_in_progress = mount.getGotoInProgress()
            print(f"Goto in progress: {goto_in_progress}")
        except Exception as e:
            print(f"Error checking goto status: {e}")
        
        # Test 8: Get location (if available)
        print("\n--- Test 8: Getting location ---")
        try:
            lat, lon = mount.getLocation()
            print(f"Latitude: {lat:.6f} degrees")
            print(f"Longitude: {lon:.6f} degrees")
        except Exception as e:
            print(f"Error getting location: {e}")
        
        # Test 9: Get time/date
        print("\n--- Test 9: Getting time/date ---")
        try:
            mount_time, dst = mount.getTime()
            print(f"Mount time: {mount_time}")
            print(f"DST enabled: {dst}")
        except Exception as e:
            print(f"Error getting time: {e}")
        
        # Test 10: Echo test
        print("\n--- Test 10: Echo test ---")
        try:
            test_byte = 42
            mount.echo(test_byte)
            print(f"Echo test successful (sent byte: {test_byte})")
        except Exception as e:
            print(f"Error in echo test: {e}")
        
        # Test 11: Get device versions
        print("\n--- Test 11: Getting device versions ---")
        for device in ns.NexstarDeviceId:
            try:
                version_major, version_minor = mount.getDeviceVersion(device)
                print(f"{device.name}: version {version_major}.{version_minor}")
            except ns.NexstarPassthroughError as e:
                print(f"{device.name}: {e}")
            except Exception as e:
                print(f"{device.name}: Error - {e}")
        
        print("\n✓ All tests completed!")
        
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

if __name__ == "__main__":
    main()

