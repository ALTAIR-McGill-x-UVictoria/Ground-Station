from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont
import math

class CompassWidget(QWidget):
    """Widget to display a compass with heading indicator"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.heading = 0  # Heading in degrees (0-359)
        self.setMinimumSize(100, 100)
    
    def setHeading(self, heading):
        """Set the compass heading in degrees"""
        # Normalize to 0-359 range
        self.heading = heading % 360
        self.update()  # Trigger repaint
        
    def paintEvent(self, event):
        """Draw the compass"""
        size = min(self.width(), self.height())
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate radius and margins
            radius = size / 2 - 10
            
            # Draw outer circle (bezel) - Converting to int
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.setBrush(QBrush(QColor(30, 30, 30)))
            painter.drawEllipse(int(center_x - radius), int(center_y - radius), 
                              int(radius * 2), int(radius * 2))
            
            # Draw inner circle (face) - Converting to int
            inner_radius = radius - 5
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.setBrush(QBrush(QColor(20, 20, 20)))
            painter.drawEllipse(int(center_x - inner_radius), int(center_y - inner_radius), 
                              int(inner_radius * 2), int(inner_radius * 2))
            
            # Draw cardinal points
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            font = QFont("Arial", 10)
            font.setBold(True)
            painter.setFont(font)
            
            # Define cardinal points and their angles
            cardinals = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
            
            for label, angle in cardinals:
                # Adjust angle for heading rotation
                adjusted_angle = (angle - self.heading) % 360
                rad_angle = math.radians(adjusted_angle - 90)  # -90 to align with trigonometric direction
                
                # Calculate position
                text_radius = inner_radius - 20
                x = center_x + text_radius * math.cos(rad_angle)
                y = center_y + text_radius * math.sin(rad_angle)
                
                # Draw cardinal point
                text_color = QColor(255, 0, 0) if label == "N" else QColor(255, 255, 255)
                painter.setPen(text_color)
                painter.drawText(QRectF(x - 10, y - 10, 20, 20), 
                               Qt.AlignCenter, label)
            
            # Draw tick marks every 30 degrees
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            for i in range(0, 360, 30):
                # Adjust angle for heading rotation
                adjusted_angle = (i - self.heading) % 360
                rad_angle = math.radians(adjusted_angle - 90)
                
                # Calculate start and end points
                outer_pt_x = center_x + inner_radius * math.cos(rad_angle)
                outer_pt_y = center_y + inner_radius * math.sin(rad_angle)
                
                inner_pt_x = center_x + (inner_radius - 10) * math.cos(rad_angle)
                inner_pt_y = center_y + (inner_radius - 10) * math.sin(rad_angle)
                
                # Draw tick mark - Converting to int
                painter.drawLine(int(outer_pt_x), int(outer_pt_y), 
                               int(inner_pt_x), int(inner_pt_y))
            
            # Draw heading indicator (triangle at top)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            
            indicator_size = 10
            
            # Create a triangle pointing up
            points = [
                QPoint(int(center_x), int(center_y - radius + 2)),
                QPoint(int(center_x - indicator_size/2), int(center_y - radius + indicator_size + 2)),
                QPoint(int(center_x + indicator_size/2), int(center_y - radius + indicator_size + 2))
            ]
            
            painter.drawPolygon(points)
            
            # Draw heading text in the center
            painter.setPen(QColor(0, 255, 0))
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            painter.drawText(QRectF(center_x - 30, center_y - 15, 60, 30), 
                           Qt.AlignCenter, f"{int(self.heading)}°")
            
        finally:
            painter.end()