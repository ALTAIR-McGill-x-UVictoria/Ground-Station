from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt

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
        # Update the list of all fields ever seen, preserving order
        for key in packet.keys():
            if key not in self.all_fields:
                self.all_fields.append(key)
        self.table.setRowCount(len(self.all_fields))
        for row, field in enumerate(self.all_fields):
            key_item = QTableWidgetItem(str(field))
            key_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            value = packet.get(field, "")
            value_item = QTableWidgetItem(str(value))
            value_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)
