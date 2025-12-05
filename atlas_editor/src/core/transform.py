"""
Transform utilities for handling tile rotations and flips.
Provides mappings for how sides change under different transforms.
"""

from typing import Literal
from dataclasses import dataclass

Side = Literal['top', 'right', 'bottom', 'left']
SIDES: list[Side] = ['top', 'right', 'bottom', 'left']


@dataclass(frozen=True)
class Transform:
    """Represents a tile transformation (rotation + flips)."""
    rotation: int = 0        # 0, 90, 180, 270 (clockwise)
    flip_x: bool = False     # horizontal flip
    flip_y: bool = False     # vertical flip
    
    @property
    def suffix(self) -> str:
        """Generate ID suffix for this transform."""
        parts = []
        if self.rotation != 0:
            parts.append(f'r{self.rotation}')
        if self.flip_x:
            parts.append('fx')
        if self.flip_y:
            parts.append('fy')
        return '_'.join(parts) if parts else ''
    
    @property
    def is_identity(self) -> bool:
        """Returns True if this is the identity transform (no change)."""
        return self.rotation == 0 and not self.flip_x and not self.flip_y
    
    def apply_to_side(self, side: Side) -> Side:
        """
        Compute which side a given side maps to after this transform.
        Rotation is applied first, then flips.
        """
        result = side
        
        # Apply rotation (clockwise)
        if self.rotation != 0:
            result = rotate_side(result, self.rotation)
        
        # Apply flips
        if self.flip_x:
            result = flip_side(result, 'x')
        if self.flip_y:
            result = flip_side(result, 'y')
        
        return result
    
    def inverse_side(self, side: Side) -> Side:
        """
        Compute which original side maps TO the given side after this transform.
        This is the inverse of apply_to_side.
        """
        # We need to find which original side becomes 'side' after transform
        for original_side in SIDES:
            if self.apply_to_side(original_side) == side:
                return original_side
        raise ValueError(f"Could not find inverse for side {side}")
    
    def inverse(self) -> 'Transform':
        """
        Compute the inverse transform.
        If T transforms A to B, then T.inverse() transforms B to A.
        Result is normalized to use only flip_x.
        """
        # Transform applies: rotate, then flip_x, then flip_y
        # Inverse must undo in reverse order: undo flip_y, undo flip_x, undo rotate
        # Flips are self-inverse
        # Rotation inverse: inv(r) = (360 - r) % 360
        
        # But we need to express this as a new Transform(rotation, flip_x, flip_y)
        # which applies in the ORDER: rotate, flip_x, flip_y
        
        # The inverse of (rotate r, flip_x fx, flip_y fy) is:
        # (flip_y fy, flip_x fx, rotate -r)  (operations in reverse order)
        
        # We need to commute flips past rotation to get standard form
        # flip_y then rotate(-r) = rotate(-r) then flip_?
        # flip_x then rotate(-r) = rotate(-r) then flip_?
        
        # When rotating, flip_x and flip_y swap axes:
        # flip_x followed by rotate(90) = rotate(90) followed by flip_y
        # flip_y followed by rotate(90) = rotate(90) followed by flip_x
        # flip_x followed by rotate(180) = rotate(180) followed by flip_x
        # flip_y followed by rotate(180) = rotate(180) followed by flip_y
        # flip_x followed by rotate(270) = rotate(270) followed by flip_y
        # flip_y followed by rotate(270) = rotate(270) followed by flip_x
        
        inv_rotation = (360 - self.rotation) % 360
        
        # We have: flip_y, flip_x, rotate(inv_rotation)
        # Need to move flips after rotation
        
        # Move flip_x past rotate(inv_rotation):
        new_flip_x = self.flip_x
        new_flip_y = self.flip_y
        
        if inv_rotation == 90 or inv_rotation == 270:
            # flip_x <-> flip_y when passing through 90 or 270 rotation
            new_flip_x, new_flip_y = self.flip_y, self.flip_x
        # For 0 and 180, flips stay the same
        
        return Transform(inv_rotation, new_flip_x, new_flip_y).normalize()
    
    def compose(self, other: 'Transform') -> 'Transform':
        """
        Compose two transforms: self followed by other.
        Returns a new Transform representing the combined effect.
        Result is normalized to use only flip_x (no flip_y).
        """
        # Apply self first: (r1, fx1, fy1), then other: (r2, fx2, fy2)
        # Result: rotate(r1), flip_x(fx1), flip_y(fy1), rotate(r2), flip_x(fx2), flip_y(fy2)
        
        # We need to combine into: rotate(r), flip_x(fx), flip_y(fy)
        
        # Step 1: Move flip_y(fy1) past rotate(r2)
        # Step 2: Move flip_x(fx1) past rotate(r2)
        # Then combine the flips and rotations
        
        # When flip passes through rotation:
        # - flip_x past r90 -> flip_y
        # - flip_y past r90 -> flip_x
        # - flip_x past r180 -> flip_x
        # - flip_y past r180 -> flip_y
        # - flip_x past r270 -> flip_y
        # - flip_y past r270 -> flip_x
        
        # Transform the flips through other's rotation
        fx1, fy1 = self.flip_x, self.flip_y
        
        if other.rotation == 90 or other.rotation == 270:
            # Swap flip axes
            fx1, fy1 = fy1, fx1
        
        # Now we have: rotate(r1), rotate(r2), flip_x(fx1), flip_y(fy1), flip_x(fx2), flip_y(fy2)
        # Combine rotations: r = (r1 + r2) % 360
        # Combine flips: flip_x = fx1 XOR fx2, flip_y = fy1 XOR fy2
        
        new_rotation = (self.rotation + other.rotation) % 360
        new_flip_x = fx1 != other.flip_x  # XOR
        new_flip_y = fy1 != other.flip_y  # XOR
        
        # Normalize: convert flip_y to r180 + flip_x
        # This ensures we only use variants that exist (_fx, not _fy)
        return Transform(new_rotation, new_flip_x, new_flip_y).normalize()
    
    def normalize(self) -> 'Transform':
        """
        Normalize transform to canonical form using only flip_x (no flip_y).
        
        Equivalences:
        - flip_y alone = r180 + flip_x
        - flip_x + flip_y = r180
        
        This ensures we match tile variants that only have _fx versions.
        """
        rotation = self.rotation
        flip_x = self.flip_x
        flip_y = self.flip_y
        
        if flip_y:
            if flip_x:
                # flip_x + flip_y = r180
                rotation = (rotation + 180) % 360
                flip_x = False
                flip_y = False
            else:
                # flip_y alone = r180 + flip_x
                rotation = (rotation + 180) % 360
                flip_x = True
                flip_y = False
        
        return Transform(rotation, flip_x, flip_y)


# --- Side Rotation ---

# Mapping: after rotating N degrees clockwise, which side does each original side become?
_ROTATION_MAP = {
    0: {'top': 'top', 'right': 'right', 'bottom': 'bottom', 'left': 'left'},
    90: {'top': 'right', 'right': 'bottom', 'bottom': 'left', 'left': 'top'},
    180: {'top': 'bottom', 'right': 'left', 'bottom': 'top', 'left': 'right'},
    270: {'top': 'left', 'right': 'top', 'bottom': 'right', 'left': 'bottom'},
}


def rotate_side(side: Side, degrees: int) -> Side:
    """Get the new position of a side after clockwise rotation."""
    degrees = degrees % 360
    if degrees not in _ROTATION_MAP:
        raise ValueError(f"Invalid rotation: {degrees}. Must be 0, 90, 180, or 270.")
    return _ROTATION_MAP[degrees][side]


# --- Side Flipping ---

_FLIP_X_MAP = {'top': 'top', 'right': 'left', 'bottom': 'bottom', 'left': 'right'}
_FLIP_Y_MAP = {'top': 'bottom', 'right': 'right', 'bottom': 'top', 'left': 'left'}


def flip_side(side: Side, axis: Literal['x', 'y']) -> Side:
    """Get the new position of a side after flipping on an axis."""
    if axis == 'x':
        return _FLIP_X_MAP[side]
    elif axis == 'y':
        return _FLIP_Y_MAP[side]
    raise ValueError(f"Invalid axis: {axis}. Must be 'x' or 'y'.")


def get_opposite_side(side: Side) -> Side:
    """Get the opposite side (top<->bottom, left<->right)."""
    opposites = {'top': 'bottom', 'bottom': 'top', 'left': 'right', 'right': 'left'}
    return opposites[side]


# --- All Transform Combinations ---

def get_all_transforms(include_identity: bool = True) -> list[Transform]:
    """
    Get all unique transform combinations.
    Note: Some combinations are equivalent (e.g., r180 = fx + fy).
    This returns all 8 combinations for simplicity.
    """
    transforms = []
    for rotation in [0, 90, 180, 270]:
        for flip_x in [False, True]:
            for flip_y in [False, True]:
                t = Transform(rotation, flip_x, flip_y)
                if include_identity or not t.is_identity:
                    transforms.append(t)
    return transforms


def get_rotation_transforms() -> list[Transform]:
    """Get just the rotation transforms (no flips)."""
    return [Transform(r, False, False) for r in [0, 90, 180, 270]]


def get_flip_transforms() -> list[Transform]:
    """Get just the flip transforms (no rotation)."""
    return [
        Transform(0, False, False),  # identity
        Transform(0, True, False),   # flip x
        Transform(0, False, True),   # flip y
        Transform(0, True, True),    # flip both
    ]
