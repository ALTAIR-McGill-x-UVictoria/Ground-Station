from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QFont, QColor, QBrush, QPen
from PyQt5.QtCore import Qt, QRectF

class DigitalClockWidget(QWidget):
    """Widget to display digital GPS time"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hours = 0
        self.minutes = 0
        self.seconds = 0
        self.setMinimumSize(200, 80)
    
    def setTime(self, time_value):
        """
        Set the time to display on the clock
        time_value: Time string in format "HH:MM:SS" or numeric value in HHMMSS.SS format
        """
        try:
            # Check if we're receiving a formatted time string
            if isinstance(time_value, str) and ":" in time_value:
                # Parse HH:MM:SS format
                time_parts = time_value.split(":")
                self.hours = int(time_parts[0])
                self.minutes = int(time_parts[1])
                self.seconds = int(time_parts[2])
            else:
                # Handle numeric time value
                if isinstance(time_value, (int, float)):
                    # Parse HHMMSS.SS format
                    time_value = float(time_value)
                    self.hours = int(time_value / 10000)
                    self.minutes = int((time_value - self.hours * 10000) / 100)
                    self.seconds = int(time_value - self.hours * 10000 - self.minutes * 100)
                else:
                    print(f"Unknown time format: {type(time_value)} - {time_value}")
        except Exception as e:
            print(f"Error parsing time in clock widget: {str(e)}")
        
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
            
            # Draw time text
            time_str = f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}"
            painter.setPen(QPen(QColor('#00ff00')))
            
            # Draw label
            label_font = QFont('Arial', 10)
            label_font.setBold(True)
            painter.setFont(label_font)
            painter.drawText(QRectF(0, 5, self.width(), 20),
                            Qt.AlignHCenter, "GPS Time (UTC)")
            
            # Draw time
            time_font = QFont('Courier New', 24)
            time_font.setBold(True)
            painter.setFont(time_font)
            painter.drawText(QRectF(0, 20, self.width(), self.height()-20),
                            Qt.AlignCenter, time_str)
        finally:
            painter.end()