"""
Rule editor panel - 2-column layout within the rule editor area:
Left: Large cross preview
Right: Side sections for adding neighbors
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QSizePolicy, QMessageBox,
    QMenu, QComboBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PIL import Image
from typing import Optional, Dict, List

from ..models import Atlas, Tile, AdjacencyRule
from ..core import SIDES, get_opposite_side
from .widgets import TileThumbnail, PercentageSpinBox, CollapsibleSection
from .tile_picker_dialog import TilePickerDialog


class CrossPreview(QWidget):
    """
    Large visual preview showing the center tile with neighbors on each side.
    Uses nearest-neighbor scaling for pixel-perfect display.
    """
    TILE_SIZE = 128  # Big tiles
    CYCLE_INTERVAL = 1500
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._center_image: Optional[Image.Image] = None
        self._side_images: Dict[str, List[Image.Image]] = {
            'top': [], 'right': [], 'bottom': [], 'left': []
        }
        self._side_indices: Dict[str, int] = {
            'top': 0, 'right': 0, 'bottom': 0, 'left': 0
        }
        self._side_counts: Dict[str, int] = {
            'top': 0, 'right': 0, 'bottom': 0, 'left': 0
        }
        
        # Size: 3 tiles + margin for labels
        margin = 24
        size = self.TILE_SIZE * 3 + margin * 2
        self.setMinimumSize(size, size)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click on a side to cycle through neighbors")
        
        self._cycle_timer = QTimer(self)
        self._cycle_timer.timeout.connect(self._auto_cycle)
        self._cycle_timer.start(self.CYCLE_INTERVAL)
    
    def set_center(self, image: Optional[Image.Image]) -> None:
        self._center_image = image
        self.update()
    
    def set_side_images(self, side: str, images: List[Image.Image]) -> None:
        if side in self._side_images:
            self._side_images[side] = images
            self._side_counts[side] = len(images)
            self._side_indices[side] = 0
            self.update()
    
    def clear(self) -> None:
        self._center_image = None
        for side in self._side_images:
            self._side_images[side] = []
            self._side_indices[side] = 0
            self._side_counts[side] = 0
        self.update()
    
    def _auto_cycle(self):
        changed = False
        for side in SIDES:
            if self._side_counts[side] > 1:
                self._side_indices[side] = (self._side_indices[side] + 1) % self._side_counts[side]
                changed = True
        if changed:
            self.update()
    
    def _get_side_at_pos(self, x: int, y: int) -> Optional[str]:
        ts = self.TILE_SIZE
        margin = 24
        ox, oy = margin, margin
        
        if ox + ts <= x < ox + ts * 2 and oy <= y < oy + ts:
            return 'top'
        if ox <= x < ox + ts and oy + ts <= y < oy + ts * 2:
            return 'left'
        if ox + ts * 2 <= x < ox + ts * 3 and oy + ts <= y < oy + ts * 2:
            return 'right'
        if ox + ts <= x < ox + ts * 2 and oy + ts * 2 <= y < oy + ts * 3:
            return 'bottom'
        return None
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            side = self._get_side_at_pos(int(event.position().x()), int(event.position().y()))
            if side and self._side_counts[side] > 1:
                self._side_indices[side] = (self._side_indices[side] + 1) % self._side_counts[side]
                self.update()
    
    def _pil_to_pixmap(self, image: Image.Image, size: int) -> QPixmap:
        """Convert PIL Image to QPixmap with NEAREST neighbor (pixel-perfect)."""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        image = image.resize((size, size), Image.Resampling.NEAREST)
        data = image.tobytes('raw', 'RGBA')
        qimage = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        
        ts = self.TILE_SIZE
        margin = 24
        ox, oy = margin, margin
        
        # Checkerboard background
        checker1 = QColor(22, 22, 22)
        checker2 = QColor(32, 32, 32)
        checker_size = 16
        
        positions = {
            'top': (ox + ts, oy),
            'left': (ox, oy + ts),
            'center': (ox + ts, oy + ts),
            'right': (ox + ts * 2, oy + ts),
            'bottom': (ox + ts, oy + ts * 2)
        }
        
        for name, (x, y) in positions.items():
            for cy in range(0, ts, checker_size):
                for cx in range(0, ts, checker_size):
                    color = checker1 if ((cx // checker_size + cy // checker_size) % 2 == 0) else checker2
                    painter.fillRect(x + cx, y + cy, checker_size, checker_size, color)
        
        # Center tile
        cx, cy = positions['center']
        if self._center_image:
            pixmap = self._pil_to_pixmap(self._center_image, ts)
            painter.drawPixmap(cx, cy, pixmap)
        else:
            painter.setPen(QColor(50, 50, 50))
            painter.drawRect(cx, cy, ts - 1, ts - 1)
            font = QFont()
            font.setPixelSize(20)
            painter.setFont(font)
            painter.drawText(cx, cy, ts, ts, Qt.AlignmentFlag.AlignCenter, "?")
        
        # Side tiles
        side_pos = {
            'top': (ox + ts, oy),
            'right': (ox + ts * 2, oy + ts),
            'bottom': (ox + ts, oy + ts * 2),
            'left': (ox, oy + ts)
        }
        
        for side, (x, y) in side_pos.items():
            images = self._side_images.get(side, [])
            count = len(images)
            
            if count > 0:
                idx = self._side_indices[side] % count
                pixmap = self._pil_to_pixmap(images[idx], ts)
                painter.drawPixmap(x, y, pixmap)
            else:
                painter.setPen(QColor(50, 35, 35))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(x + 4, y + 4, ts - 9, ts - 9)
        
        # Grid lines
        painter.setPen(QColor(45, 45, 45))
        for i in range(4):
            painter.drawLine(ox + i * ts, oy, ox + i * ts, oy + ts * 3)
            painter.drawLine(ox, oy + i * ts, ox + ts * 3, oy + i * ts)
        
        # Count labels in margins
        font = QFont()
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(90, 90, 110))
        
        label_pos = {
            'top': (ox + ts + ts // 2, 16),
            'bottom': (ox + ts + ts // 2, oy + ts * 3 + 16),
            'left': (10, oy + ts + ts // 2),
            'right': (ox + ts * 3 + 6, oy + ts + ts // 2)
        }
        
        for side, (lx, ly) in label_pos.items():
            count = self._side_counts.get(side, 0)
            if count > 0:
                idx = self._side_indices[side] % count
                text = f"{idx + 1}/{count}" if count > 1 else "1"
                if side in ['top', 'bottom']:
                    painter.drawText(lx - 25, ly - 6, 50, 14, Qt.AlignmentFlag.AlignCenter, text)
                else:
                    painter.drawText(lx - 5, ly - 6, 40, 14, Qt.AlignmentFlag.AlignLeft if side == 'right' else Qt.AlignmentFlag.AlignRight, text)


class NeighborRow(QWidget):
    """Row for a neighbor with thumbnail, variant selector, weight, remove."""
    weight_changed = Signal(str, float)
    remove_requested = Signal(str)
    variant_changed = Signal(str, str)
    
    def __init__(self, neighbor_id: str, weight: float, image: Optional[Image.Image],
                 auto_generated: bool = False, available_variants: Optional[List[str]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.neighbor_id = neighbor_id
        self.available_variants = available_variants or []
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(6)
        
        # Thumbnail
        self.thumbnail = TileThumbnail(neighbor_id)
        self.thumbnail.THUMBNAIL_SIZE = 36
        self.thumbnail.setFixedSize(42, 42)
        if image:
            self.thumbnail.set_image(image)
        layout.addWidget(self.thumbnail)
        
        # Variant selector or name
        if len(self.available_variants) > 1:
            self.variant_combo = QComboBox()
            self.variant_combo.setStyleSheet("""
                QComboBox {
                    background-color: #383838;
                    color: #ddd;
                    border: 1px solid #4a4a4a;
                    border-radius: 3px;
                    padding: 3px 6px;
                    font-size: 11px;
                    min-width: 90px;
                }
                QComboBox:hover { border-color: #5a5a5a; }
                QComboBox::drop-down { border: none; width: 18px; }
                QComboBox QAbstractItemView {
                    background-color: #383838;
                    color: #ddd;
                    selection-background-color: #4a90d9;
                }
            """)
            for v in self.available_variants:
                self.variant_combo.addItem(self._variant_display(v), v)
            idx = self.variant_combo.findData(neighbor_id)
            if idx >= 0:
                self.variant_combo.setCurrentIndex(idx)
            self.variant_combo.currentIndexChanged.connect(self._on_variant_changed)
            layout.addWidget(self.variant_combo, 1)
        else:
            name_lbl = QLabel(neighbor_id)
            name_lbl.setStyleSheet("color: #ccc; font-size: 11px;")
            name_lbl.setWordWrap(True)
            layout.addWidget(name_lbl, 1)
        
        if auto_generated:
            auto_lbl = QLabel("⚡")
            auto_lbl.setToolTip("Auto-generated rule")
            auto_lbl.setStyleSheet("color: #777;")
            layout.addWidget(auto_lbl)
        
        # Weight
        self.weight_spin = PercentageSpinBox()
        self.weight_spin.setValue(weight)
        self.weight_spin.valueChanged.connect(lambda v: self.weight_changed.emit(self.neighbor_id, v))
        layout.addWidget(self.weight_spin)
        
        # Remove button
        rm_btn = QPushButton("×")
        rm_btn.setFixedSize(22, 22)
        rm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a3535;
                color: #caa;
                border: none;
                border-radius: 11px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5a4545; }
        """)
        rm_btn.clicked.connect(lambda: self.remove_requested.emit(self.neighbor_id))
        layout.addWidget(rm_btn)
    
    def _variant_display(self, vid: str) -> str:
        parts = vid.split('_')
        if len(parts) == 1:
            return "Original"
        transforms = []
        for p in parts[1:]:
            if p.startswith('r'):
                transforms.append(f"↻{p[1:]}°")
            elif p == 'fx':
                transforms.append("↔")
            elif p == 'fy':
                transforms.append("↕")
        return " ".join(transforms) if transforms else vid
    
    def _on_variant_changed(self, index: int):
        if hasattr(self, 'variant_combo'):
            new_id = self.variant_combo.itemData(index)
            if new_id and new_id != self.neighbor_id:
                old_id = self.neighbor_id
                self.neighbor_id = new_id
                self.variant_changed.emit(old_id, new_id)


class SideSection(QFrame):
    """Section for editing neighbors on one side of a tile."""
    rule_changed = Signal()
    neighbors_updated = Signal(str, list)
    
    def __init__(self, side: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.side = side
        self._atlas: Optional[Atlas] = None
        self._tile_id: Optional[str] = None
        self._get_image_fn = None
        self._rows: Dict[str, NeighborRow] = {}
        
        self.setStyleSheet("""
            SideSection {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Header
        header = QHBoxLayout()
        side_lbl = QLabel(f"{side.upper()}")
        side_lbl.setStyleSheet("font-weight: bold; color: #999; font-size: 12px;")
        header.addWidget(side_lbl)
        header.addStretch()
        
        self.total_lbl = QLabel("0%")
        self.total_lbl.setStyleSheet("color: #777; font-size: 11px;")
        header.addWidget(self.total_lbl)
        
        self.warn_lbl = QLabel("⚠")
        self.warn_lbl.setStyleSheet("color: #e0a030; font-size: 12px;")
        self.warn_lbl.hide()
        header.addWidget(self.warn_lbl)
        
        layout.addLayout(header)
        
        # Neighbors
        self.neighbors_widget = QWidget()
        self.neighbors_layout = QVBoxLayout(self.neighbors_widget)
        self.neighbors_layout.setContentsMargins(0, 0, 0, 0)
        self.neighbors_layout.setSpacing(2)
        layout.addWidget(self.neighbors_widget)
        
        # Add button
        self.add_btn = QPushButton("+ Add Neighbor")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a3a2a;
                color: #8ab08a;
                border: 1px dashed #3a4a3a;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #3a4a3a; color: #a0c0a0; }
        """)
        self.add_btn.clicked.connect(self._on_add)
        layout.addWidget(self.add_btn)
    
    def set_context(self, atlas: Optional[Atlas], tile_id: Optional[str], get_image_fn):
        self._atlas = atlas
        self._tile_id = tile_id
        self._get_image_fn = get_image_fn
        self._refresh()
    
    def _get_variants(self, tile_id: str) -> List[str]:
        if not self._atlas:
            return [tile_id]
        tile = self._atlas.get_tile(tile_id)
        if not tile:
            return [tile_id]
        return [t.id for t in self._atlas.get_tiles_for_base(tile.base_tile_id)]
    
    def _refresh(self):
        for r in self._rows.values():
            r.deleteLater()
        self._rows.clear()
        
        if not self._atlas or not self._tile_id:
            self.total_lbl.setText("0%")
            self.warn_lbl.hide()
            self.neighbors_updated.emit(self.side, [])
            return
        
        rules = self._atlas.get_rules_for_tile(self._tile_id, self.side)
        total = 0.0
        neighbor_ids = []
        
        for rule in rules:
            neighbor_ids.append(rule.neighbor_id)
            img = self._get_image_fn(rule.neighbor_id) if self._get_image_fn else None
            variants = self._get_variants(rule.neighbor_id)
            
            row = NeighborRow(rule.neighbor_id, rule.weight, img, rule.auto_generated, variants)
            row.weight_changed.connect(self._on_weight_changed)
            row.remove_requested.connect(self._on_remove)
            row.variant_changed.connect(self._on_variant_changed)
            
            self._rows[rule.neighbor_id] = row
            self.neighbors_layout.addWidget(row)
            total += rule.weight
        
        self.total_lbl.setText(f"{total:.0f}%")
        
        if rules and abs(total - 100.0) > 0.1:
            self.warn_lbl.show()
            self.warn_lbl.setToolTip(f"Total: {total:.1f}% (should be 100%)")
            self.total_lbl.setStyleSheet("color: #e0a030; font-size: 11px;")
        elif not rules:
            self.warn_lbl.show()
            self.warn_lbl.setToolTip("No neighbors defined")
            self.total_lbl.setStyleSheet("color: #c06060; font-size: 11px;")
        else:
            self.warn_lbl.hide()
            self.total_lbl.setStyleSheet("color: #70a070; font-size: 11px;")
        
        self.neighbors_updated.emit(self.side, neighbor_ids)
    
    def _on_add(self):
        if not self._atlas or not self._tile_id:
            return
        
        existing_bases = set()
        for r in self._atlas.get_rules_for_tile(self._tile_id, self.side):
            t = self._atlas.get_tile(r.neighbor_id)
            if t:
                existing_bases.add(t.base_tile_id)
        
        exclude = set()
        for bid in existing_bases:
            for t in self._atlas.get_tiles_for_base(bid):
                exclude.add(t.id)
        
        dialog = TilePickerDialog(self._atlas, self._get_image_fn, exclude, self.window())
        if dialog.exec() and dialog.selected_tile_id:
            self._atlas.add_rule(self._tile_id, self.side, dialog.selected_tile_id, 100.0, False)
            self._refresh()
            self.rule_changed.emit()
    
    def _on_weight_changed(self, neighbor_id: str, weight: float):
        if not self._atlas or not self._tile_id:
            return
        rule = self._atlas.get_rule(self._tile_id, self.side, neighbor_id)
        if rule:
            rule.weight = weight
            self._atlas.modified = True
            self._update_total()
            self.rule_changed.emit()
    
    def _on_remove(self, neighbor_id: str):
        if not self._atlas or not self._tile_id:
            return
        self._atlas.remove_rule(self._tile_id, self.side, neighbor_id)
        self._refresh()
        self.rule_changed.emit()
    
    def _on_variant_changed(self, old_id: str, new_id: str):
        if not self._atlas or not self._tile_id:
            return
        
        old_rule = self._atlas.get_rule(self._tile_id, self.side, old_id)
        if not old_rule:
            return
        
        if not self._atlas.get_tile(new_id):
            tile = self._atlas.get_tile(old_id)
            if tile:
                parts = new_id.split('_')
                base_id = parts[0]
                rotation, flip_x, flip_y = 0, False, False
                for p in parts[1:]:
                    if p.startswith('r'):
                        rotation = int(p[1:])
                    elif p == 'fx':
                        flip_x = True
                    elif p == 'fy':
                        flip_y = True
                self._atlas.add_tile_variant(base_id, rotation, flip_x, flip_y)
        
        weight, auto = old_rule.weight, old_rule.auto_generated
        self._atlas.remove_rule(self._tile_id, self.side, old_id)
        self._atlas.add_rule(self._tile_id, self.side, new_id, weight, auto)
        self._refresh()
        self.rule_changed.emit()
    
    def _update_total(self):
        if not self._atlas or not self._tile_id:
            return
        rules = self._atlas.get_rules_for_tile(self._tile_id, self.side)
        total = sum(r.weight for r in rules)
        self.total_lbl.setText(f"{total:.0f}%")
        
        if abs(total - 100.0) > 0.1:
            self.warn_lbl.show()
            self.total_lbl.setStyleSheet("color: #e0a030; font-size: 11px;")
        else:
            self.warn_lbl.hide()
            self.total_lbl.setStyleSheet("color: #70a070; font-size: 11px;")


class RuleEditor(QWidget):
    """
    Rule editor with 2-column internal layout:
    Left: Large cross preview (center column of main window)
    Right: Side sections for adding neighbors (right column of main window)
    """
    rules_changed = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._atlas: Optional[Atlas] = None
        self._selected_tile_id: Optional[str] = None
        self._get_image_fn = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)
        
        # LEFT SIDE: Cross preview
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        # Selected tile label
        self.selected_lbl = QLabel("No tile selected")
        self.selected_lbl.setStyleSheet("color: #888; font-size: 12px; font-weight: bold;")
        self.selected_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.selected_lbl)
        
        left_layout.addStretch()
        
        # Cross preview
        self.cross_preview = CrossPreview()
        preview_h = QHBoxLayout()
        preview_h.addStretch()
        preview_h.addWidget(self.cross_preview)
        preview_h.addStretch()
        left_layout.addLayout(preview_h)
        
        hint = QLabel("Click a side to cycle neighbors")
        hint.setStyleSheet("color: #555; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(hint)
        
        left_layout.addStretch()
        
        main_layout.addWidget(left_widget, 1)
        
        # RIGHT SIDE: Rule editing controls
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        # Header
        header = QLabel("ADJACENCY RULES")
        header.setStyleSheet("font-weight: bold; font-size: 11px; color: #888;")
        right_layout.addWidget(header)
        
        # Scroll area for side sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        sides_widget = QWidget()
        sides_layout = QVBoxLayout(sides_widget)
        sides_layout.setContentsMargins(0, 0, 0, 0)
        sides_layout.setSpacing(6)
        
        self.side_sections: Dict[str, SideSection] = {}
        for side in SIDES:
            section = SideSection(side)
            section.rule_changed.connect(self._on_rule_changed)
            section.neighbors_updated.connect(self._on_neighbors_updated)
            self.side_sections[side] = section
            sides_layout.addWidget(section)
        
        sides_layout.addStretch()
        scroll.setWidget(sides_widget)
        right_layout.addWidget(scroll, 1)
        
        # Normalize button
        self.normalize_btn = QPushButton("Normalize All Weights to 100%")
        self.normalize_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a4a;
                color: #a0a0c0;
                border: 1px solid #4a4a5a;
                border-radius: 3px;
                padding: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #4a4a5a; }
        """)
        self.normalize_btn.clicked.connect(self._on_normalize)
        right_layout.addWidget(self.normalize_btn)
        
        right_widget.setMinimumWidth(280)
        main_layout.addWidget(right_widget, 1)
    
    def set_atlas(self, atlas: Optional[Atlas]) -> None:
        self._atlas = atlas
        self._selected_tile_id = None
        self._update_ui()
    
    def set_image_getter(self, fn) -> None:
        self._get_image_fn = fn
    
    def set_selected_tile(self, tile_id: Optional[str]) -> None:
        self._selected_tile_id = tile_id
        self._update_ui()
    
    def _update_ui(self):
        if not self._atlas or not self._selected_tile_id:
            self.selected_lbl.setText("No tile selected")
            self.selected_lbl.setStyleSheet("color: #888; font-size: 12px; font-weight: bold;")
            self.cross_preview.clear()
            for section in self.side_sections.values():
                section.set_context(None, None, None)
            return
        
        tile = self._atlas.get_tile(self._selected_tile_id)
        if not tile:
            self.selected_lbl.setText("Tile not found")
            return
        
        self.selected_lbl.setText(f"Editing: {tile.id}")
        self.selected_lbl.setStyleSheet("color: #4a90d9; font-size: 12px; font-weight: bold;")
        
        if self._get_image_fn:
            img = self._get_image_fn(tile.id)
            self.cross_preview.set_center(img)
        
        for side, section in self.side_sections.items():
            section.set_context(self._atlas, tile.id, self._get_image_fn)
    
    def _on_neighbors_updated(self, side: str, neighbor_ids: List[str]):
        images = []
        if self._get_image_fn:
            for nid in neighbor_ids:
                img = self._get_image_fn(nid)
                if img:
                    images.append(img)
        self.cross_preview.set_side_images(side, images)
    
    def _on_rule_changed(self):
        self.rules_changed.emit()
    
    def _on_normalize(self):
        if not self._atlas or not self._selected_tile_id:
            return
        
        from ..core.validation import normalize_side_weights
        for side in SIDES:
            normalize_side_weights(self._atlas, self._selected_tile_id, side)
        
        self._update_ui()
        self.rules_changed.emit()
    
    def refresh(self):
        self._update_ui()
