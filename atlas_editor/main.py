#!/usr/bin/env python3
"""
WFC Atlas Editor - A visual editor for Wave Function Collapse tile atlases and rules.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.ui import MainWindow


def main():
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("WFC Atlas Editor")
    app.setOrganizationName("WFC")
    app.setApplicationVersion("1.0.0")
    
    # Set default font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

