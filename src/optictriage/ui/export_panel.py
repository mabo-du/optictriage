"""export_panel.py — UI for configuring and triggering export.
exports: ExportPanel
used_by: app.py
rules:
Include software selector, output path browser, progress indicator, and 'Open Folder' button.
"""

import os
import subprocess
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QCheckBox, QProgressBar, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal

class ExportPanel(QWidget):
    """UI for configuring and running the final Export Stage."""
    
    # Signal emitted when 'Run Export' is clicked, passing settings dict
    start_export = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.last_export_path = None
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        title = QLabel("Export & Finalize")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Software Selectors
        group = QGroupBox("Select Downstream Software")
        group.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        vbox = QVBoxLayout()
        
        self.chk_metashape = QCheckBox("Agisoft Metashape (.py script)")
        self.chk_odm = QCheckBox("OpenDroneMap (cameras.json, gcp_list.txt)")
        self.chk_colmap = QCheckBox("COLMAP (database.db, project.ini)")
        
        # Default all true
        self.chk_metashape.setChecked(True)
        self.chk_odm.setChecked(True)
        self.chk_colmap.setChecked(True)
        
        vbox.addWidget(self.chk_metashape)
        vbox.addWidget(self.chk_odm)
        vbox.addWidget(self.chk_colmap)
        group.setLayout(vbox)
        layout.addWidget(group)
        
        layout.addSpacing(20)
        
        # Run Button
        self.btn_export = QPushButton("Run Export")
        self.btn_export.setMinimumHeight(50)
        self.btn_export.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold; font-size: 16px;")
        self.btn_export.clicked.connect(self._on_export_clicked)
        layout.addWidget(self.btn_export)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)
        
        # Open Folder Button
        self.btn_open_folder = QPushButton("Open Output Folder")
        self.btn_open_folder.setVisible(False)
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        layout.addWidget(self.btn_open_folder)
        
        layout.addStretch()

    def _on_export_clicked(self):
        settings = {
            "export_metashape": self.chk_metashape.isChecked(),
            "export_odm": self.chk_odm.isChecked(),
            "export_colmap": self.chk_colmap.isChecked()
        }
        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Starting export...")
        self.btn_open_folder.setVisible(False)
        
        self.start_export.emit(settings)

    def update_progress(self, val: float, msg: str, export_path: str = None):
        self.progress_bar.setValue(int(val))
        self.lbl_status.setText(msg)
        
        if val >= 100.0:
            self.btn_export.setEnabled(True)
            if export_path:
                self.last_export_path = export_path
                self.btn_open_folder.setVisible(True)

    def _open_output_folder(self):
        if not self.last_export_path:
            return
            
        path = self.last_export_path
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
