"""app.py — Main application entrypoint.
exports: main
used_by: __main__.py
rules:
Initialize database, wire UI events, and manage the main event loop.
"""

import sys
from PyQt6.QtWidgets import QApplication
from optictriage.ui.main_window import MainWindow
from optictriage.ui.import_panel import ImportPanel
from optictriage.ui.metadata_panel import MetadataPanel
from optictriage.ui.dashboard import HealthDashboard
from optictriage.ui.export_panel import ExportPanel
from optictriage.database import DatabaseManager

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Initialize DB
    db_manager = DatabaseManager()
    db_manager.create_all()
    
    # Initialize UI
    window = MainWindow()
    
    # Wire up pages
    import_panel = ImportPanel()
    metadata_panel = MetadataPanel()
    dashboard_panel = HealthDashboard()
    export_panel = ExportPanel()
    
    window.content_stack.addWidget(import_panel)
    window.content_stack.addWidget(metadata_panel)
    window.content_stack.addWidget(dashboard_panel)
    window.content_stack.addWidget(export_panel)
    
    # Navigation
    window.btn_import.clicked.connect(lambda: window.content_stack.setCurrentWidget(import_panel))
    window.btn_metadata.clicked.connect(lambda: window.content_stack.setCurrentWidget(metadata_panel))
    
    # Assuming there's a btn_quality in MainWindow for the dashboard
    if hasattr(window, 'btn_quality'):
        window.btn_quality.clicked.connect(lambda: window.content_stack.setCurrentWidget(dashboard_panel))
        
    if hasattr(window, 'btn_export'):
        window.btn_export.clicked.connect(lambda: window.content_stack.setCurrentWidget(export_panel))
    
    window.content_stack.setCurrentWidget(import_panel)
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
