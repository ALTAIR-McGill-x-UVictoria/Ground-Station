from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont
import math

class CompassWidget(QWidget):
    """Widget to display a compass with heading indicator"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.heading = 0  # Heading in degrees (0-359)
        self.setMinimumSize(100, 100)
    
    def set_heading(self, heading):
        """Set the compass heading in degrees"""
        # Normalize to 0-359 range
        self.heading = heading % 360
        self.update()  # Trigger repaint
        
    # Compatibility method - maintain both naming conventions
    def setHeading(self, heading):
        self.set_heading(heading)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Get widget dimensions
            widget_size = self.size()
            widget_width = widget_size.width()
            widget_height = widget_size.height()
            
            # Calculate center and radius
            center_x = widget_width / 2
            center_y = widget_height / 2
            radius = min(center_x, center_y) - 10  # Leave some margin
            
            # Create center point
            center = QPoint(int(center_x), int(center_y))
            
            # Draw outer circle (bezel)
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.setBrush(QBrush(QColor(30, 30, 30)))
            painter.drawEllipse(center, int(radius), int(radius))
            
            # Draw inner circle (face)
            inner_radius = int(radius - 5)
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.setBrush(QBrush(QColor(20, 20, 20)))
            painter.drawEllipse(center, inner_radius, inner_radius)
            
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
                painter.drawText(int(x) - 5, int(y) + 5, label)
            
            # Draw tick marks every 30 degrees
            for tick in range(0, 360, 30):
                if tick % 90 != 0:  # Skip cardinal points
                    # Adjust angle for heading rotation
                    adjusted_angle = (tick - self.heading) % 360
                    rad_angle = math.radians(adjusted_angle - 90)
                    
                    # Calculate start and end points for tick
                    outer_x = center_x + (radius - 2) * math.cos(rad_angle)
                    outer_y = center_y + (radius - 2) * math.sin(rad_angle)
                    inner_x = center_x + (radius - 10) * math.cos(rad_angle)
                    inner_y = center_y + (radius - 10) * math.sin(rad_angle)
                    
                    # Draw tick
                    painter.setPen(QPen(QColor(150, 150, 150), 1))
                    painter.drawLine(int(outer_x), int(outer_y), int(inner_x), int(inner_y))
            
            # Draw heading indicator (triangle at top)
            painter.setPen(QPen(QColor(255, 165, 0), 2))
            painter.setBrush(QBrush(QColor(255, 165, 0)))
            
            heading_indicator = []
            heading_indicator.append(QPoint(int(center_x), int(center_y - radius + 2)))
            heading_indicator.append(QPoint(int(center_x - 8), int(center_y - radius + 12)))
            heading_indicator.append(QPoint(int(center_x + 8), int(center_y - radius + 12)))
            
            painter.drawPolygon(heading_indicator)
            
            # Draw heading value
            heading_text = f"{int(self.heading)}°"
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRect(int(center_x - 20), int(center_y + 15), 40, 20), 
                           Qt.AlignCenter, heading_text)
                
        finally:
            # Make sure to end the painter
            painter.end()