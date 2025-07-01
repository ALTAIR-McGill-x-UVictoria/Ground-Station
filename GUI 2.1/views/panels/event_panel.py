import os
from datetime import datetime # Keep this for timestamps
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTextEdit, QLineEdit, QCheckBox, QComboBox, QGroupBox, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QTextCursor, QFont, QColor # Removed QTextCharFormat, QBrush
from PyQt5.QtCore import Qt, pyqtSlot
# import datetime # Redundant import

class EventPanel(QWidget):
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
        
        # Console header with title and status
        header_layout = QHBoxLayout()
        console_title = QLabel("Event Monitor")
        console_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(console_title)
        
        header_layout.addStretch()
        
        # Connection status indicator
        self.connection_status = QLabel("Not Connected")
        self.connection_status.setStyleSheet(
            "background-color: #ff3333; color: white; padding: 4px 8px; "
            "border-radius: 4px; font-weight: bold; font-size: 9pt;"
        )
        header_layout.addWidget(self.connection_status)
        
        layout.addLayout(header_layout)
        
        # Raw data display (QTextEdit)
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00; /* Green text like in gui.py */
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.data_display, 1) # Make it expand
        
        # Control section
        controls_group = QGroupBox("Console Controls")
        controls_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                color: #00ff00;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        controls_layout = QHBoxLayout(controls_group)
        
        # Button layout (Clear, Start/Stop Logging)
        self.clear_button = QPushButton("Clear Console")
        self.clear_button.clicked.connect(self.clear_data_display)
        self.clear_button.setToolTip("Clear all console output")
        controls_layout.addWidget(self.clear_button)
        
        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self.toggle_logging)
        self.log_button.setToolTip("Start/stop logging console output to file")
        controls_layout.addWidget(self.log_button)

        # Save console button
        save_button = QPushButton("Save Console")
        save_button.clicked.connect(self.save_console_contents)
        save_button.setToolTip("Save current console contents to file")
        controls_layout.addWidget(save_button)
        
        # Auto-scroll checkbox
        self.auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self.auto_scroll_checkbox.setChecked(True)
        self.auto_scroll_checkbox.setToolTip("Automatically scroll to bottom when new data arrives")
        controls_layout.addWidget(self.auto_scroll_checkbox)
        
        # Max lines setting
        controls_layout.addWidget(QLabel("Max lines:"))
        self.max_lines_combo = QComboBox()
        self.max_lines_combo.addItems(["100", "200", "500", "1000", "2000"])
        self.max_lines_combo.setCurrentText(str(self.max_console_lines))
        self.max_lines_combo.currentTextChanged.connect(self.update_max_lines)
        self.max_lines_combo.setToolTip("Maximum number of lines to keep in console")
        controls_layout.addWidget(self.max_lines_combo)
        
        layout.addWidget(controls_group)
        
        # Connect to serial controller signals for connection status
        if hasattr(self.serial_controller, 'connection_changed'):
            self.serial_controller.connection_changed.connect(self.update_connection_status)

    @pyqtSlot(str)
    def display_raw_data(self, data_line):
        """Display raw data line with a timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        formatted_line = f"[{timestamp}] {data_line}"
        
        self.data_display.append(formatted_line)
        self.trim_console_lines()
        self.auto_scroll_to_bottom()

        if self.is_logging and self.log_file:
            try:
                self.log_file.write(f"{formatted_line}\n")
                self.log_file.flush()
            except Exception as e:
                error_msg = f"[{timestamp}] Error writing to log: {str(e)}"
                self.data_display.append(error_msg)
                self.trim_console_lines()
                self.auto_scroll_to_bottom()
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
        self.auto_scroll_to_bottom()

    def log_to_console(self, message, color=None):
        """Generic method to log messages to the console display."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        if color:
            self.data_display.setTextColor(QColor(color))
        
        self.data_display.append(f"[{timestamp}] {message}")
        
        if color: # Reset to default color if a specific color was used
            self.data_display.setTextColor(QColor("#00ff00"))
        self.trim_console_lines()
        self.auto_scroll_to_bottom()

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

    def update_connection_status(self, connected, port_name=""):
        """Update the connection status indicator."""
        if connected:
            self.connection_status.setText(f"Connected: {port_name}")
            self.connection_status.setStyleSheet(
                "background-color: #00cc00; color: white; padding: 4px 8px; "
                "border-radius: 4px; font-weight: bold; font-size: 9pt;"
            )
        else:
            self.connection_status.setText("Not Connected")
            self.connection_status.setStyleSheet(
                "background-color: #ff3333; color: white; padding: 4px 8px; "
                "border-radius: 4px; font-weight: bold; font-size: 9pt;"
            )

    def update_max_lines(self, new_max_str):
        """Update the maximum number of lines to keep in console."""
        try:
            new_max = int(new_max_str)
            self.max_console_lines = new_max
            self.settings_model.set('console.max_lines', new_max)
            self.trim_console_lines()  # Apply new limit immediately
        except ValueError:
            pass  # Ignore invalid values

    def auto_scroll_to_bottom(self):
        """Automatically scroll to bottom if auto-scroll is enabled."""
        if self.auto_scroll_checkbox.isChecked():
            cursor = self.data_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.data_display.setTextCursor(cursor)