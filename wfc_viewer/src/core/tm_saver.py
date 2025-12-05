"""
Save and load .tm (Tile Map) files.
"""

import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from PySide6.QtGui import QImage
from PySide6.QtCore import QBuffer, QIODevice

from .tile import TileAtlas


@dataclass
class CellData:
    """Data for a single grid cell."""
    x: int
    y: int
    tile_id: Optional[str] = None  # None if uncollapsed
    locked: bool = False  # True if manually placed by user
    possibilities: Set[str] = field(default_factory=set)  # If uncollapsed


@dataclass
class GridState:
    """Complete state of the WFC grid."""
    width: int
    height: int
    source_tr: str = ""  # Original .tr filename
    cells: Dict[tuple, CellData] = field(default_factory=dict)
    
    def get_cell(self, x: int, y: int) -> Optional[CellData]:
        """Get cell at position, or None if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells.get((x, y))
        return None
    
    def set_cell(self, x: int, y: int, tile_id: Optional[str], locked: bool = False):
        """Set a cell's tile."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.cells[(x, y)] = CellData(
                x=x, y=y, tile_id=tile_id, locked=locked
            )
    
    def clear_cell(self, x: int, y: int):
        """Clear a cell (remove tile assignment)."""
        if (x, y) in self.cells:
            cell = self.cells[(x, y)]
            cell.tile_id = None
            cell.locked = False
            cell.possibilities.clear()
    
    def is_complete(self) -> bool:
        """Check if all cells are collapsed."""
        for y in range(self.height):
            for x in range(self.width):
                cell = self.get_cell(x, y)
                if cell is None or cell.tile_id is None:
                    return False
        return True


class TMSaver:
    """Save and load .tm tile map files."""
    
    @staticmethod
    def save(
        filepath: str,
        grid_state: GridState,
        atlas: TileAtlas,
        source_tr_path: Optional[str] = None
    ):
        """
        Save grid state to a .tm file.
        
        Args:
            filepath: Output .tm file path
            grid_state: Current grid state
            atlas: TileAtlas with tile images
            source_tr_path: Original .tr file path (for reference)
        """
        path = Path(filepath)
        
        # Build map.json
        cells_data = []
        uncollapsed_data = []
        
        for y in range(grid_state.height):
            for x in range(grid_state.width):
                cell = grid_state.get_cell(x, y)
                if cell is None:
                    continue
                
                if cell.tile_id is not None:
                    cells_data.append({
                        "x": x,
                        "y": y,
                        "tile_id": cell.tile_id,
                        "locked": cell.locked
                    })
                elif cell.possibilities:
                    uncollapsed_data.append({
                        "x": x,
                        "y": y,
                        "possibilities": list(cell.possibilities)
                    })
        
        map_json = {
            "version": "1.0",
            "source_tr": source_tr_path or grid_state.source_tr,
            "grid": {
                "width": grid_state.width,
                "height": grid_state.height
            },
            "cells": cells_data,
            "uncollapsed": uncollapsed_data
        }
        
        # Build source_atlas.json (copy of atlas metadata)
        atlas_json = {
            "version": atlas.version,
            "settings": atlas.settings,
            "base_tiles": [
                {
                    "id": bt.id,
                    "source": bt.source,
                    "width": bt.width,
                    "height": bt.height
                }
                for bt in atlas.base_tiles.values()
            ],
            "tiles": [
                {
                    "id": tv.id,
                    "base": tv.base_tile_id,
                    "rotation": tv.rotation,
                    "flip_x": tv.flip_x,
                    "flip_y": tv.flip_y,
                    "enabled": tv.enabled
                }
                for tv in atlas.tiles.values()
            ],
            "rules": [
                {
                    "tile": r.tile,
                    "side": r.side,
                    "neighbor": r.neighbor,
                    "weight": r.weight,
                    "auto": r.auto
                }
                for r in atlas.rules
            ]
        }
        
        # Create the ZIP archive
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Write map.json
            zf.writestr('map.json', json.dumps(map_json, indent=2))
            
            # Write source_atlas.json
            zf.writestr('source_atlas.json', json.dumps(atlas_json, indent=2))
            
            # Write tile images
            for base_tile in atlas.base_tiles.values():
                if base_tile.image is not None:
                    # Convert QImage to PNG bytes using QBuffer
                    buffer = QBuffer()
                    buffer.open(QIODevice.WriteOnly)
                    base_tile.image.save(buffer, "PNG")
                    zf.writestr(base_tile.source, buffer.data().data())
    
    @staticmethod
    def load(filepath: str) -> tuple[GridState, TileAtlas]:
        """
        Load a .tm file.
        
        Args:
            filepath: Path to .tm file
            
        Returns:
            Tuple of (GridState, TileAtlas)
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with zipfile.ZipFile(path, 'r') as zf:
            # Read map.json
            map_data = json.loads(zf.read('map.json').decode('utf-8'))
            
            # Read source_atlas.json
            atlas_data = json.loads(zf.read('source_atlas.json').decode('utf-8'))
            
            # Reconstruct atlas
            atlas = TileAtlas()
            atlas.version = atlas_data.get('version', '1.0')
            atlas.settings = atlas_data.get('settings', {})
            
            # Load base tiles
            from .tile import BaseTile, TileVariant, Rule
            
            for bt_data in atlas_data.get('base_tiles', []):
                base_tile = BaseTile(
                    id=bt_data['id'],
                    source=bt_data['source'],
                    width=bt_data.get('width', 0),
                    height=bt_data.get('height', 0)
                )
                
                # Load image from archive
                try:
                    img_data = zf.read(bt_data['source'])
                    image = QImage()
                    if image.loadFromData(img_data):
                        base_tile.image = image
                        base_tile.width = image.width()
                        base_tile.height = image.height()
                except KeyError:
                    pass
                
                atlas.base_tiles[base_tile.id] = base_tile
            
            # Load tile variants
            for tv_data in atlas_data.get('tiles', []):
                # Support both 'base' and 'base_tile_id' field names
                base_id = tv_data.get('base') or tv_data.get('base_tile_id')
                variant = TileVariant(
                    id=tv_data['id'],
                    base_tile_id=base_id,
                    rotation=tv_data.get('rotation', 0),
                    flip_x=tv_data.get('flip_x', False),
                    flip_y=tv_data.get('flip_y', False),
                    enabled=tv_data.get('enabled', True)
                )
                atlas.tiles[variant.id] = variant
            
            # Load rules
            for rule_data in atlas_data.get('rules', []):
                rule = Rule(
                    tile=rule_data['tile'],
                    side=rule_data['side'],
                    neighbor=rule_data['neighbor'],
                    weight=rule_data.get('weight', 100.0),
                    auto=rule_data.get('auto', False)
                )
                atlas.rules.append(rule)
            
            atlas.build_adjacency_lookup()
            
            # Reconstruct grid state
            grid_state = GridState(
                width=map_data['grid']['width'],
                height=map_data['grid']['height'],
                source_tr=map_data.get('source_tr', '')
            )
            
            # Load collapsed cells
            for cell_data in map_data.get('cells', []):
                grid_state.set_cell(
                    x=cell_data['x'],
                    y=cell_data['y'],
                    tile_id=cell_data['tile_id'],
                    locked=cell_data.get('locked', False)
                )
            
            # Load uncollapsed cells
            for cell_data in map_data.get('uncollapsed', []):
                cell = CellData(
                    x=cell_data['x'],
                    y=cell_data['y'],
                    possibilities=set(cell_data.get('possibilities', []))
                )
                grid_state.cells[(cell.x, cell.y)] = cell
        
        return grid_state, atlas

