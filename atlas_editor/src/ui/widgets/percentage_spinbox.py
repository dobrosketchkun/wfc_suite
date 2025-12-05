"""
Custom spinbox for percentage input.
"""

from PySide6.QtWidgets import QDoubleSpinBox
from PySide6.QtCore import Signal


class PercentageSpinBox(QDoubleSpinBox):
    """
    A spinbox specifically for percentage values (0-100).
    Shows % suffix and validates input.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0.0, 100.0)
        self.setDecimals(1)
        self.setSuffix("%")
        self.setSingleStep(5.0)
        self.setValue(100.0)
        
        # Style
        self.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 2px 5px;
                min-width: 70px;
            }
            QDoubleSpinBox:focus {
                border-color: #4a90d9;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background-color: #4a4a4a;
                border: none;
                width: 16px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #5a5a5a;
            }
        """)

