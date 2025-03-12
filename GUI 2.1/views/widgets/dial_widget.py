from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont, QFontMetrics
import math

class SpeedDialWidget(QWidget):
    """Widget to display a speed dial gauge"""
    
    def __init__(self, title="Speed", unit="m/s", max_value=100, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.max_value = max_value
        self.value = 0
        self.setMinimumSize(120, 120)
    
    def setValue(self, value):
        """Set the dial value"""
        self.value = value
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        """Draw the speed dial"""
        size = min(self.width(), self.height())
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate radius
            radius = size / 2 - 10
            
            # Draw title
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 10)
            font.setBold(True)
            painter.setFont(font)
            title_rect = QRectF(0, 5, self.width(), 20)
            painter.drawText(title_rect, Qt.AlignCenter, self.title)
            
            # Draw outer circle (bezel) - Converting to int
            painter.setPen(QPen(QColor(80, 80, 80), 2))
            painter.setBrush(QBrush(QColor(30, 30, 30)))
            painter.drawEllipse(int(center_x - radius), int(center_y - radius + 10), 
                              int(radius * 2), int(radius * 2))
            
            # Draw inner circle (face) - Converting to int
            inner_radius = radius - 5
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.setBrush(QBrush(QColor(20, 20, 20)))
            painter.drawEllipse(int(center_x - inner_radius), int(center_y - inner_radius + 10), 
                              int(inner_radius * 2), int(inner_radius * 2))
            
            # Draw tick marks and labels
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            font = QFont("Arial", 8)
            painter.setFont(font)
            
            # Sweep angle from 225 to -45 degrees (270 degrees total)
            start_angle = 225
            end_angle = -45
            sweep_angle = 270
            
            for i in range(0, 11):
                # Calculate angle for this tick mark (0 to 10 => 0% to 100%)
                angle = start_angle - (i / 10) * sweep_angle
                rad_angle = math.radians(angle)
                
                # Calculate tick mark start and end points
                outer_pt_x = center_x + inner_radius * math.cos(rad_angle)
                outer_pt_y = center_y + inner_radius * math.sin(rad_angle) + 10
                
                inner_pt_x = center_x + (inner_radius - 10) * math.cos(rad_angle)
                inner_pt_y = center_y + (inner_radius - 10) * math.sin(rad_angle) + 10
                
                # Draw tick mark - Converting to int
                painter.setPen(QPen(QColor(200, 200, 200), 1 if i % 5 == 0 else 0.5))
                painter.drawLine(int(outer_pt_x), int(outer_pt_y), 
                               int(inner_pt_x), int(inner_pt_y))
                
                # Draw label for major ticks
                if i % 5 == 0:
                    label_value = int((i / 10) * self.max_value)
                    label_radius = inner_radius - 20
                    label_x = center_x + label_radius * math.cos(rad_angle)
                    label_y = center_y + label_radius * math.sin(rad_angle) + 10
                    
                    # Calculate label size for correct positioning
                    fm = QFontMetrics(font)
                    label_width = fm.horizontalAdvance(str(label_value))
                    label_height = fm.height()
                    
                    label_rect = QRectF(label_x - label_width/2, 
                                      label_y - label_height/2,
                                      label_width, label_height)
                    
                    painter.drawText(label_rect, Qt.AlignCenter, str(label_value))
            
            # Draw current value
            painter.setPen(QColor(0, 255, 0))
            painter.setFont(QFont("Arial", 16, QFont.Bold))
            value_text = f"{self.value:.1f}"
            painter.drawText(QRectF(center_x - 40, center_y + 20, 80, 30), 
                           Qt.AlignCenter, value_text)
            
            # Draw unit
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(QRectF(center_x - 40, center_y + 40, 80, 20), 
                           Qt.AlignCenter, self.unit)
            
            # Calculate needle angle based on value
            if self.value > self.max_value:
                needle_angle = end_angle
            else:
                ratio = min(1.0, max(0.0, self.value / self.max_value))
                needle_angle = start_angle - ratio * sweep_angle
            
            rad_needle_angle = math.radians(needle_angle)
            
            # Draw needle
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            
            # Define points for the needle
            needle_length = inner_radius - 15
            needle_width = 3
            
            needle_tip_x = center_x + needle_length * math.cos(rad_needle_angle)
            needle_tip_y = center_y + needle_length * math.sin(rad_needle_angle) + 10
            
            # Calculate perpendicular points for needle base
            perp_angle = rad_needle_angle + math.pi/2
            base_x1 = center_x + needle_width * math.cos(perp_angle)
            base_y1 = center_y + needle_width * math.sin(perp_angle) + 10
            
            base_x2 = center_x - needle_width * math.cos(perp_angle)
            base_y2 = center_y - needle_width * math.sin(perp_angle) + 10
            
            # Draw needle as a triangle - Converting to int
            painter.drawPolygon([
                QPoint(int(needle_tip_x), int(needle_tip_y)),
                QPoint(int(base_x1), int(base_y1)),
                QPoint(int(base_x2), int(base_y2))
            ])
            
            # Draw center hub - Converting to int
            painter.setBrush(QBrush(QColor(100, 100, 100)))
            painter.drawEllipse(int(center_x - 5), int(center_y - 5 + 10), 10, 10)
            
        finally:
            painter.end()