"""
Collapsible section widget.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from typing import Optional


class CollapsibleSection(QWidget):
    """
    A collapsible section with a clickable header that shows/hides content.
    """
    toggled = Signal(bool)  # Emits True when expanded, False when collapsed
    
    def __init__(self, title: str, parent: Optional[QWidget] = None, collapsed: bool = False):
        super().__init__(parent)
        self._collapsed = collapsed
        self._title = title
        
        self._setup_ui()
        
        # Set initial state
        if collapsed:
            self._content_widget.hide()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header button
        self._header_btn = QPushButton()
        self._update_header_text()
        self._header_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #aaa;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                text-align: left;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #454545;
                color: #ccc;
            }
        """)
        self._header_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_btn.clicked.connect(self._toggle)
        layout.addWidget(self._header_btn)
        
        # Content widget
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 2, 0, 0)
        self._content_layout.setSpacing(3)
        layout.addWidget(self._content_widget)
    
    def _update_header_text(self):
        arrow = "▼" if not self._collapsed else "▶"
        self._header_btn.setText(f"{arrow} {self._title}")
    
    def _toggle(self):
        self._collapsed = not self._collapsed
        self._content_widget.setVisible(not self._collapsed)
        self._update_header_text()
        self.toggled.emit(not self._collapsed)
    
    def add_widget(self, widget: QWidget):
        """Add a widget to the collapsible content area."""
        self._content_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """Add a layout to the collapsible content area."""
        self._content_layout.addLayout(layout)
    
    def set_collapsed(self, collapsed: bool):
        """Set the collapsed state."""
        if self._collapsed != collapsed:
            self._toggle()
    
    def is_collapsed(self) -> bool:
        """Check if the section is collapsed."""
        return self._collapsed
    
    @property
    def content_layout(self):
        """Get the content layout for adding widgets directly."""
        return self._content_layout

