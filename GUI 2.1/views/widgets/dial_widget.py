from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont
import math

class SpeedDialWidget(QWidget):
    def __init__(self, title, unit, max_value=100, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.value = 0
        self.max_value = max_value
        self.setMinimumSize(100, 100)
        
    def setValue(self, value):
        self.value = min(float(value), float(self.max_value))  # Ensure float comparison and clamp
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate center and radius
            center_x = self.width() // 2
            center_y = self.height() // 2
            radius = min(center_x, center_y) - 10
            
            # Draw outer circle
            painter.setPen(QPen(QColor('#3a3a3a'), 2))
            painter.setBrush(QBrush(QColor('#2a2a2a')))
            painter.drawEllipse(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
            
            # Draw title
            painter.setPen(QPen(QColor('#00ff00'), 1))
            font = QFont('Arial', 12)  # Increased from 9
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, 8, self.width(), 25),  # Adjusted spacing
                           Qt.AlignHCenter, self.title)
            
            # Draw scale markers
            painter.setPen(QPen(QColor('#666666'), 1))
            for i in range(11):  # 0 to max_value in 10 steps
                angle = -120 + (i * 240 / 10)  # -120° to +120°
                inner_x = center_x + (radius - 15) * math.cos(math.radians(angle))
                inner_y = center_y + (radius - 15) * math.sin(math.radians(angle))
                outer_x = center_x + (radius - 5) * math.cos(math.radians(angle))
                outer_y = center_y + (radius - 5) * math.sin(math.radians(angle))
                painter.drawLine(int(inner_x), int(inner_y), 
                               int(outer_x), int(outer_y))
            
            # Draw value needle
            painter.setPen(QPen(QColor('#ff0000'), 2))
            if self.max_value == 0: # Avoid division by zero
                value_angle = -120
            else:
                value_angle = -120 + (self.value * 240 / self.max_value)
            needle_length = radius - 10
            end_x = center_x + needle_length * math.cos(math.radians(value_angle))
            end_y = center_y + needle_length * math.sin(math.radians(value_angle))
            painter.drawLine(center_x, center_y, int(end_x), int(end_y))
            
            # Draw center dot
            painter.setBrush(QBrush(QColor('#ff0000')))
            painter.drawEllipse(QPoint(center_x, center_y), 5, 5)
            
            # Draw value text
            painter.setPen(QPen(QColor('#ffffff'), 1))
            font = QFont('Arial', 14)  # Increased from 11
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, center_y + 15, self.width(), 30),  # Adjusted spacing
                           Qt.AlignHCenter,
                           f"{self.value:.1f} {self.unit}")
        finally:
            painter.end()