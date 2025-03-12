import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTextEdit, QLineEdit, QCheckBox, QComboBox, QGroupBox, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QTextCursor, QFont, QColor, QTextCharFormat, QBrush
from PyQt5.QtCore import Qt, pyqtSlot
import datetime

class ConsolePanel(QWidget):
    """Panel for displaying serial console output and sending commands"""
    
    def __init__(self, serial_controller, settings_model, parent=None):
        super().__init__(parent)
        self.serial_controller = serial_controller
        self.settings_model = settings_model
        
        # Command history
        self.command_history = []
        self.history_position = 0
        
        # Initialize logging variables
        self.is_logging = False
        self.log_file = None
        
        # Set up UI
        self.setup_ui()
        
        # Connect signals
        self.serial_controller.packet_received.connect(self.on_data_received)
        self.serial_controller.connection_error.connect(self.on_connection_error)
    
    def setup_ui(self):
        """Set up the console panel UI"""
        layout = QVBoxLayout(self)
        
        # Console output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.console, 1)
        
        # Console controls
        controls_layout = QHBoxLayout()
        
        # Auto-scroll checkbox
        self.auto_scroll = QCheckBox("Auto-scroll")
        self.auto_scroll.setChecked(True)
        controls_layout.addWidget(self.auto_scroll)
        
        # Display mode
        self.display_mode = QComboBox()
        self.display_mode.addItems(["All", "Raw Packets", "Parsed Data", "Commands"])
        controls_layout.addWidget(QLabel("Display:"))
        controls_layout.addWidget(self.display_mode)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_console)
        controls_layout.addWidget(self.clear_button)
        
        layout.addLayout(controls_layout)
        
        # Command input
        input_layout = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        self.command_input.returnPressed.connect(self.send_command)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_command)
        
        input_layout.addWidget(self.command_input, 1)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Log button
        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self.toggle_logging)
        button_layout.addWidget(self.log_button)
        
        # Save button
        save_button = QPushButton("Save Console")
        save_button.clicked.connect(self.save_console)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
    
    @pyqtSlot(str)
    def on_data_received(self, data):
        """Handle data received from serial port"""
        # Only show if display mode is "All" or "Raw Packets"
        if self.display_mode.currentText() in ["All", "Raw Packets"]:
            timestamp = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            self.log_data(f"[{timestamp}] RX: {data}")
        
        # Log to file if enabled
        if self.is_logging and self.log_file:
            try:
                self.log_file.write(f"{formatted_line}\n")
                self.log_file.flush()
            except Exception as e:
                self.console.append(f"[{timestamp}] Error writing to log: {str(e)}")
                self.toggle_logging()  # Stop logging on error
    
    @pyqtSlot(str)
    def on_connection_error(self, error_message):
        """Handle connection errors"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        self.console.append(f"[{timestamp}] ERROR: {error_message}")
        
        # Scroll to bottom
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.console.setTextCursor(cursor)
    
    def log_message(self, message):
        """Log a regular message to the console"""
        # Only show if display mode is "All" or includes relevant type
        display_mode = self.display_mode.currentText()
        if (display_mode == "All" or 
            (display_mode == "Commands" and message.find("Sent:") != -1) or
            (display_mode == "Parsed Data" and message.find("Parsed:") != -1)):
            
            self.console.setTextColor(QColor("white"))
            self.console.append(message)
            
            if self.auto_scroll.isChecked():
                self.console.moveCursor(QTextCursor.End)
    
    def log_data(self, message):
        """Log data to the console"""
        self.console.setTextColor(QColor("#00ff00"))  # Green for received data
        self.console.append(message)
        
        if self.auto_scroll.isChecked():
            self.console.moveCursor(QTextCursor.End)
    
    def log_error(self, message):
        """Log an error to the console"""
        self.console.setTextColor(QColor("#ff5500"))  # Orange-red for errors
        self.console.append(f"ERROR: {message}")
        
        # Always auto-scroll for errors
        self.console.moveCursor(QTextCursor.End)
    
    def clear_console(self):
        """Clear the console output"""
        self.console.clear()
    
    def send_command(self):
        """Send the current command"""
        command = self.command_input.text().strip()
        if command:
            # Add to history
            self.command_history.append(command)
            self.history_position = len(self.command_history)
            
            # Send command
            timestamp = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            success = self.serial_controller.send_command(command)
            
            # Log to console
            if success:
                self.console.setTextColor(QColor("#00aaff"))  # Blue for sent commands
                self.console.append(f"[{timestamp}] TX: {command}")
            else:
                self.log_error(f"Failed to send: {command}")
            
            # Clear input
            self.command_input.clear()
            
            # Auto-scroll
            if self.auto_scroll.isChecked():
                self.console.moveCursor(QTextCursor.End)
    
    def toggle_logging(self):
        """Toggle serial data logging to file"""
        if not self.is_logging:
            try:
                # Create logs directory if it doesn't exist
                path = "logs"
                if not os.path.exists(path):
                    os.makedirs(path)
                
                # Create filename with timestamp
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                log_file_path = f"{path}/flight_log_{timestamp}.txt"
                
                self.log_file = open(log_file_path, 'w')
                self.log_file.write(f"HAB Ground Station Log\n")
                self.log_file.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.log_file.write(f"----------------------------------------\n\n")
                self.log_file.flush()
                
                self.is_logging = True
                self.log_button.setText("Stop Logging")
                
                # Notify in console
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                self.console.append(f"[{timestamp}] Started logging to {log_file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Logging Error", f"Could not create log file: {str(e)}")
        else:
            try:
                if self.log_file:
                    self.log_file.write(f"\n----------------------------------------\n")
                    self.log_file.write(f"Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    self.log_file.close()
                    self.log_file = None
                
                self.is_logging = False
                self.log_button.setText("Start Logging")
                
                # Notify in console
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                self.console.append(f"[{timestamp}] Stopped logging")
            except Exception as e:
                QMessageBox.critical(self, "Logging Error", f"Error closing log file: {str(e)}")
    
    def save_console(self):
        """Save console contents to a file"""
        try:
            # Create logs directory if it doesn't exist
            path = "logs"
            if not os.path.exists(path):
                os.makedirs(path)
            
            # Get filename with timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            default_filename = f"{path}/console_export_{timestamp}.txt"
            
            # Ask user for filename
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Console Output",
                default_filename,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if filename:
                with open(filename, 'w') as file:
                    file.write(self.console.toPlainText())
                
                # Notify in console
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                self.console.append(f"[{timestamp}] Console saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save console: {str(e)}")