import win32com.client

class TelescopeController:
    def __init__(self):
        self.mount = None
        self.connected = False

    def connect(self):
        if not self.connected:
            try:
                self.mount = win32com.client.Dispatch("ASCOM.ASIMount.Telescope")
                self.mount.Connected = True
                self.connected = True
                if not self.mount.CanSlew or not self.mount.CanSlewAsync:
                    raise Exception("❌ This mount does not support slewing.")
                print("✅ Mount connected.")
            except Exception as e:
                print(f"❌ Failed to connect to ASCOM mount: {e}")


    def disconnect(self):
        if self.mount and self.connected:
            self.mount.Connected = False
            self.connected = False
            print("🔌 Disconnected from mount.")

    def slew_to(self, ra_hours, dec_degrees):
        self.connect()
        print(f"➡️ Slewing to RA: {ra_hours}, DEC: {dec_degrees}")
        self.mount.SlewToCoordinatesAsync(ra_hours, dec_degrees)
        print("✅ Slew complete.")

    def get_current_coordinates(self):
        self.connect()
        return self.mount.RightAscension, self.mount.Declination