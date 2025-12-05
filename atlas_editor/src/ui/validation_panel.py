"""
Validation panel - shows tiles with incomplete rules.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from typing import Optional, List

from ..models import Atlas
from ..core import validate_atlas, ValidationResult, SIDES


class ValidationItem(QFrame):
    """A single validation issue item."""
    clicked = Signal(str)  # Emits tile_id when clicked
    
    def __init__(self, tile_id: str, issues: List[str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tile_id = tile_id
        
        self.setStyleSheet("""
            ValidationItem {
                background-color: #3a3535;
                border: 1px solid #4a4040;
                border-radius: 3px;
            }
            ValidationItem:hover {
                background-color: #4a4545;
                border-color: #5a5050;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(2)
        
        # Tile ID
        id_label = QLabel(f"⚠️ {tile_id}")
        id_label.setStyleSheet("font-weight: bold; color: #f0a030;")
        layout.addWidget(id_label)
        
        # Issues
        for issue in issues:
            issue_label = QLabel(f"  • {issue}")
            issue_label.setStyleSheet("color: #c0a0a0; font-size: 11px;")
            layout.addWidget(issue_label)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tile_id)


class ValidationPanel(QWidget):
    """
    Panel showing validation issues for the atlas.
    Click on an issue to jump to that tile.
    """
    tile_clicked = Signal(str)  # Emits tile_id when an issue is clicked
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._atlas: Optional[Atlas] = None
        self._validation_items: List[ValidationItem] = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header
        header_layout = QHBoxLayout()
        
        header_label = QLabel("VALIDATION")
        header_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #aaa;")
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(24, 24)
        self.refresh_btn.setToolTip("Refresh validation")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-radius: 12px;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Summary
        self.summary_label = QLabel("No atlas loaded")
        self.summary_label.setStyleSheet("color: #888;")
        layout.addWidget(self.summary_label)
        
        # Scroll area for issues
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3a3a3a;
                background-color: #252525;
            }
        """)
        
        self.issues_container = QWidget()
        self.issues_layout = QVBoxLayout(self.issues_container)
        self.issues_layout.setContentsMargins(5, 5, 5, 5)
        self.issues_layout.setSpacing(5)
        self.issues_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.issues_container)
        layout.addWidget(self.scroll_area, 1)
        
        # Status
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet("""
            QFrame {
                background-color: #2a3a2a;
                border: 1px solid #3a4a3a;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_icon = QLabel("✓")
        self.status_icon.setStyleSheet("color: #80c080; font-size: 16px;")
        status_layout.addWidget(self.status_icon)
        
        self.status_text = QLabel("All tiles valid")
        self.status_text.setStyleSheet("color: #a0c0a0;")
        status_layout.addWidget(self.status_text)
        
        status_layout.addStretch()
        
        layout.addWidget(self.status_frame)
    
    def set_atlas(self, atlas: Optional[Atlas]) -> None:
        """Set the atlas to validate."""
        self._atlas = atlas
        self.refresh()
    
    def refresh(self) -> None:
        """Refresh the validation display."""
        # Clear existing items
        for item in self._validation_items:
            item.deleteLater()
        self._validation_items.clear()
        
        if not self._atlas:
            self.summary_label.setText("No atlas loaded")
            self._set_status(True, "No atlas")
            return
        
        # Run validation
        result = validate_atlas(self._atlas)
        
        # Count issues
        error_count = result.error_count
        warning_count = result.warning_count
        
        if error_count == 0 and warning_count == 0:
            self.summary_label.setText("All tiles have complete rules")
            self.summary_label.setStyleSheet("color: #80c080;")
            self._set_status(True, "All tiles valid")
        else:
            parts = []
            if error_count > 0:
                parts.append(f"{error_count} errors")
            if warning_count > 0:
                parts.append(f"{warning_count} warnings")
            self.summary_label.setText(", ".join(parts))
            self.summary_label.setStyleSheet("color: #f0a030;")
            self._set_status(False, f"{error_count + warning_count} issues")
        
        # Show orphan tiles
        for tile_id in result.orphan_tiles:
            item = ValidationItem(tile_id, ["No rules defined (orphan tile)"])
            item.clicked.connect(self._on_item_clicked)
            self._validation_items.append(item)
            self.issues_layout.addWidget(item)
        
        # Show tiles with issues
        for tile_id, tile_result in result.tile_results.items():
            if tile_result.is_valid:
                continue
            if tile_id in result.orphan_tiles:
                continue  # Already shown as orphan
            
            issues = []
            
            for side in tile_result.missing_sides:
                issues.append(f"Missing {side} neighbors")
            
            for side, total in tile_result.incomplete_sides.items():
                issues.append(f"{side}: weights sum to {total:.1f}% (should be 100%)")
            
            if issues:
                item = ValidationItem(tile_id, issues)
                item.clicked.connect(self._on_item_clicked)
                self._validation_items.append(item)
                self.issues_layout.addWidget(item)
    
    def _set_status(self, valid: bool, text: str):
        """Update the status display."""
        if valid:
            self.status_frame.setStyleSheet("""
                QFrame {
                    background-color: #2a3a2a;
                    border: 1px solid #3a4a3a;
                    border-radius: 3px;
                }
            """)
            self.status_icon.setText("✓")
            self.status_icon.setStyleSheet("color: #80c080; font-size: 16px;")
            self.status_text.setStyleSheet("color: #a0c0a0;")
        else:
            self.status_frame.setStyleSheet("""
                QFrame {
                    background-color: #3a352a;
                    border: 1px solid #4a4030;
                    border-radius: 3px;
                }
            """)
            self.status_icon.setText("⚠")
            self.status_icon.setStyleSheet("color: #f0a030; font-size: 16px;")
            self.status_text.setStyleSheet("color: #c0a080;")
        
        self.status_text.setText(text)
    
    def _on_item_clicked(self, tile_id: str):
        """Handle click on a validation item."""
        self.tile_clicked.emit(tile_id)
    
    def get_tiles_with_issues(self) -> List[str]:
        """Get list of tile IDs that have validation issues."""
        if not self._atlas:
            return []
        result = validate_atlas(self._atlas)
        return result.get_tiles_with_issues()

