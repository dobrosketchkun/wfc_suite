from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BaseTile:
    """
    Represents an original imported tile image.
    Does not include transforms - those are stored in Tile objects.
    """
    id: str                           # unique identifier (usually filename without extension)
    source_path: str                  # relative path to image file
    width: int = 0                    # image width in pixels
    height: int = 0                   # image height in pixels
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'source': self.source_path,
            'width': self.width,
            'height': self.height
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BaseTile':
        return cls(
            id=data['id'],
            source_path=data['source'],
            width=data.get('width', 0),
            height=data.get('height', 0)
        )
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, BaseTile):
            return self.id == other.id
        return False

