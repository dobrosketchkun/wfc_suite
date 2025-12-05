from dataclasses import dataclass
from typing import Optional


@dataclass
class Tile:
    """
    Represents a tile variant, which may be the original or a transformed version.
    Stores transform information (rotation, flips) rather than creating new image files.
    """
    id: str                           # e.g., "grass" or "grass_r90_fx"
    base_tile_id: str                 # reference to the BaseTile
    rotation: int = 0                 # 0, 90, 180, or 270 degrees clockwise
    flip_x: bool = False              # horizontal flip (mirror)
    flip_y: bool = False              # vertical flip
    enabled: bool = True              # whether to include in WFC export
    
    @property
    def is_original(self) -> bool:
        """Returns True if this is the original (no transforms applied)."""
        return self.rotation == 0 and not self.flip_x and not self.flip_y
    
    @property
    def transform_suffix(self) -> str:
        """Returns the suffix string representing the transform (e.g., '_r90_fx')."""
        parts = []
        if self.rotation != 0:
            parts.append(f'r{self.rotation}')
        if self.flip_x:
            parts.append('fx')
        if self.flip_y:
            parts.append('fy')
        return '_' + '_'.join(parts) if parts else ''
    
    @classmethod
    def create_id(cls, base_id: str, rotation: int = 0, flip_x: bool = False, flip_y: bool = False) -> str:
        """Generate a tile ID from base ID and transform parameters."""
        parts = [base_id]
        if rotation != 0:
            parts.append(f'r{rotation}')
        if flip_x:
            parts.append('fx')
        if flip_y:
            parts.append('fy')
        return '_'.join(parts)
    
    @classmethod
    def from_base(cls, base_tile_id: str, rotation: int = 0, flip_x: bool = False, flip_y: bool = False) -> 'Tile':
        """Create a Tile from a base tile ID and transform parameters."""
        tile_id = cls.create_id(base_tile_id, rotation, flip_x, flip_y)
        return cls(
            id=tile_id,
            base_tile_id=base_tile_id,
            rotation=rotation,
            flip_x=flip_x,
            flip_y=flip_y
        )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'base': self.base_tile_id,
            'rotation': self.rotation,
            'flip_x': self.flip_x,
            'flip_y': self.flip_y,
            'enabled': self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Tile':
        return cls(
            id=data['id'],
            base_tile_id=data['base'],
            rotation=data.get('rotation', 0),
            flip_x=data.get('flip_x', False),
            flip_y=data.get('flip_y', False),
            enabled=data.get('enabled', True)
        )
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Tile):
            return self.id == other.id
        return False

