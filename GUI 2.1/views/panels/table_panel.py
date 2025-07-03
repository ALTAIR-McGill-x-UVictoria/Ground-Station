from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt
import datetime

class TablePanel(QWidget):
    """Panel to display the latest received radio data packet in a vertical key-value table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Store the last set of fields to keep the table structure consistent
        self.all_fields = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setRowCount(0)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #232323;
                color: #ffcc00;
                font-family: 'Courier New', monospace;
                font-size: 16pt;
                border: none;
                gridline-color: #666666;
                selection-background-color: #444444;
                selection-color: #ffffff;
            }
            QTableWidget::item:selected {
                background: #444444;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #222222;
                color: #ffcc00;
                font-weight: bold;
                border: 1px solid #444444;
                padding: 8px;
                font-size: 16pt;
            }
        """)
        self.table.setHorizontalHeaderLabels(["Field", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def add_packet(self, packet: dict):
        """Show only the latest packet (dict) in the table, one field per row.
        Keep all fields ever seen, and update their values as new packets arrive.
        """
        if not isinstance(packet, dict):
            return
            
        # Update the list of all fields ever seen, preserving order
        for key in packet.keys():
            if key not in self.all_fields:
                self.all_fields.append(key)
                
        # Sort fields in a logical order: important fields first
        priority_fields = [
            'ack', 'rssi', 'snr', 
            'gps_lat', 'gps_lon', 'gps_alt', 'gps_valid', 'gps_time',
            'altitude', 'temperature', 'pressure', 'ground_speed',
            'fc_battery_voltage', 'led_battery_voltage',
            'photodiode_value1', 'photodiode_value2'
        ]
        
        # Start with priority fields that exist in the packet
        ordered_fields = [field for field in priority_fields if field in packet]
        
        # Add remaining fields
        remaining_fields = [field for field in packet if field not in priority_fields]
        remaining_fields.sort()  # Sort alphabetically
        
        self.all_fields = ordered_fields + remaining_fields

        self.table.setRowCount(len(self.all_fields))
        
        for row, field in enumerate(self.all_fields):
            key_item = QTableWidgetItem(str(field))
            key_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            
            # Format the value based on its type
            value = packet.get(field, "")
            if isinstance(value, float):
                if field in ['gps_lat', 'gps_lon']:
                    formatted_value = f"{value:.6f}"  # GPS coordinates with 6 decimal places
                elif field in ['gps_time'] and value > 1000000000:  # Unix timestamp
                    try:
                        # Handle microseconds if value is very large
                        if value > 1000000000000:  # Microseconds
                            dt = datetime.datetime.fromtimestamp(value / 1000000.0, tz=datetime.timezone.utc)
                        else:  # Seconds
                            dt = datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)
                        formatted_value = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                    except:
                        formatted_value = f"{value:.2f}"
                else:
                    formatted_value = f"{value:.2f}"  # 2 decimal places for other floats
            elif isinstance(value, bool):
                formatted_value = "YES" if value else "NO"
            elif isinstance(value, int):
                formatted_value = str(value)
            else:
                formatted_value = str(value) if value != "" else "N/A"
            
            value_item = QTableWidgetItem(formatted_value)
            value_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            
            # Color coding for important fields
            if field == 'gps_valid':
                if value:
                    value_item.setBackground(Qt.darkGreen)
                else:
                    value_item.setBackground(Qt.darkRed)
            elif field in ['rssi', 'snr']:
                if isinstance(value, (int, float)):
                    if field == 'rssi' and value > -80:
                        value_item.setBackground(Qt.darkGreen)
                    elif field == 'rssi' and value < -100:
                        value_item.setBackground(Qt.darkRed)
                    elif field == 'snr' and value > 5:
                        value_item.setBackground(Qt.darkGreen)
                    elif field == 'snr' and value < 0:
                        value_item.setBackground(Qt.darkRed)
            
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)

    def clear_table(self):
        """Clear all data from the table"""
        self.all_fields = []
        self.table.setRowCount(0)
