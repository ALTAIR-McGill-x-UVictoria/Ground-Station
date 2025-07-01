import serial
import threading
import queue
import time
from PyQt5.QtCore import QObject, pyqtSignal

class EventController(QObject):
    """Controller for serial port communications"""
    
    # packet_received = pyqtSignal(str) # For parsed telemetry packets
    # raw_data_received = pyqtSignal(str) # For raw lines to console
    # connection_changed = pyqtSignal(bool, str) # connected (bool), port_name (str)
    # connection_error = pyqtSignal(str)
    
    def __init__(self, connection_model):
        super().__init__()
        self.connection_model = connection_model
        self.serial_port = None
        # self.serial_queue = queue.Queue() # Not directly used if emitting signals
        self.read_thread = None
        self.stop_thread_flag = threading.Event() # Use threading.Event for safer stop
    
    def get_available_ports(self):
        import serial.tools.list_ports
        ports = [port.device for port in serial.tools.list_ports.comports()]
        # On Linux, filter out common non-serial tty devices if necessary
        # ports = [p for p in ports if 'ttyS' in p or 'ttyUSB' in p or 'ttyACM' in p or 'COM' in p.upper()]
        return sorted(ports)
    
    def connect(self, port, baud_rate=115200):
        if self.serial_port and self.serial_port.is_open:
            if self.serial_port.port == port: # Already connected to this port
                return True
            self.disconnect() # Disconnect if connected to a different port

        try:
            self.serial_port = serial.Serial(port, baud_rate, timeout=1)
            self.connection_model.set_connected(True, port) # Update model
            self.connection_changed.emit(True, port) # Emit signal
            
            self.stop_thread_flag.clear() # Reset stop flag
            self.read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
            self.read_thread.start()
            
            return True
        except serial.SerialException as e:
            self.connection_error.emit(f"Connection error on {port}: {str(e)}")
            self.serial_port = None # Ensure serial_port is None on failure
            self.connection_model.set_connected(False) # Update model
            self.connection_changed.emit(False, "") # Emit signal
            return False
    
    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            self.stop_thread_flag.set() # Signal thread to stop
            
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=2.0) # Wait for thread with timeout
            
            try:
                self.serial_port.close()
            except Exception as e:
                self.connection_error.emit(f"Error closing port: {str(e)}")
                
            port_name = self.serial_port.portstr
            self.serial_port = None
            self.connection_model.set_connected(False) # Update model
            self.connection_changed.emit(False, port_name) # Emit signal
            return True
        return False


    def is_connected(self):
        return self.serial_port is not None and self.serial_port.is_open
    
    def log_event(self, event_id, timestamp, message):
        """Log an event with ID, timestamp, and message"""
        log_entry = f"{timestamp} - Event {event_id}: {message}"
        print(log_entry)

    