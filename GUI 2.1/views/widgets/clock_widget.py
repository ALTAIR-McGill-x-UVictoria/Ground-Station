from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QFont, QColor, QBrush, QPen
from PyQt5.QtCore import Qt, QRectF, QDateTime
import datetime

class DigitalClockWidget(QWidget):
    """Widget to display digital GPS time"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hours = 0
        self.minutes = 0
        self.seconds = 0
        self.valid_time = False
        self.setMinimumSize(200, 80)
    
    def setTime(self, time_value):
        """
        Set the time to display on the clock
        time_value: Can be:
        - Unix timestamp in microseconds (from GPS)
        - Time string in format "HH:MM:SS" 
        - Numeric value in HHMMSS.SS format (legacy)
        """
        try:
            self.valid_time = False
            
            # Check if we're receiving a Unix timestamp in microseconds
            if isinstance(time_value, (int, float)) and time_value > 1000000000000:  # Microseconds since epoch
                # Convert microseconds to seconds
                unix_seconds = time_value / 1000000.0
                
                # Convert to UTC datetime
                utc_time = datetime.datetime.fromtimestamp(unix_seconds, tz=datetime.timezone.utc)
                self.hours = utc_time.hour
                self.minutes = utc_time.minute
                self.seconds = utc_time.second
                self.valid_time = True
                print(f"GPS Time (UTC): {self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}")
                
            # Check if we're receiving a formatted time string
            elif isinstance(time_value, str) and ":" in time_value:
                # Parse HH:MM:SS format
                time_parts = time_value.split(":")
                self.hours = int(time_parts[0])
                self.minutes = int(time_parts[1])
                self.seconds = int(time_parts[2])
                self.valid_time = True
                
            # Handle legacy numeric time value (HHMMSS.SS format)
            elif isinstance(time_value, (int, float)) and time_value > 0:
                # Parse HHMMSS.SS format
                time_value = float(time_value)
                self.hours = int(time_value / 10000)
                self.minutes = int((time_value - self.hours * 10000) / 100)
                self.seconds = int(time_value - self.hours * 10000 - self.minutes * 100)
                self.valid_time = True
                
            else:
                print(f"Invalid time format: {type(time_value)} - {time_value}")
                self.valid_time = False
                
        except Exception as e:
            print(f"Error parsing time in clock widget: {str(e)}")
            self.valid_time = False
        
        self.update()
    
    def paintEvent(self, event):
        """Draw the digital clock"""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw background
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor('#1a1a1a')))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)
            
            # Set color based on time validity
            time_color = QColor('#00ff00') if self.valid_time else QColor('#888888')
            
            # Draw label
            painter.setPen(QPen(time_color))
            label_font = QFont('Arial', 10)
            label_font.setBold(True)
            painter.setFont(label_font)
            
            label_text = "GPS Time (UTC)" if self.valid_time else "GPS Time (No Signal)"
            painter.drawText(QRectF(0, 5, self.width(), 20),
                            Qt.AlignHCenter, label_text)
            
            # Draw time
            if self.valid_time:
                time_str = f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}"
            else:
                time_str = "--:--:--"
                
            time_font = QFont('Courier New', 24)
            time_font.setBold(True)
            painter.setFont(time_font)
            painter.drawText(QRectF(0, 20, self.width(), self.height()-20),
                            Qt.AlignCenter, time_str)
        finally:
            painter.end()