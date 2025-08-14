try:
    import win32com.client
    ASCOM_AVAILABLE = True
except ImportError:
    ASCOM_AVAILABLE = False
    print("❌ ASCOM/win32com not available. Telescope functionality will be disabled.")

class TelescopeController:
    def __init__(self):
        self.mount = None
        self.connected = False
        self.ascom_available = ASCOM_AVAILABLE

    def connect(self):
        if not self.ascom_available:
            print("❌ ASCOM not available. Cannot connect to telescope.")
            return False
            
        if not self.connected:
            try:
                self.mount = win32com.client.Dispatch("ASCOM.ASIMount.Telescope")
                self.mount.Connected = True
                self.connected = True
                if not self.mount.CanSlew or not self.mount.CanSlewAsync:
                    raise Exception("❌ This mount does not support slewing.")
                print("✅ Mount connected.")
                return True
            except Exception as e:
                print(f"❌ Failed to connect to ASCOM mount: {e}")
                self.connected = False
                return False
        return True


    def disconnect(self):
        if not self.ascom_available:
            print("❌ ASCOM not available. Cannot disconnect telescope.")
            return
            
        if self.mount and self.connected:
            try:
                self.mount.Connected = False
                self.connected = False
                print("🔌 Disconnected from mount.")
            except Exception as e:
                print(f"❌ Error disconnecting from mount: {e}")
                self.connected = False

    def slew_to(self, ra_hours, dec_degrees):
        if not self.ascom_available:
            print("❌ ASCOM not available. Cannot slew telescope.")
            return False
            
        if not self.connect():
            return False
            
        try:
            print(f"➡️ Slewing to RA: {ra_hours}, DEC: {dec_degrees}")
            self.mount.SlewToCoordinatesAsync(ra_hours, dec_degrees)
            return True
        except Exception as e:
            print(f"❌ Error slewing telescope: {e}")
            return False
        print("✅ Slew complete.")

    def get_current_coordinates(self):
        self.connect()
        return self.mount.RightAscension, self.mount.Declination

