import win32com.client

try:
    # Connect to ZWO ASCOM Telescope Driver
    mount = win32com.client.Dispatch("ASCOM.ASIMount.Telescope")
    
    # Connect the mount
    mount.Connected = True
    print("✅ Mount connected.")

    # Check if it supports slewing
    if not mount.CanSlew or not mount.CanSlewAsync:
        raise Exception("❌ This mount does not support slewing.")

    # Print current coordinates
    print(f"📍 Current RA: {mount.RightAscension} hrs")
    print(f"📍 Current DEC: {mount.Declination}°")

    # Check if tracking is on
    print(f"🔭 Tracking: {'ON' if mount.Tracking else 'OFF'}")

    # Example: Slew to RA = 10.5 hours, DEC = 25.0 degrees
    target_ra = 10.5      # Hours (0–24)
    target_dec = 25.0     # Degrees (-90 to +90)

    print(f"➡️ Slewing to RA: {target_ra}, DEC: {target_dec}")
    mount.SlewToCoordinates(target_ra, target_dec)
    print("✅ Slew complete.")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    # Disconnect safely
    if 'mount' in locals() and mount.Connected:
        mount.Connected = False
        print("🔌 Disconnected from mount.")
