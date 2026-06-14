"""blur_histogram.py — Interactive blur score histogram.
exports: BlurHistogramWidget
used_by: ui/dashboard.py → HealthDashboard
rules:
Must allow draggable threshold line that updates blur bounds.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class BlurHistogramWidget(QWidget):
    """
    Displays a histogram of blur scores with a draggable threshold line.
    Emits threshold_changed(float) when the user moves the line.
    """
    threshold_changed = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Setup Figure and Canvas
        self.figure = Figure(figsize=(6, 4), facecolor='#1E1E1E')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Setup Axis
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#1E1E1E')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.set_xlabel("Laplacian Variance (Sharpness)")
        self.ax.set_ylabel("Image Count")
        
        self.threshold_line = None
        self.threshold_value = 50.0  # default arbitrary
        self.scores = []
        
        # Interaction State
        self._dragging = False
        self.canvas.mpl_connect('button_press_event', self._on_press)
        self.canvas.mpl_connect('button_release_event', self._on_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_motion)

    def update_data(self, scores: list[float]):
        self.scores = scores
        self.ax.clear()
        
        self.ax.set_xlabel("Laplacian Variance (Sharpness)")
        self.ax.set_ylabel("Image Count")
        
        if scores:
            counts, bins, patches = self.ax.hist(scores, bins=50, color='#007ACC', alpha=0.7)
            # Re-draw threshold line
            if self.threshold_line is None:
                # Set initial threshold to roughly the bottom 10%
                self.threshold_value = np.percentile(scores, 10)
            
            self.threshold_line = self.ax.axvline(x=self.threshold_value, color='#FF5555', linewidth=2, linestyle='--')
        
        self.canvas.draw()

    def _on_press(self, event):
        if event.inaxes != self.ax or self.threshold_line is None:
            return
        
        # Check if click is near the threshold line
        xdata = self.threshold_line.get_xdata()[0]
        if abs(event.xdata - xdata) < (self.ax.get_xlim()[1] - self.ax.get_xlim()[0]) * 0.05:
            self._dragging = True

    def _on_release(self, event):
        if self._dragging:
            self._dragging = False
            # Final emit on release
            self.threshold_changed.emit(self.threshold_value)

    def _on_motion(self, event):
        if not self._dragging or event.inaxes != self.ax:
            return
        
        self.threshold_value = event.xdata
        self.threshold_line.set_xdata([self.threshold_value, self.threshold_value])
        self.canvas.draw_idle()
        # Live emit during drag
        self.threshold_changed.emit(self.threshold_value)
