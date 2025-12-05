"""
Tile thumbnail widget for displaying tile previews.
"""

from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PIL import Image
from typing import Optional


class TileThumbnail(QWidget):
    """
    A widget that displays a tile thumbnail with optional selection state.
    Supports multi-selection via Ctrl+click and Alt+click for transform-only selection.
    """
    # (tile_id, ctrl_held, alt_held)
    clicked = Signal(str, bool, bool)
    double_clicked = Signal(str)
    right_clicked = Signal(str)
    
    THUMBNAIL_SIZE = 64
    
    def __init__(self, tile_id: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tile_id = tile_id
        self._selected = False
        self._pixmap: Optional[QPixmap] = None
        self._has_warning = False
        
        self.setFixedSize(self.THUMBNAIL_SIZE + 8, self.THUMBNAIL_SIZE + 8)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{tile_id}\n\nCtrl+Click: Multi-select\nAlt+Click: Select for transforms only")
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
    
    def set_image(self, image: Image.Image) -> None:
        """Set the tile image from a PIL Image."""
        # Convert PIL Image to QPixmap
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        data = image.tobytes('raw', 'RGBA')
        qimage = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        
        # Scale to thumbnail size
        self._pixmap = pixmap.scaled(
            self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.update()
    
    def set_pixmap(self, pixmap: QPixmap) -> None:
        """Set the tile image from a QPixmap."""
        self._pixmap = pixmap.scaled(
            self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.update()
    
    def set_selected(self, selected: bool) -> None:
        """Set the selection state."""
        self._selected = selected
        self.update()
    
    def set_warning(self, has_warning: bool) -> None:
        """Set whether to show a warning indicator."""
        self._has_warning = has_warning
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        if self._selected:
            painter.fillRect(self.rect(), QColor(70, 130, 180))  # Steel blue
        else:
            painter.fillRect(self.rect(), QColor(50, 50, 50))
        
        # Draw checkerboard pattern for transparency
        if self._pixmap:
            checker_size = 8
            px = (self.width() - self._pixmap.width()) // 2
            py = (self.height() - self._pixmap.height()) // 2
            
            for y in range(0, self._pixmap.height(), checker_size):
                for x in range(0, self._pixmap.width(), checker_size):
                    if (x // checker_size + y // checker_size) % 2 == 0:
                        painter.fillRect(
                            px + x, py + y, 
                            min(checker_size, self._pixmap.width() - x),
                            min(checker_size, self._pixmap.height() - y),
                            QColor(40, 40, 40)
                        )
                    else:
                        painter.fillRect(
                            px + x, py + y,
                            min(checker_size, self._pixmap.width() - x),
                            min(checker_size, self._pixmap.height() - y),
                            QColor(60, 60, 60)
                        )
            
            # Draw the pixmap
            painter.drawPixmap(px, py, self._pixmap)
        else:
            # No image - draw placeholder
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "?")
        
        # Border
        if self._selected:
            painter.setPen(QPen(QColor(100, 180, 255), 2))
        else:
            painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        
        # Warning indicator
        if self._has_warning:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 180, 0))
            painter.drawEllipse(self.width() - 14, 2, 12, 12)
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(self.width() - 12, 12, "!")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
            alt = event.modifiers() & Qt.KeyboardModifier.AltModifier
            self.clicked.emit(self.tile_id, bool(ctrl), bool(alt))
        elif event.button() == Qt.MouseButton.RightButton:
            self.clicked.emit(self.tile_id, False, False)  # Select first
            self.right_clicked.emit(self.tile_id)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.tile_id)
