"""metadata_panel.py — UI for the Metadata extraction phase.
exports: MetadataPanel
used_by: ui/main_window.py
rules:
Must display warnings for telemetry issues (like RTK float) prominently.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt

class MetadataPanel(QWidget):
    """UI for viewing metadata extraction results and warnings."""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Title
        title = QLabel("Metadata Extraction & Validation")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Start Button
        self.btn_extract = QPushButton("Extract Metadata")
        self.btn_extract.setMinimumHeight(40)
        self.btn_extract.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold;")
        layout.addWidget(self.btn_extract)
        
        layout.addSpacing(20)
        
        # Summary Section
        summary_layout = QHBoxLayout()
        self.lbl_processed = QLabel("Images Processed: 0")
        self.lbl_warnings = QLabel("Warnings/Errors: 0")
        self.lbl_warnings.setStyleSheet("color: #FF5555; font-weight: bold;")
        
        summary_layout.addWidget(self.lbl_processed)
        summary_layout.addWidget(self.lbl_warnings)
        summary_layout.addStretch()
        layout.addLayout(summary_layout)
        
        layout.addSpacing(10)
        
        # Results Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Filename", "Camera", "Altitude", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                color: white;
                gridline-color: #3E3E42;
            }
            QHeaderView::section {
                background-color: #2D2D30;
                color: white;
                padding: 4px;
                border: 1px solid #3E3E42;
            }
        """)
        
        layout.addWidget(self.table)
        
    def add_result(self, filename: str, camera: str, altitude: str, status: str, is_warning: bool = False):
        """Adds a row to the results table."""
        row_pos = self.table.rowCount()
        self.table.insertRow(row_pos)
        
        self.table.setItem(row_pos, 0, QTableWidgetItem(filename))
        self.table.setItem(row_pos, 1, QTableWidgetItem(camera))
        self.table.setItem(row_pos, 2, QTableWidgetItem(altitude))
        
        status_item = QTableWidgetItem(status)
        if is_warning:
            status_item.setForeground(Qt.GlobalColor.red)
        else:
            status_item.setForeground(Qt.GlobalColor.green)
            
        self.table.setItem(row_pos, 3, status_item)
