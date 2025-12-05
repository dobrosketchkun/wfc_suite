"""
Cross preview panel - standalone widget showing center tile with neighbors.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PIL import Image
from typing import Optional, Dict, List

from ..core import SIDES


class CrossPreviewPanel(QWidget):
    """
    Large cross preview showing the center tile with neighbors on each side.
    Uses nearest-neighbor scaling for pixel-perfect display.
    """
    TILE_SIZE = 140  # Big tiles
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
        self._selected_tile_name: str = ""
        
        self._setup_ui()
        
        self._cycle_timer = QTimer(self)
        self._cycle_timer.timeout.connect(self._auto_cycle)
        self._cycle_timer.start(self.CYCLE_INTERVAL)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Title
        self.title_lbl = QLabel("No tile selected")
        self.title_lbl.setStyleSheet("color: #888; font-size: 12px; font-weight: bold;")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_lbl)
        
        layout.addStretch()
        
        # The preview area (custom painted)
        self.preview_widget = CrossPreviewWidget(self)
        layout.addWidget(self.preview_widget, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Hint
        hint = QLabel("Click a side to cycle neighbors")
        hint.setStyleSheet("color: #555; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        
        layout.addStretch()
    
    def set_selected_tile(self, name: str) -> None:
        self._selected_tile_name = name
        if name:
            self.title_lbl.setText(f"Editing: {name}")
            self.title_lbl.setStyleSheet("color: #4a90d9; font-size: 12px; font-weight: bold;")
        else:
            self.title_lbl.setText("No tile selected")
            self.title_lbl.setStyleSheet("color: #888; font-size: 12px; font-weight: bold;")
    
    def set_center(self, image: Optional[Image.Image]) -> None:
        self._center_image = image
        self.preview_widget.set_center(image)
    
    def set_side_images(self, side: str, images: List[Image.Image]) -> None:
        if side in self._side_images:
            self._side_images[side] = images
            self._side_counts[side] = len(images)
            self._side_indices[side] = 0
            self.preview_widget.set_side_images(side, images)
    
    def clear(self) -> None:
        self._center_image = None
        for side in self._side_images:
            self._side_images[side] = []
            self._side_indices[side] = 0
            self._side_counts[side] = 0
        self.preview_widget.clear()
        self.set_selected_tile("")
    
    def _auto_cycle(self):
        changed = False
        for side in SIDES:
            if self._side_counts[side] > 1:
                self._side_indices[side] = (self._side_indices[side] + 1) % self._side_counts[side]
                changed = True
        if changed:
            self.preview_widget.set_indices(self._side_indices)


class CrossPreviewWidget(QWidget):
    """The actual painted cross preview."""
    TILE_SIZE = 140
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._center_image: Optional[Image.Image] = None
        self._side_images: Dict[str, List[Image.Image]] = {
            'top': [], 'right': [], 'bottom': [], 'left': []
        }
        self._side_indices: Dict[str, int] = {
            'top': 0, 'right': 0, 'bottom': 0, 'left': 0
        }
        
        margin = 26
        size = self.TILE_SIZE * 3 + margin * 2
        self.setFixedSize(size, size)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def set_center(self, image: Optional[Image.Image]) -> None:
        self._center_image = image
        self.update()
    
    def set_side_images(self, side: str, images: List[Image.Image]) -> None:
        if side in self._side_images:
            self._side_images[side] = images
            self._side_indices[side] = 0
            self.update()
    
    def set_indices(self, indices: Dict[str, int]) -> None:
        self._side_indices = indices.copy()
        self.update()
    
    def clear(self) -> None:
        self._center_image = None
        for side in self._side_images:
            self._side_images[side] = []
            self._side_indices[side] = 0
        self.update()
    
    def _get_side_at_pos(self, x: int, y: int) -> Optional[str]:
        ts = self.TILE_SIZE
        margin = 26
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
            if side and len(self._side_images.get(side, [])) > 1:
                count = len(self._side_images[side])
                self._side_indices[side] = (self._side_indices[side] + 1) % count
                self.update()
    
    def _pil_to_pixmap(self, image: Image.Image, size: int) -> QPixmap:
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
        margin = 26
        ox, oy = margin, margin
        
        # Checkerboard
        c1 = QColor(20, 20, 20)
        c2 = QColor(30, 30, 30)
        cs = 16
        
        positions = {
            'top': (ox + ts, oy),
            'left': (ox, oy + ts),
            'center': (ox + ts, oy + ts),
            'right': (ox + ts * 2, oy + ts),
            'bottom': (ox + ts, oy + ts * 2)
        }
        
        for name, (x, y) in positions.items():
            for cy in range(0, ts, cs):
                for cx in range(0, ts, cs):
                    color = c1 if ((cx // cs + cy // cs) % 2 == 0) else c2
                    painter.fillRect(x + cx, y + cy, cs, cs, color)
        
        # Center tile
        cx, cy = positions['center']
        if self._center_image:
            pixmap = self._pil_to_pixmap(self._center_image, ts)
            painter.drawPixmap(cx, cy, pixmap)
        else:
            painter.setPen(QColor(50, 50, 50))
            painter.drawRect(cx, cy, ts - 1, ts - 1)
            font = QFont()
            font.setPixelSize(24)
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
                idx = self._side_indices.get(side, 0) % count
                pixmap = self._pil_to_pixmap(images[idx], ts)
                painter.drawPixmap(x, y, pixmap)
            else:
                painter.setPen(QColor(50, 35, 35))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(x + 4, y + 4, ts - 9, ts - 9)
        
        # Grid lines
        painter.setPen(QColor(40, 40, 40))
        for i in range(4):
            painter.drawLine(ox + i * ts, oy, ox + i * ts, oy + ts * 3)
            painter.drawLine(ox, oy + i * ts, ox + ts * 3, oy + i * ts)
        
        # Count labels in margins
        font = QFont()
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(80, 80, 100))
        
        for side, (x, y) in side_pos.items():
            images = self._side_images.get(side, [])
            count = len(images)
            if count > 0:
                idx = self._side_indices.get(side, 0) % count
                text = f"{idx + 1}/{count}" if count > 1 else "1"
                
                if side == 'top':
                    painter.drawText(x, oy - 14, ts, 14, Qt.AlignmentFlag.AlignCenter, text)
                elif side == 'bottom':
                    painter.drawText(x, oy + ts * 3 + 2, ts, 14, Qt.AlignmentFlag.AlignCenter, text)
                elif side == 'left':
                    painter.drawText(2, y, margin - 4, ts, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, text)
                elif side == 'right':
                    painter.drawText(ox + ts * 3 + 2, y, margin - 4, ts, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

