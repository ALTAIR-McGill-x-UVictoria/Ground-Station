import serial
import threading
import queue
import time
from PyQt5.QtCore import QObject, pyqtSignal

class SerialController(QObject):
    """Controller for serial port communications"""
    
    packet_received = pyqtSignal(str) # For parsed telemetry packets
    raw_data_received = pyqtSignal(str) # For raw lines to console
    connection_changed = pyqtSignal(bool, str) # connected (bool), port_name (str)
    connection_error = pyqtSignal(str)
    
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
    
    def read_serial_data(self): # Renamed from read_serial
        """Thread function to read from serial port, inspired by gui.py."""
        while not self.stop_thread_flag.is_set():
            if not self.serial_port or not self.serial_port.is_open:
                # Port closed or not available, break loop
                if not self.stop_thread_flag.is_set(): # Avoid error if intentionally stopping
                     self.connection_error.emit("Serial port disconnected or unavailable.")
                break
            try:
                if self.serial_port.in_waiting > 0:
                    line_bytes = self.serial_port.readline()
                    try:
                        # Decode and strip whitespace
                        decoded_line = line_bytes.decode('utf-8', errors='ignore').strip()
                        
                        if not decoded_line: # Skip empty lines
                            continue

                        # Emit raw data for console
                        self.raw_data_received.emit(decoded_line)
                        
                        # Skip processing certain lines that are not telemetry
                        if decoded_line.startswith('Sending packet:'):
                            continue  # Skip command acknowledgments
                        
                        # Basic check for printable characters and comma (from gui.py)
                        # This is a heuristic; more robust parsing should be in TelemetryController
                        is_potentially_valid_packet = True
                        # if any(ord(c) < 32 or ord(c) > 126 for c in decoded_line if c not in ['\r', '\n']):
                        #    is_potentially_valid_packet = False # Contains non-printable
                        
                        # Check for known packet formats or legacy comma-separated format
                        if not (decoded_line.startswith(('GPS:', 'GS:', 'FC:')) or ',' in decoded_line):
                            is_potentially_valid_packet = False # Not known format

                        if is_potentially_valid_packet:
                            # Update statistics in model
                            self.connection_model.record_packet(len(line_bytes))
                            # Emit packet for telemetry processing
                            self.packet_received.emit(decoded_line)
                            
                    except UnicodeDecodeError:
                        # self.raw_data_received.emit(f"[Decode Error] {line_bytes}")
                        continue # Skip lines that can't be decoded
            except serial.SerialException as e: # Catch specific serial exceptions
                if not self.stop_thread_flag.is_set():
                    self.connection_error.emit(f"Serial read error: {str(e)}")
                break # Exit thread on serial error
            except Exception as e: # Catch other unexpected errors
                if not self.stop_thread_flag.is_set():
                    self.connection_error.emit(f"Unexpected serial read error: {str(e)}")
                break # Exit thread
            
            time.sleep(0.005) # Small sleep to yield CPU, reduce if high data rate

        # Cleanup after loop exits
        if not self.stop_thread_flag.is_set() and self.connection_model.is_connected():
            # If loop exited unexpectedly and still thought it was connected
            self.disconnect()


    def send_command(self, command):
        if not self.serial_port or not self.serial_port.is_open:
            self.connection_error.emit("Not connected: Cannot send command.")
            return False
            
        try:
            # Ensure command ends with newline, as in gui.py
            if not command.endswith('\n'):
                command += '\n'
            self.serial_port.write(command.encode('utf-8'))
            self.raw_data_received.emit(f"TX: {command.strip()}") # Log sent command to console
            return True
        except serial.SerialTimeoutException:
            self.connection_error.emit(f"Send timeout: {command.strip()}")
            return False
        except Exception as e:
            self.connection_error.emit(f"Send error: {str(e)}")
            return False

    def is_connected(self):
        return self.serial_port is not None and self.serial_port.is_open