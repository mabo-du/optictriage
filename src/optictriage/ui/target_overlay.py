"""target_overlay.py — UI to view images with overlaid target boxes.
exports: TargetOverlayWidget
used_by: app.py
rules:
Must draw bounding boxes and IDs over detected markers.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PyQt6.QtCore import Qt
import json

class TargetOverlayWidget(QWidget):
    """
    Displays an image and draws boxes/points around detected targets.
    """
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.image_label = QLabel("No Image Selected")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1E1E1E;")
        layout.addWidget(self.image_label)

    def load_image(self, filepath: str, detected_targets_json: str, colorchecker_found: int):
        pixmap = QPixmap(filepath)
        if pixmap.isNull():
            return
            
        # Draw on pixmap
        painter = QPainter(pixmap)
        
        # Colorchecker Highlight
        if colorchecker_found:
            pen = QPen(QColor(0, 255, 0))
            pen.setWidth(10)
            painter.setPen(pen)
            # Draw a green border around the whole image to indicate CC presence
            painter.drawRect(0, 0, pixmap.width()-1, pixmap.height()-1)

        # Draw ArUco / ChArUco
        if detected_targets_json:
            targets = json.loads(detected_targets_json)
            for t in targets:
                if t["target_type"].startswith("aruco"):
                    pen = QPen(QColor(255, 0, 0))
                    pen.setWidth(4)
                    painter.setPen(pen)
                    corners = t["corners"]
                    # Draw polygon
                    for i in range(4):
                        x1, y1 = corners[i]
                        x2, y2 = corners[(i+1)%4]
                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                    
                    # Draw ID
                    painter.drawText(int(corners[0][0]), int(corners[0][1] - 10), f"ID: {t['id']}")
                    
                elif t["target_type"] == "charuco_corner":
                    pen = QPen(QColor(0, 0, 255))
                    pen.setWidth(6)
                    painter.setPen(pen)
                    x, y = t["corners"]
                    painter.drawPoint(int(x), int(y))
                    
        painter.end()
        
        # Scale to fit window while keeping aspect ratio
        scaled = pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        # We could redraw here to maintain aspect ratio on resize, but keeping it simple for now.
        super().resizeEvent(event)
