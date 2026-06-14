"""dashboard.py — Health Dashboard UI.
exports: HealthDashboard
used_by: app.py
rules:
Integrate blur histogram, summaries, and flagged image gallery.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QScrollArea, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
from optictriage.ui.blur_histogram import BlurHistogramWidget

class HealthDashboard(QWidget):
    """UI for viewing overall dataset quality and managing flagged images."""
    
    def __init__(self):
        super().__init__()
        self._blur_scores = []
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Title
        title = QLabel("Quality Health Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Start Stage Button
        self.btn_run_quality = QPushButton("Run Quality Scoring")
        self.btn_run_quality.setMinimumHeight(40)
        self.btn_run_quality.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold;")
        layout.addWidget(self.btn_run_quality)
        
        layout.addSpacing(20)
        
        # Top row: Histogram and Summaries
        top_row = QHBoxLayout()
        
        # Histogram
        self.blur_histogram = BlurHistogramWidget()
        self.blur_histogram.threshold_changed.connect(self._on_threshold_changed)
        top_row.addWidget(self.blur_histogram, stretch=2)
        
        # Summary Stats
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #2D2D30; border-radius: 8px;")
        stats_layout = QVBoxLayout(stats_frame)
        
        lbl_stats_title = QLabel("Dataset Statistics")
        lbl_stats_title.setStyleSheet("font-size: 16px; font-weight: bold; border-bottom: 1px solid #3E3E42;")
        stats_layout.addWidget(lbl_stats_title)
        
        self.lbl_total = QLabel("Total Images: 0")
        self.lbl_overexposed = QLabel("Overexposed: 0")
        self.lbl_glare = QLabel("Veiling Glare: 0")
        self.lbl_blurry = QLabel("Blurry (Below Threshold): 0")
        
        for lbl in (self.lbl_total, self.lbl_overexposed, self.lbl_glare, self.lbl_blurry):
            lbl.setStyleSheet("font-size: 14px;")
            stats_layout.addWidget(lbl)
            
        stats_layout.addStretch()
        top_row.addWidget(stats_frame, stretch=1)
        
        layout.addLayout(top_row)
        layout.addSpacing(20)
        
        # Flagged Image Gallery
        gallery_title = QLabel("Flagged Images Review")
        gallery_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(gallery_title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #1E1E1E; border: 1px solid #3E3E42;")
        
        self.gallery_widget = QWidget()
        self.gallery_layout = QGridLayout(self.gallery_widget)
        self.gallery_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.gallery_widget)
        layout.addWidget(scroll)

    def _on_threshold_changed(self, threshold: float):
        if not self._blur_scores:
            return
        # Live recalculate how many are below the new threshold
        blurry_count = sum(1 for s in self._blur_scores if s < threshold)
        self.lbl_blurry.setText(f"Blurry (Below Threshold): {blurry_count}")

    def update_stats(self, total: int, overexposed: int, glare: int, blurry: int, blur_scores: list[float] = None):
        self.lbl_total.setText(f"Total Images: {total}")
        self.lbl_overexposed.setText(f"Overexposed: {overexposed}")
        self.lbl_glare.setText(f"Veiling Glare: {glare}")
        self.lbl_blurry.setText(f"Blurry (Below Threshold): {blurry}")
        if blur_scores is not None:
            self._blur_scores = blur_scores
            self.blur_histogram.update_data(blur_scores)
