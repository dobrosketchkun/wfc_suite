"""
Export grid to PNG image.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtCore import Qt

from ..core.tile import TileAtlas
from ..core.wfc_engine import WFCEngine


def export_grid_to_png(
    filepath: str,
    engine: WFCEngine,
    atlas: TileAtlas,
    tile_size: Optional[int] = None,
    background_color: QColor = None
) -> bool:
    """
    Export the current grid state to a PNG image.
    
    Args:
        filepath: Output PNG file path
        engine: WFCEngine with current grid state
        atlas: TileAtlas with tile images
        tile_size: Size of each tile in output (None = use original size)
        background_color: Background color for uncollapsed cells
        
    Returns:
        True if export successful, False otherwise
    """
    if engine.width == 0 or engine.height == 0:
        return False
    
    if background_color is None:
        background_color = QColor(200, 200, 200)
    
    # Determine tile size
    if tile_size is None:
        # Use first base tile's size
        for base_tile in atlas.base_tiles.values():
            tile_size = max(base_tile.width, base_tile.height)
            break
        if tile_size is None:
            tile_size = 32
    
    # Create output image
    img_width = engine.width * tile_size
    img_height = engine.height * tile_size
    
    image = QImage(img_width, img_height, QImage.Format_ARGB32)
    image.fill(background_color)
    
    painter = QPainter(image)
    # No smooth transform for pixel art - use nearest neighbor
    painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
    
    # Draw each cell
    for y in range(engine.height):
        for x in range(engine.width):
            cell = engine.get_cell(x, y)
            if cell is None or not cell.is_collapsed:
                continue
            
            tile_id = cell.collapsed_tile
            variant = atlas.tiles.get(tile_id)
            if variant is None:
                continue
            
            pixmap = variant.get_pixmap(atlas.base_tiles, tile_size)
            painter.drawPixmap(x * tile_size, y * tile_size, pixmap)
    
    painter.end()
    
    # Save to file
    path = Path(filepath)
    return image.save(str(path), "PNG")

