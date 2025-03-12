from PyQt5.QtCore import QObject, pyqtSignal
from datetime import datetime

class CommandController(QObject):
    """Controller for handling command execution"""
    
    # Define signals
    command_sent = pyqtSignal(str, bool)  # command, success
    command_log = pyqtSignal(str)  # log message
    
    def __init__(self, serial_controller, settings_model):
        super().__init__()
        self.serial_controller = serial_controller
        self.settings_model = settings_model
    
    def send_command(self, command):
        """Send a generic command to the flight computer"""
        success = self.serial_controller.send_command(command)
        self.command_sent.emit(command, success)
        
        # Log the command
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        if success:
            self.command_log.emit(f"[{timestamp}] Sent: {command}")
        else:
            self.command_log.emit(f"[{timestamp}] Failed to send: {command}")
        
        return success
    
    def send_led_command(self, intensity):
        """Send LED intensity command"""
        return self.send_command(f"LED_SET {intensity}")
    
    def send_blink_command(self, delay_ms):
        """Send LED blink command"""
        return self.send_command(f"LED_BLINK {delay_ms}")
    
    def send_source_command(self, intensity):
        """Send source LED intensity command"""
        return self.send_command(f"SOURCE_LED_SET {intensity}")
    
    def send_source_blink_command(self, delay_ms):
        """Send source LED blink command"""
        return self.send_command(f"SOURCE_LED_BLINK {delay_ms}")
    
    def activate_sd(self):
        """Activate SD card logging"""
        return self.send_command("SD_ACTIVATE")
    
    def send_ping(self):
        """Send ping command"""
        return self.send_command("ping")