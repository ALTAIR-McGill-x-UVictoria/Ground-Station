import serial
import threading
import queue
import time
from PyQt5.QtCore import QObject, pyqtSignal

class SerialController(QObject):
    """Controller for serial port communications"""
    
    # Define signals
    packet_received = pyqtSignal(str)
    connection_changed = pyqtSignal(bool)
    connection_error = pyqtSignal(str)
    
    def __init__(self, connection_model):
        super().__init__()
        self.connection_model = connection_model
        self.serial_port = None
        self.serial_queue = queue.Queue()
        self.read_thread = None
        self.stop_thread = False
    
    def get_available_ports(self):
        """Get list of available serial ports"""
        import serial.tools.list_ports
        return [port.device for port in serial.tools.list_ports.comports()]
    
    def connect(self, port, baud_rate=115200):
        """Connect to specified serial port"""
        try:
            self.serial_port = serial.Serial(port, baud_rate, timeout=1)
            self.connection_model.set_connected(True, port)
            
            # Reset stop flag and start reading thread
            self.stop_thread = False
            self.read_thread = threading.Thread(
                target=self.read_serial, daemon=True
            )
            self.read_thread.start()
            
            return True
        except Exception as e:
            self.connection_error.emit(f"Connection error: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from serial port"""
        if self.serial_port and self.serial_port.is_open:
            # Signal thread to stop
            self.stop_thread = True
            
            # Wait for thread to finish (with timeout)
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=1.0)
            
            try:
                self.serial_port.close()
            except:
                pass
                
            self.serial_port = None
            self.connection_model.set_connected(False)
            return True
        return False
    
    def read_serial(self):
        """Thread function to read from serial port"""
        while self.serial_port and self.serial_port.is_open and not self.stop_thread:
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline()
                    try:
                        decoded_line = line.decode('utf-8').strip()
                        # Skip non-printable characters and ensure comma-separated values
                        if any(ord(c) < 32 or ord(c) > 126 for c in decoded_line):
                            continue
                        if ',' in decoded_line:
                            # Update statistics
                            self.connection_model.record_packet(len(line))
                            # Emit signal with the packet data
                            self.packet_received.emit(decoded_line)
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                if not self.stop_thread:  # Only report error if not intentionally stopping
                    self.connection_error.emit(f"Serial read error: {str(e)}")
                break
            # Small sleep to prevent CPU hogging
            time.sleep(0.01)
    
    def send_command(self, command):
        """Send a command to the connected device"""
        if not self.serial_port or not self.serial_port.is_open:
            self.connection_error.emit("Not connected")
            return False
            
        try:
            # Add newline if not present
            if not command.endswith('\n'):
                command += '\n'
            self.serial_port.write(command.encode())
            return True
        except Exception as e:
            self.connection_error.emit(f"Send error: {str(e)}")
            return False