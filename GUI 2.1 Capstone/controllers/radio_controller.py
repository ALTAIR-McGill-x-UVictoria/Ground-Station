import serial
import threading
import time
import logging

class RadioController:
    def __init__(self, telemetry_model):
        self.telemetry_model = telemetry_model
        self.serial = None
        self.running = False
        self.connected = False
        self.receive_thread = None
        self.logger = logging.getLogger(__name__)
        self.connection_callbacks = []
        
        # Define packet markers - CHANGE THESE TO MATCH YOUR ACTUAL PROTOCOL
        self.CONTROL_TO_POWER_HEADER = b'\xAA\xBB'  # Example header bytes
        self.POWER_TO_CONTROL_HEADER = b'\xCC\xDD'  # Example header bytes
        self.PACKET_FOOTER = b'\xEE\xFF'  # Example footer bytes
    
    def register_connection_callback(self, callback):
        """Register a callback to be notified of connection status changes"""
        if callback not in self.connection_callbacks:
            self.connection_callbacks.append(callback)
    
    def connect(self, port, baud=115200):
        """Connect to radio on specified port"""
        try:
            self.serial = serial.Serial(port, baud, timeout=0.1)
            self.connected = True
            self.running = True
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # Notify connection callbacks
            for callback in self.connection_callbacks:
                callback(True, port)
                
            self.logger.info(f"Connected to radio on {port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to radio: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from radio"""
        self.running = False
        
        if self.receive_thread:
            self.receive_thread.join(1.0)
        
        if self.serial:
            self.serial.close()
            self.serial = None
        
        self.connected = False
        
        # Notify connection callbacks
        for callback in self.connection_callbacks:
            callback(False)
            
        self.logger.info("Disconnected from radio")
    
    def _receive_loop(self):
        """Main receive loop to process incoming packets"""
        buffer = bytearray()
        
        while self.running:
            try:
                if self.serial and self.serial.is_open:
                    # Read data from serial port
                    data = self.serial.read(256)
                    if data:
                        # Add to buffer and process
                        buffer.extend(data)
                        self._process_buffer(buffer)
                        
                # Small delay to prevent CPU hogging
                time.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Error in receive loop: {e}")
                time.sleep(1.0)
    
    def _process_buffer(self, buffer):
        """Process the buffer for complete packets"""
        # Look for Control to Power packets
        self._find_and_process_packet(buffer, self.CONTROL_TO_POWER_HEADER, 
                                     self.telemetry_model.parse_control_to_power_packet)
        
        # Look for Power to Control packets
        self._find_and_process_packet(buffer, self.POWER_TO_CONTROL_HEADER,
                                     self.telemetry_model.parse_power_to_control_packet)
        
        # Prevent buffer from growing too large
        if len(buffer) > 1024:
            del buffer[:-512]  # Keep the last 512 bytes
    
    def _find_and_process_packet(self, buffer, header, parser_func):
        """Find and process packets with the given header"""
        header_pos = 0
        
        while True:
            # Find header starting from current position
            header_pos = buffer.find(header, header_pos)
            if header_pos == -1:
                break  # No more headers found
            
            # Look for footer after header
            footer_pos = buffer.find(self.PACKET_FOOTER, header_pos + len(header))
            if footer_pos == -1:
                break  # No complete packet found
            
            # Extract packet data between header and footer
            packet_data = buffer[header_pos + len(header):footer_pos]
            
            # Parse the packet
            if parser_func(packet_data):
                # Successfully parsed, remove packet from buffer
                del buffer[:footer_pos + len(self.PACKET_FOOTER)]
                header_pos = 0  # Start from beginning of new buffer
            else:
                # Parse failed, move to next header position
                header_pos += len(header)