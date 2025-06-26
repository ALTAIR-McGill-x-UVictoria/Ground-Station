from PyQt5.QtCore import QObject, pyqtSignal

class ConnectionModel(QObject):
    """Model for managing connection state"""
    
    # Define signals
    connection_changed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        
        # Connection state
        self.connected = False
        self.port = ""
        self.baud_rate = 115200
        
        # Statistics
        self.bytes_received = 0
        self.packets_received = 0
        self.last_packet_time = 0
        
    def set_connected(self, connected, port=""):
        """Set connection state and emit signal"""
        if self.connected != connected:
            self.connected = connected
            if connected:
                self.port = port
            else:
                self.port = ""
            self.connection_changed.emit(connected)
    
    def record_packet(self, bytes_count):
        """Record statistics for a received packet"""
        import time
        now = time.time()
        
        self.bytes_received += bytes_count
        self.packets_received += 1
        self.last_packet_time = now
    
    def get_port(self):
        """Get the current connected port"""
        return self.port
    
    def is_connected(self):
        """Check if currently connected"""
        return self.connected