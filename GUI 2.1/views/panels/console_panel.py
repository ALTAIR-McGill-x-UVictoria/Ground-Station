import os
from datetime import datetime # Keep this for timestamps
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTextEdit, QLineEdit, QCheckBox, QComboBox, QGroupBox, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QTextCursor, QFont, QColor # Removed QTextCharFormat, QBrush
from PyQt5.QtCore import Qt, pyqtSlot
# import datetime # Redundant import

class ConsolePanel(QWidget):
    """Panel for displaying serial console output, similar to gui.py's raw data section"""
    
    def __init__(self, serial_controller, settings_model, parent=None):
        super().__init__(parent)
        self.serial_controller = serial_controller
        self.settings_model = settings_model # Keep for potential settings like log path
        
        # Logging variables from gui.py
        self.is_logging = False
        self.log_file = None
        
        # Max lines for console display
        self.max_console_lines = self.settings_model.get('console.max_lines', 200)

        self.setup_ui()
        
        # Connect signals
        # packet_received is now handled by TelemetryController, which updates TelemetryModel.
        # If raw data needs to be displayed directly from serial_controller:
        self.serial_controller.raw_data_received.connect(self.display_raw_data) # Assuming serial_controller emits this
        self.serial_controller.connection_error.connect(self.display_connection_error)
        # If console needs to log commands sent via command_controller:
        # self.command_controller.command_log.connect(self.log_to_console) # Assuming command_controller exists and has this signal

    def setup_ui(self):
        """Set up the console panel UI based on gui.py's raw data section."""
        layout = QVBoxLayout(self)
        
        # Raw data display (QTextEdit)
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00; /* Green text like in gui.py */
                font-family: 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.data_display, 1) # Make it expand
        
        # Button layout (Clear, Start/Stop Logging)
        button_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_data_display)
        button_layout.addWidget(self.clear_button)
        
        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self.toggle_logging)
        button_layout.addWidget(self.log_button)

        # Optional: Save console button (good feature to keep)
        save_button = QPushButton("Save Console")
        save_button.clicked.connect(self.save_console_contents)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)

    @pyqtSlot(str)
    def display_raw_data(self, data_line):
        """Display raw data line with a timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        formatted_line = f"[{timestamp}] {data_line}"
        
        self.data_display.append(formatted_line)
        self.trim_console_lines()

        if self.is_logging and self.log_file:
            try:
                self.log_file.write(f"{formatted_line}\n")
                self.log_file.flush()
            except Exception as e:
                error_msg = f"[{timestamp}] Error writing to log: {str(e)}"
                self.data_display.append(error_msg)
                self.trim_console_lines()
                self.stop_logging_on_error() # Stop logging on error

    def stop_logging_on_error(self):
        if self.is_logging:
            self.toggle_logging() # This will attempt to close the file and update UI

    @pyqtSlot(str)
    def display_connection_error(self, error_message):
        """Display connection errors."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        self.data_display.setTextColor(QColor("red")) # Show errors in red
        self.data_display.append(f"[{timestamp}] ERROR: {error_message}")
        self.data_display.setTextColor(QColor("#00ff00")) # Reset to default color
        self.trim_console_lines()

    def log_to_console(self, message, color=None):
        """Generic method to log messages to the console display."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        if color:
            self.data_display.setTextColor(QColor(color))
        
        self.data_display.append(f"[{timestamp}] {message}")
        
        if color: # Reset to default color if a specific color was used
            self.data_display.setTextColor(QColor("#00ff00"))
        self.trim_console_lines()

    def clear_data_display(self):
        self.data_display.clear()

    def trim_console_lines(self):
        """Keep only the last N lines in the data display."""
        doc = self.data_display.document()
        while doc.blockCount() > self.max_console_lines:
            cursor = QTextCursor(doc.firstBlock())
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            # QTextEdit's BlockUnderCursor selection sometimes leaves the newline,
            # an explicit deleteChar can help ensure the block is fully removed.
            if doc.blockCount() > self.max_console_lines : # Check again before deleting char
                 cursor.deleteChar()


    def toggle_logging(self):
        """Toggle serial data logging to file, from gui.py."""
        if not self.is_logging:
            try:
                log_dir = self.settings_model.get('logging.directory', "logs")
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                
                ts_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                log_file_path = os.path.join(log_dir, f"flight_log_{ts_filename}.txt")
                
                self.log_file = open(log_file_path, 'w')
                self.log_file.write(f"HAB Ground Station Log\n")
                self.log_file.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.log_file.write(f"----------------------------------------\n\n")
                self.log_file.flush()
                
                self.is_logging = True
                self.log_button.setText("Stop Logging")
                self.log_to_console(f"Started logging to {log_file_path}", "yellow")
            except Exception as e:
                QMessageBox.critical(self, "Logging Error", f"Could not create log file: {str(e)}")
                if self.log_file: # Ensure file is closed if opened partially
                    self.log_file.close()
                    self.log_file = None
                self.is_logging = False # Reset state
                self.log_button.setText("Start Logging")

        else:
            try:
                if self.log_file:
                    self.log_file.write(f"\n----------------------------------------\n")
                    self.log_file.write(f"Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    self.log_file.close()
                    self.log_file = None
                
                self.is_logging = False
                self.log_button.setText("Start Logging")
                self.log_to_console("Stopped logging", "yellow")
            except Exception as e:
                QMessageBox.critical(self, "Logging Error", f"Error closing log file: {str(e)}")
                # Even if closing fails, update state
                self.log_file = None 
                self.is_logging = False
                self.log_button.setText("Start Logging")

    def save_console_contents(self):
        """Save current console contents to a user-specified file."""
        try:
            log_dir = self.settings_model.get('logging.directory', "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            ts_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            default_filename = os.path.join(log_dir, f"console_export_{ts_filename}.txt")
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Console Output", default_filename, "Text Files (*.txt);;All Files (*)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    f.write(self.data_display.toPlainText())
                self.log_to_console(f"Console saved to {filename}", "yellow")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save console: {str(e)}")

    def closeEvent(self, event): # Ensure log file is closed if panel is closed
        if self.is_logging and self.log_file:
            self.toggle_logging() # This will handle closing the file
        super().closeEvent(event)