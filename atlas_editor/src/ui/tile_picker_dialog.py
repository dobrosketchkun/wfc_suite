"""
Dialog for picking a tile from the atlas.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QWidget, QPushButton, QLineEdit, QLabel, QDialogButtonBox
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor, QPainter, QPen
from PIL import Image
from typing import Optional, Callable, Set

from ..models import Atlas, Tile
from .widgets import TileThumbnail


class TilePickerDialog(QDialog):
    """
    Modal dialog for selecting tiles from the atlas.
    Supports multi-selection with Ctrl+Click.
    Remembers its position between uses.
    """
    
    # Class-level settings for position persistence
    _settings = QSettings("WFC", "AtlasEditor")
    
    def __init__(
        self, 
        atlas: Atlas, 
        get_image_fn: Callable[[str], Optional[Image.Image]],
        exclude_ids: Optional[Set[str]] = None,
        already_neighbor_ids: Optional[Set[str]] = None,
        side_name: Optional[str] = None,
        tile_name: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.atlas = atlas
        self.get_image_fn = get_image_fn
        self.exclude_ids = exclude_ids or set()
        self.already_neighbor_ids = already_neighbor_ids or set()
        self.side_name = side_name
        self.tile_name = tile_name
        self.selected_tile_ids: Set[str] = set()  # Multi-selection support
        self._thumbnails: dict[str, TileThumbnail] = {}
        
        self._setup_ui()
        self._populate_tiles()
        self._restore_geometry()
    
    def _setup_ui(self):
        # Build title with context info
        title = "Select Neighbor Tile"
        if self.side_name:
            title = f"Select {self.side_name.upper()} Neighbor"
        if self.tile_name:
            title += f" for {self.tile_name}"
        self.setWindowTitle(title)
        
        self.setMinimumSize(450, 550)
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Tile count label (shows how many tiles are available)
        total_tiles = len(self.atlas.tiles) if self.atlas else 0
        available = total_tiles - len(self.exclude_ids)
        self.count_label = QLabel(f"Available: {available} / {total_tiles} tiles")
        self.count_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.count_label)
        
        # Hint for multi-selection
        hint_label = QLabel("Ctrl+Click to select multiple tiles")
        hint_label.setStyleSheet("color: #666; font-size: 9px; font-style: italic;")
        layout.addWidget(hint_label)
        
        # Filter
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter tiles...")
        self.filter_input.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_input)
        
        # Scroll area for tiles
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3a3a3a;
                background-color: #252525;
            }
        """)
        
        self.tiles_container = QWidget()
        self.tiles_layout = QGridLayout(self.tiles_container)
        self.tiles_layout.setSpacing(5)
        self.tiles_layout.setContentsMargins(5, 5, 5, 5)
        self.tiles_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll_area.setWidget(self.tiles_container)
        layout.addWidget(self.scroll_area, 1)
        
        # Selection label
        self.selection_label = QLabel("No tile selected")
        self.selection_label.setStyleSheet("color: #888;")
        layout.addWidget(self.selection_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: #e0e0e0;
                border: 1px solid #5a5a5a;
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        layout.addWidget(button_box)
    
    def _restore_geometry(self):
        """Restore dialog position from settings."""
        geometry = self._settings.value("TilePickerDialog/geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def _save_geometry(self):
        """Save dialog position to settings."""
        self._settings.setValue("TilePickerDialog/geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        """Save geometry when closing."""
        self._save_geometry()
        super().closeEvent(event)
    
    def accept(self):
        """Save geometry when accepting."""
        self._save_geometry()
        super().accept()
    
    def reject(self):
        """Save geometry when rejecting."""
        self._save_geometry()
        super().reject()
    
    def _populate_tiles(self, filter_text: str = "") -> None:
        """Populate the tile grid."""
        # Clear existing
        while self.tiles_layout.count():
            item = self.tiles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._thumbnails.clear()
        
        filter_text = filter_text.lower()
        row = 0
        col = 0
        max_cols = 5
        shown_count = 0
        
        # DEBUG: Print tile count
        print(f"[TilePickerDialog] Atlas has {len(self.atlas.tiles)} tiles, exclude_ids={len(self.exclude_ids)}")
        
        # Iterate through all tiles in atlas
        for tile in self.atlas.tiles:
            # Skip excluded tiles (already added for THIS side)
            if tile.id in self.exclude_ids:
                print(f"[TilePickerDialog] Excluding tile: {tile.id}")
                continue
            
            # Apply text filter
            if filter_text and filter_text not in tile.id.lower():
                continue
            
            # Just use regular TileThumbnail (no special highlighting)
            thumbnail = TileThumbnail(tile.id)
            thumbnail.clicked.connect(self._on_tile_clicked)
            thumbnail.double_clicked.connect(self._on_tile_double_clicked)
            
            # Get image
            if self.get_image_fn:
                image = self.get_image_fn(tile.id)
                if image:
                    thumbnail.set_image(image)
            
            if tile.id in self.selected_tile_ids:
                thumbnail.set_selected(True)
            
            self._thumbnails[tile.id] = thumbnail
            self.tiles_layout.addWidget(thumbnail, row, col)
            shown_count += 1
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Update count label
        total_tiles = len(self.atlas.tiles) if self.atlas else 0
        self.count_label.setText(f"Showing: {shown_count} / {total_tiles} tiles")
    
    def _on_filter_changed(self, text: str) -> None:
        """Handle filter change."""
        self._populate_tiles(text)
    
    def _on_tile_clicked(self, tile_id: str, ctrl: bool = False, alt: bool = False) -> None:
        """Handle tile selection. Ctrl+Click for multi-select."""
        if ctrl:
            # Toggle selection
            if tile_id in self.selected_tile_ids:
                self.selected_tile_ids.remove(tile_id)
                if tile_id in self._thumbnails:
                    self._thumbnails[tile_id].set_selected(False)
            else:
                self.selected_tile_ids.add(tile_id)
                if tile_id in self._thumbnails:
                    self._thumbnails[tile_id].set_selected(True)
        else:
            # Single selection - clear previous and select new
            for tid in self.selected_tile_ids:
                if tid in self._thumbnails:
                    self._thumbnails[tid].set_selected(False)
            self.selected_tile_ids.clear()
            self.selected_tile_ids.add(tile_id)
            if tile_id in self._thumbnails:
                self._thumbnails[tile_id].set_selected(True)
        
        # Update selection label
        count = len(self.selected_tile_ids)
        if count == 0:
            self.selection_label.setText("No tile selected")
            self.selection_label.setStyleSheet("color: #888;")
        elif count == 1:
            self.selection_label.setText(f"Selected: {list(self.selected_tile_ids)[0]}")
            self.selection_label.setStyleSheet("color: #4a90d9;")
        else:
            self.selection_label.setText(f"Selected: {count} tiles")
            self.selection_label.setStyleSheet("color: #4a90d9;")
    
    def _on_tile_double_clicked(self, tile_id: str) -> None:
        """Handle tile double-click (select and confirm)."""
        self._on_tile_clicked(tile_id)
        self.accept()
    
    def get_selected_tiles(self) -> Set[str]:
        """Get all selected tile IDs."""
        return self.selected_tile_ids
    
    def get_selected_tile(self) -> Optional[str]:
        """Get the first selected tile ID (for backwards compatibility)."""
        if self.selected_tile_ids:
            return list(self.selected_tile_ids)[0]
        return None
