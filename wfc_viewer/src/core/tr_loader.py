"""
Load and parse .tr (Tile Rules) files.
"""

import json
import zipfile
from pathlib import Path
from typing import Optional
from io import BytesIO

from PySide6.QtGui import QImage

from .tile import TileAtlas, BaseTile, TileVariant, Rule


class TRLoader:
    """Loader for .tr tile rules archives."""
    
    @staticmethod
    def load(filepath: str) -> TileAtlas:
        """
        Load a .tr file and return a TileAtlas.
        
        Args:
            filepath: Path to the .tr file
            
        Returns:
            TileAtlas with all tiles, variants, and rules loaded
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        atlas = TileAtlas()
        
        with zipfile.ZipFile(path, 'r') as zf:
            # Read atlas.json
            try:
                atlas_data = json.loads(zf.read('atlas.json').decode('utf-8'))
            except KeyError:
                raise ValueError("Invalid .tr file: missing atlas.json")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid atlas.json: {e}")
            
            # Parse metadata
            atlas.version = atlas_data.get('version', '1.0')
            atlas.settings = atlas_data.get('settings', {})
            
            # Load base tiles
            for bt_data in atlas_data.get('base_tiles', []):
                base_tile = BaseTile(
                    id=bt_data['id'],
                    source=bt_data['source'],
                    width=bt_data.get('width', 0),
                    height=bt_data.get('height', 0)
                )
                
                # Load the image
                try:
                    img_data = zf.read(bt_data['source'])
                    image = QImage()
                    if image.loadFromData(img_data):
                        base_tile.image = image
                        base_tile.width = image.width()
                        base_tile.height = image.height()
                except KeyError:
                    pass  # Image not found in archive
                
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
        
        # Build adjacency lookup for fast queries
        atlas.build_adjacency_lookup()
        
        return atlas
    
    @staticmethod
    def extract_atlas_json(filepath: str) -> dict:
        """
        Extract just the atlas.json data without loading images.
        Useful for quick inspection.
        """
        with zipfile.ZipFile(filepath, 'r') as zf:
            return json.loads(zf.read('atlas.json').decode('utf-8'))

