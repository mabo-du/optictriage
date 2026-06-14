"""import_panel.py — UI for the Import Phase.
exports: ImportPanel
used_by: ui/main_window.py
rules:
Must remain responsive while pipeline runs in the background.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFileDialog, QLineEdit, QSpinBox, QSlider, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt

class ImportPanel(QWidget):
    """UI for selecting input/output folders and triggering import."""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Title
        title = QLabel("Import Dataset")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Input Folder Selection
        input_layout = QHBoxLayout()
        self.lbl_input = QLabel("Input Folder:")
        self.lbl_input.setFixedWidth(100)
        self.txt_input = QLineEdit()
        self.txt_input.setReadOnly(True)
        self.btn_browse_input = QPushButton("Browse...")
        self.btn_browse_input.clicked.connect(self._browse_input)
        
        input_layout.addWidget(self.lbl_input)
        input_layout.addWidget(self.txt_input)
        input_layout.addWidget(self.btn_browse_input)
        layout.addLayout(input_layout)
        
        # Output Folder Selection
        output_layout = QHBoxLayout()
        self.lbl_output = QLabel("Output Folder:")
        self.lbl_output.setFixedWidth(100)
        self.txt_output = QLineEdit()
        self.txt_output.setReadOnly(True)
        self.btn_browse_output = QPushButton("Browse...")
        self.btn_browse_output.clicked.connect(self._browse_output)
        
        output_layout.addWidget(self.lbl_output)
        output_layout.addWidget(self.txt_output)
        output_layout.addWidget(self.btn_browse_output)
        layout.addLayout(output_layout)
        
        # V2.0 Advanced Settings
        adv_group = QGroupBox("v2.0 Advanced Settings")
        adv_layout = QFormLayout()
        
        # GPX Alignment
        gpx_layout = QHBoxLayout()
        self.txt_gpx = QLineEdit()
        self.txt_gpx.setPlaceholderText("Optional: Select .gpx file for GPS alignment")
        self.txt_gpx.setReadOnly(True)
        self.btn_browse_gpx = QPushButton("Browse...")
        self.btn_browse_gpx.clicked.connect(self._browse_gpx)
        gpx_layout.addWidget(self.txt_gpx)
        gpx_layout.addWidget(self.btn_browse_gpx)
        
        self.spin_gpx_offset = QSpinBox()
        self.spin_gpx_offset.setRange(-3600, 3600)
        self.spin_gpx_offset.setValue(0)
        self.spin_gpx_offset.setSuffix(" seconds")
        self.spin_gpx_offset.setToolTip("Offset camera clock relative to GPS time")
        
        adv_layout.addRow("GPX Track:", gpx_layout)
        adv_layout.addRow("GPX Time Offset:", self.spin_gpx_offset)
        
        # PHash Threshold
        self.slider_phash = QSlider(Qt.Orientation.Horizontal)
        self.slider_phash.setRange(0, 16)
        self.slider_phash.setValue(5)
        self.slider_phash.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_phash.setTickInterval(1)
        
        self.lbl_phash_val = QLabel("5 (Hamming Distance)")
        self.slider_phash.valueChanged.connect(lambda v: self.lbl_phash_val.setText(f"{v} (Hamming Distance)"))
        
        phash_layout = QHBoxLayout()
        phash_layout.addWidget(self.slider_phash)
        phash_layout.addWidget(self.lbl_phash_val)
        
        adv_layout.addRow("Perceptual Hash Threshold:", phash_layout)
        
        adv_group.setLayout(adv_layout)
        layout.addWidget(adv_group)
        layout.addSpacing(10)
        
        # Start Button
        self.btn_start = QPushButton("Start Import")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold;")
        layout.addSpacing(10)
        layout.addWidget(self.btn_start)
        
        # Stats & Preview Section (Phase 1.8 Deliverables)
        stats_layout = QHBoxLayout()
        
        # Thumbnail display
        self.lbl_thumbnail = QLabel("No Image Selected")
        self.lbl_thumbnail.setFixedSize(160, 120)
        self.lbl_thumbnail.setStyleSheet("background-color: #1E1E1E; border: 1px solid #3E3E42;")
        self.lbl_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.lbl_thumbnail)
        
        # Info display
        info_layout = QVBoxLayout()
        self.lbl_format_summary = QLabel("Format Summary: N/A")
        self.lbl_duplicate_count = QLabel("Duplicates Flagged: 0")
        info_layout.addWidget(self.lbl_format_summary)
        info_layout.addWidget(self.lbl_duplicate_count)
        info_layout.addStretch()
        stats_layout.addLayout(info_layout)
        
        layout.addSpacing(20)
        layout.addLayout(stats_layout)
        layout.addStretch()

    def _browse_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.txt_input.setText(folder)
            
    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.txt_output.setText(folder)
            
    def _browse_gpx(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select GPX File", "", "GPX Files (*.gpx)")
        if file:
            self.txt_gpx.setText(file)
