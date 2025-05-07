from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont
import math

class CompassWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bearing = 0
        self.setMinimumSize(150, 150)
        
    def setBearing(self, bearing):
        self.bearing = float(bearing)
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
            
            # Draw cardinal points
            painter.setPen(QPen(QColor('#666666'), 1))
            font = QFont('Arial', 10)
            font.setBold(True)
            painter.setFont(font)
            
            points_text = [('N', 0), ('E', 90), ('S', 180), ('W', 270)]
            for label, angle in points_text:
                x = int(center_x + (radius - 20) * math.sin(math.radians(angle)))
                y = int(center_y - (radius - 20) * math.cos(math.radians(angle)))
                # Create a QRect for text placement
                text_rect = QRectF(x - 10, y - 10, 20, 20)
                painter.drawText(text_rect, Qt.AlignCenter, label)
            
            # Draw direction arrow instead of simple line
            painter.setPen(QPen(QColor('#00ff00'), 2))
            painter.setBrush(QBrush(QColor('#00ff00')))
            
            # Calculate arrow points
            needle_length = radius - 15
            arrow_width = 10
            
            # Arrow tip
            tip_x = center_x + needle_length * math.sin(math.radians(self.bearing))
            tip_y = center_y - needle_length * math.cos(math.radians(self.bearing))
            
            # Arrow base points
            base1_x = center_x + arrow_width * math.sin(math.radians(self.bearing + 90))
            base1_y = center_y - arrow_width * math.cos(math.radians(self.bearing + 90))
            base2_x = center_x + arrow_width * math.sin(math.radians(self.bearing - 90))
            base2_y = center_y - arrow_width * math.cos(math.radians(self.bearing - 90))
            
            # Draw arrow
            arrow_points = [
                QPoint(int(tip_x), int(tip_y)),
                QPoint(int(base1_x), int(base1_y)),
                QPoint(int(base2_x), int(base2_y))
            ]
            painter.drawPolygon(arrow_points)
            
            # Draw bearing value
            painter.setPen(QPen(QColor('#00ff00'), 1))
            font = QFont('Arial', 12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, center_y + radius/2, self.width(), 30),
                            Qt.AlignHCenter,
                            f"{self.bearing:.1f}°")
        finally:
            # Make sure to end the painter
            painter.end()