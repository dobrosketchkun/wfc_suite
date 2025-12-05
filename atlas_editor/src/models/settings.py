from dataclasses import dataclass


@dataclass
class Settings:
    """
    Editor settings that control auto-propagation behavior.
    """
    auto_propagate_rotations: bool = True    # auto-generate rules for rotated variants
    auto_propagate_mirrors: bool = True      # auto-generate rules for flipped variants
    
    def to_dict(self) -> dict:
        return {
            'auto_propagate_rotations': self.auto_propagate_rotations,
            'auto_propagate_mirrors': self.auto_propagate_mirrors
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Settings':
        return cls(
            auto_propagate_rotations=data.get('auto_propagate_rotations', True),
            auto_propagate_mirrors=data.get('auto_propagate_mirrors', True)
        )

