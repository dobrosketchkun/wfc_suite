"""
Data classes for tiles, variants, and rules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from PySide6.QtGui import QPixmap, QImage, QTransform
from PySide6.QtCore import Qt


@dataclass
class BaseTile:
    """Original imported tile image."""
    id: str
    source: str  # Relative path inside archive (tiles/filename.png)
    width: int
    height: int
    image: Optional[QImage] = None  # Loaded image data


@dataclass
class TileVariant:
    """A tile variant (original or transformed)."""
    id: str
    base_tile_id: str
    rotation: int = 0  # 0, 90, 180, 270
    flip_x: bool = False
    flip_y: bool = False
    enabled: bool = True
    
    # Cached pixmap for rendering
    _pixmap: Optional[QPixmap] = field(default=None, repr=False)
    
    def get_pixmap(self, base_tiles: Dict[str, BaseTile], size: int = 32) -> QPixmap:
        """Get the transformed pixmap for this variant."""
        if self._pixmap is not None and self._pixmap.width() == size:
            return self._pixmap
        
        base = base_tiles.get(self.base_tile_id)
        if base is None or base.image is None:
            # Return placeholder
            pixmap = QPixmap(size, size)
            pixmap.fill()
            return pixmap
        
        # Apply transformations
        image = base.image.copy()
        
        # Apply rotation FIRST (as per atlas_editor convention: turn_r90_fx = rotate, then flip)
        if self.rotation != 0:
            transform = QTransform()
            transform.rotate(self.rotation)
            image = image.transformed(transform)
        
        # Apply flips AFTER rotation (positional args: horizontally, vertically)
        if self.flip_x:
            image = image.mirrored(True, False)
        if self.flip_y:
            image = image.mirrored(False, True)
        
        # Scale to requested size (FastTransformation = nearest neighbor for pixel art)
        pixmap = QPixmap.fromImage(image).scaled(
            size, size,
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )
        
        self._pixmap = pixmap
        return pixmap
    
    def clear_cache(self):
        """Clear the cached pixmap."""
        self._pixmap = None


@dataclass
class Rule:
    """Adjacency rule defining which tiles can be neighbors."""
    tile: str  # Source tile ID
    side: str  # 'top', 'right', 'bottom', 'left'
    neighbor: str  # Neighbor tile ID
    weight: float = 100.0  # Probability weight
    auto: bool = False  # Whether auto-generated from propagation
    
    @property
    def opposite_side(self) -> str:
        """Get the opposite side."""
        opposites = {
            'top': 'bottom',
            'bottom': 'top',
            'left': 'right',
            'right': 'left'
        }
        return opposites[self.side]


class TileAtlas:
    """Container for all tiles and rules from a .tr file."""
    
    def __init__(self):
        self.version: str = "1.0"
        self.settings: Dict = {
            "auto_propagate_rotations": True,
            "auto_propagate_mirrors": True
        }
        self.base_tiles: Dict[str, BaseTile] = {}
        self.tiles: Dict[str, TileVariant] = {}
        self.rules: List[Rule] = []
        
        # Precomputed adjacency lookup
        # {tile_id: {side: {neighbor_id: weight}}} - what each tile allows on each side
        self._adjacency: Dict[str, Dict[str, Dict[str, float]]] = {}
        
        # Reverse lookup: {side: {neighbor_id: set of tiles that allow this neighbor on this side}}
        self._reverse_adjacency: Dict[str, Dict[str, Set[str]]] = {}
    
    def build_adjacency_lookup(self):
        """Build fast lookup tables for adjacency rules."""
        self._adjacency.clear()
        self._reverse_adjacency = {
            'top': {}, 'right': {}, 'bottom': {}, 'left': {}
        }
        
        for rule in self.rules:
            # Forward lookup: tile -> side -> allowed neighbors
            if rule.tile not in self._adjacency:
                self._adjacency[rule.tile] = {
                    'top': {}, 'right': {}, 'bottom': {}, 'left': {}
                }
            self._adjacency[rule.tile][rule.side][rule.neighbor] = rule.weight
            
            # Reverse lookup: side -> neighbor -> tiles that allow this neighbor
            if rule.neighbor not in self._reverse_adjacency[rule.side]:
                self._reverse_adjacency[rule.side][rule.neighbor] = set()
            self._reverse_adjacency[rule.side][rule.neighbor].add(rule.tile)
    
    def get_valid_neighbors(self, tile_id: str, side: str) -> Dict[str, float]:
        """Get valid neighbor tiles for a given tile and side."""
        if tile_id not in self._adjacency:
            return {}
        return self._adjacency[tile_id].get(side, {})
    
    def get_tiles_allowing_neighbor(self, side: str, neighbor_id: str) -> Set[str]:
        """Get tiles that allow a specific neighbor on a specific side."""
        return self._reverse_adjacency.get(side, {}).get(neighbor_id, set())
    
    def can_be_neighbor(self, tile_id: str, side: str, neighbor_id: str) -> bool:
        """Check if neighbor_id can be placed on the given side of tile_id."""
        neighbors = self.get_valid_neighbors(tile_id, side)
        return neighbor_id in neighbors
    
    def get_all_enabled_tiles(self) -> List[TileVariant]:
        """Get all enabled tile variants."""
        return [t for t in self.tiles.values() if t.enabled]
    
    def get_enabled_tile_ids(self) -> Set[str]:
        """Get IDs of all enabled tiles."""
        return {t.id for t in self.tiles.values() if t.enabled}
    
    def get_valid_tiles_for_position(
        self, 
        neighbors: Dict[str, Optional[str]]
    ) -> Set[str]:
        """
        Get tiles valid for a position given its neighbors.
        
        Args:
            neighbors: Dict mapping side ('top', 'right', 'bottom', 'left') 
                      to tile_id or None if no neighbor/uncollapsed
        
        Returns:
            Set of valid tile IDs
        """
        enabled = self.get_enabled_tile_ids()
        
        if not any(neighbors.values()):
            # No constraints, all enabled tiles are valid
            return enabled
        
        valid = enabled.copy()
        
        for side, neighbor_id in neighbors.items():
            if neighbor_id is None:
                continue
            
            # We need tiles that can have neighbor_id on their `side`
            # Which means neighbor_id must allow us on its opposite side
            opposite = {
                'top': 'bottom', 'bottom': 'top',
                'left': 'right', 'right': 'left'
            }[side]
            
            # Get what tiles neighbor_id allows on its opposite side
            allowed_by_neighbor = set(self.get_valid_neighbors(neighbor_id, opposite).keys())
            valid &= allowed_by_neighbor
        
        return valid

