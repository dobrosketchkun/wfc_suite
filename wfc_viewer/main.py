#!/usr/bin/env python3
"""
WFC Viewer - Wave Function Collapse Grid Editor
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.ui import MainWindow


def main():
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("WFC Viewer")
    app.setApplicationVersion("1.0.0")
    
    # Set application style
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

