"""
Image utility functions.
"""

from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QTransform
from PySide6.QtCore import Qt


class ImageUtils:
    """Utility class for image operations."""
    
    @staticmethod
    def create_checkerboard(size: int, cell_size: int = 8) -> QPixmap:
        """Create a checkerboard pattern pixmap (for uncollapsed cells)."""
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(200, 200, 200))
        
        painter = QPainter(pixmap)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(170, 170, 170))
        
        for y in range(0, size, cell_size * 2):
            for x in range(0, size, cell_size * 2):
                painter.drawRect(x, y, cell_size, cell_size)
                painter.drawRect(x + cell_size, y + cell_size, cell_size, cell_size)
        
        painter.end()
        return pixmap
    
    @staticmethod
    def create_question_mark(size: int) -> QPixmap:
        """Create a question mark pixmap (for uncollapsed cells)."""
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(240, 240, 240))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw subtle border
        painter.setPen(QColor(200, 200, 200))
        painter.drawRect(0, 0, size - 1, size - 1)
        
        # Draw question mark
        font = painter.font()
        font.setPixelSize(int(size * 0.6))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(180, 180, 180))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "?")
        
        painter.end()
        return pixmap
    
    @staticmethod
    def create_error_pixmap(size: int) -> QPixmap:
        """Create an error/contradiction pixmap."""
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(255, 200, 200))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw X
        painter.setPen(QColor(200, 50, 50))
        margin = int(size * 0.2)
        painter.drawLine(margin, margin, size - margin, size - margin)
        painter.drawLine(size - margin, margin, margin, size - margin)
        
        painter.end()
        return pixmap
    
    @staticmethod
    def add_locked_border(pixmap: QPixmap, border_color: QColor = None) -> QPixmap:
        """Add a colored border to indicate locked cell."""
        if border_color is None:
            border_color = QColor(50, 150, 255)
        
        result = pixmap.copy()
        painter = QPainter(result)
        painter.setPen(border_color)
        painter.setBrush(Qt.NoBrush)
        
        # Draw border
        for i in range(2):
            painter.drawRect(i, i, result.width() - 1 - 2*i, result.height() - 1 - 2*i)
        
        painter.end()
        return result

