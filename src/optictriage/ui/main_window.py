"""main_window.py — Core PyQt6 UI shell for OpticTriage.
exports: MainWindow
used_by: app.py → main()
rules:
Keep UI unblocked; offload pipeline execution to worker threads (sherd pattern).
"""

from PyQt6.QtWidgets import (
    QMainWindow, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton, 
    QLabel,
    QStackedWidget,
    QStatusBar,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QSize

class MainWindow(QMainWindow):
    """The main shell of the OpticTriage application."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpticTriage")
        self.setMinimumSize(QSize(1024, 768))
        self._init_ui()
        
    def _init_ui(self):
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar for navigation
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: #2D2D30; color: #FFFFFF;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.btn_import = QPushButton("1. Import")
        self.btn_metadata = QPushButton("2. Metadata")
        self.btn_quality = QPushButton("3. Quality")
        self.btn_export = QPushButton("4. Export")
        
        for btn in (self.btn_import, self.btn_metadata, self.btn_quality, self.btn_export):
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    border: none;
                    font-size: 14px;
                    font-weight: bold;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #3E3E42;
                }
            """)
            sidebar_layout.addWidget(btn)
            
        main_layout.addWidget(self.sidebar)
        
        # Main content area (stacked widget)
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #1E1E1E; color: #FFFFFF;")
        
        # Placeholder pages
        self.page_import = QLabel("Import Panel Placeholder")
        self.page_import.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_stack.addWidget(self.page_import)
        
        main_layout.addWidget(self.content_stack)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.status_bar.showMessage("Ready")

    def update_progress(self, value: float, message: str = ""):
        """Updates the status bar progress indicator."""
        if message:
            self.status_bar.showMessage(message)
            
        if value >= 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(int(value))
        else:
            self.progress_bar.setVisible(False)
