import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QCheckBox, QGroupBox, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QTextCursor, QColor
from PyQt5.QtCore import Qt

class EventPanel(QWidget):
    """Panel for displaying and logging system events (e.g., GPS, telemetry, etc)."""

    def __init__(self, serial_controller, settings_model, parent=None):
        super().__init__(parent)
        self.serial_controller = serial_controller
        self.settings_model = settings_model

        self.is_logging = False
        self.log_file = None
        self.max_event_lines = self.settings_model.get('event_panel.max_lines', 200)

        self.setup_ui()
        # Automatically start logging on panel creation
        self.toggle_logging()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Event Log")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Event display
        self.event_display = QTextEdit()
        self.event_display.setReadOnly(True)
        self.event_display.setStyleSheet("""
            QTextEdit {
                background-color: #232323;
                color: #ffcc00;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.event_display, 1)

        # Controls
        controls_group = QGroupBox("Event Controls")
        controls_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                color: #ffcc00;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        controls_layout = QHBoxLayout(controls_group)

        self.clear_button = QPushButton("Clear Events")
        self.clear_button.clicked.connect(self.clear_event_display)
        controls_layout.addWidget(self.clear_button)

        self.log_button = QPushButton("Start Logging")
        self.log_button.clicked.connect(self.toggle_logging)
        controls_layout.addWidget(self.log_button)

        save_button = QPushButton("Save Events")
        save_button.clicked.connect(self.save_event_contents)
        controls_layout.addWidget(save_button)

        self.auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self.auto_scroll_checkbox.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_checkbox)

        controls_layout.addWidget(QLabel("Max lines:"))
        from PyQt5.QtWidgets import QComboBox
        self.max_lines_combo = QComboBox()
        self.max_lines_combo.addItems(["100", "200", "500", "1000", "2000"])
        self.max_lines_combo.setCurrentText(str(self.max_event_lines))
        self.max_lines_combo.currentTextChanged.connect(self.update_max_lines)
        controls_layout.addWidget(self.max_lines_combo)

        layout.addWidget(controls_group)

    def log_event(self, message, color=None):
        """Display and log an event with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        if color:
            self.event_display.setTextColor(QColor(color))
        self.event_display.append(formatted)
        if color:
            self.event_display.setTextColor(QColor("#ffcc00"))
        self.trim_event_lines()
        self.auto_scroll_to_bottom()
        if self.is_logging and self.log_file:
            try:
                self.log_file.write(formatted + "\n")
                self.log_file.flush()
            except Exception as e:
                self.event_display.setTextColor(QColor("red"))
                self.event_display.append(f"[{timestamp}] Error writing to log: {str(e)}")
                self.event_display.setTextColor(QColor("#ffcc00"))
                self.trim_event_lines()
                self.auto_scroll_to_bottom()
                self.stop_logging_on_error()

    def stop_logging_on_error(self):
        if self.is_logging:
            self.toggle_logging()

    def clear_event_display(self):
        self.event_display.clear()

    def trim_event_lines(self):
        doc = self.event_display.document()
        while doc.blockCount() > self.max_event_lines:
            cursor = QTextCursor(doc.firstBlock())
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            if doc.blockCount() > self.max_event_lines:
                cursor.deleteChar()

    def toggle_logging(self):
        if not self.is_logging:
            try:
                log_dir = self.settings_model.get('event_panel.log_dir', "event_logs")
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                ts_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                log_file_path = os.path.join(log_dir, f"event_log_{ts_filename}.txt")
                self.log_file = open(log_file_path, 'w')
                self.log_file.write(f"Event Log\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.log_file.write(f"----------------------------------------\n\n")
                self.log_file.flush()
                self.is_logging = True
                self.log_button.setText("Stop Logging")
                self.log_event(f"Started logging to {log_file_path}", color="yellow")
            except Exception as e:
                QMessageBox.critical(self, "Logging Error", f"Could not create log file: {str(e)}")
                if self.log_file:
                    self.log_file.close()
                    self.log_file = None
                self.is_logging = False
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
                self.log_event("Stopped logging", color="yellow")
            except Exception as e:
                QMessageBox.critical(self, "Logging Error", f"Error closing log file: {str(e)}")
                self.log_file = None
                self.is_logging = False
                self.log_button.setText("Start Logging")

    def save_event_contents(self):
        try:
            log_dir = self.settings_model.get('event_panel.log_dir', "event_logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            ts_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            default_filename = os.path.join(log_dir, f"event_export_{ts_filename}.txt")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Event Log", default_filename, "Text Files (*.txt);;All Files (*)"
            )
            if filename:
                with open(filename, 'w') as f:
                    f.write(self.event_display.toPlainText())
                self.log_event(f"Events saved to {filename}", color="yellow")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save events: {str(e)}")

    def closeEvent(self, event):
        if self.is_logging and self.log_file:
            self.toggle_logging()
        super().closeEvent(event)

    def update_max_lines(self, new_max_str):
        try:
            new_max = int(new_max_str)
            self.max_event_lines = new_max
            self.settings_model.set('event_panel.max_lines', new_max)
            self.trim_event_lines()
        except ValueError:
            pass

    def auto_scroll_to_bottom(self):
        if self.auto_scroll_checkbox.isChecked():
            cursor = self.event_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.event_display.setTextCursor(cursor)

# Usage:
# event_panel = EventPanel(settings_model)
# event_panel.log_event("GPS Acquired")
# event_panel.log_event("Telemetry Connected")
