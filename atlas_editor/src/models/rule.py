from dataclasses import dataclass
from typing import Literal

Side = Literal['top', 'right', 'bottom', 'left']


@dataclass
class AdjacencyRule:
    """
    Represents an adjacency rule: which tile can be placed next to another tile on a specific side.
    Weight is stored as a percentage (0-100). All weights for a given tile+side should sum to 100.
    """
    tile_id: str                      # the tile this rule belongs to
    side: Side                        # which side of the tile
    neighbor_id: str                  # which tile can be adjacent on that side
    weight: float = 100.0             # percentage weight (0-100)
    auto_generated: bool = False      # True if created by auto-propagation
    
    @property
    def key(self) -> tuple:
        """Unique key for this rule (tile_id, side, neighbor_id)."""
        return (self.tile_id, self.side, self.neighbor_id)
    
    def to_dict(self) -> dict:
        return {
            'tile': self.tile_id,
            'side': self.side,
            'neighbor': self.neighbor_id,
            'weight': self.weight,
            'auto': self.auto_generated
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AdjacencyRule':
        return cls(
            tile_id=data['tile'],
            side=data['side'],
            neighbor_id=data['neighbor'],
            weight=data.get('weight', 100.0),
            auto_generated=data.get('auto', False)
        )
    
    def __hash__(self):
        return hash(self.key)
    
    def __eq__(self, other):
        if isinstance(other, AdjacencyRule):
            return self.key == other.key
        return False

