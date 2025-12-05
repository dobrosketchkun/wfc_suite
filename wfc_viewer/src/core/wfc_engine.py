"""
Wave Function Collapse engine with pause/resume support.
"""

import random
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal, QTimer

from .tile import TileAtlas


class EngineState(Enum):
    """WFC engine states."""
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()
    CONTRADICTION = auto()


@dataclass
class CellState:
    """State of a single cell in the WFC grid."""
    x: int
    y: int
    possibilities: Set[str] = field(default_factory=set)
    collapsed_tile: Optional[str] = None
    locked: bool = False  # User-placed tile, cannot be changed
    
    @property
    def is_collapsed(self) -> bool:
        return self.collapsed_tile is not None
    
    @property
    def entropy(self) -> int:
        """Number of remaining possibilities (lower = more constrained)."""
        if self.is_collapsed:
            return 0
        return len(self.possibilities)


class WFCEngine(QObject):
    """
    Wave Function Collapse algorithm with real-time visualization support.
    
    Signals:
        cell_collapsed(x, y, tile_id): Emitted when a cell is collapsed
        cell_updated(x, y): Emitted when cell possibilities change
        contradiction_found(x, y): Emitted when a contradiction is found
        state_changed(state): Emitted when engine state changes
        finished(success): Emitted when collapse completes
        progress_updated(collapsed, total): Emitted on progress change
    """
    
    cell_collapsed = Signal(int, int, str)
    cell_updated = Signal(int, int)
    contradiction_found = Signal(int, int)
    state_changed = Signal(EngineState)
    finished = Signal(bool)
    progress_updated = Signal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.atlas: Optional[TileAtlas] = None
        self.width: int = 0
        self.height: int = 0
        self.cells: Dict[Tuple[int, int], CellState] = {}
        
        self._state = EngineState.IDLE
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._step_delay = 50  # milliseconds between steps
        
        self._collapsed_count = 0
        self._total_cells = 0
    
    @property
    def state(self) -> EngineState:
        return self._state
    
    @state.setter
    def state(self, value: EngineState):
        if self._state != value:
            self._state = value
            self.state_changed.emit(value)
    
    def set_speed(self, delay_ms: int):
        """Set delay between collapse steps in milliseconds."""
        self._step_delay = max(1, delay_ms)
        if self._timer.isActive():
            self._timer.setInterval(self._step_delay)
    
    def initialize(self, atlas: TileAtlas, width: int, height: int):
        """
        Initialize the grid with all possibilities.
        
        Args:
            atlas: TileAtlas with tiles and rules
            width: Grid width
            height: Grid height
        """
        self.atlas = atlas
        self.width = width
        self.height = height
        self.cells.clear()
        self._collapsed_count = 0
        self._total_cells = width * height
        
        # Get all enabled tile IDs
        enabled_tiles = atlas.get_enabled_tile_ids()
        
        # Initialize each cell with all possibilities
        for y in range(height):
            for x in range(width):
                self.cells[(x, y)] = CellState(
                    x=x, y=y,
                    possibilities=enabled_tiles.copy()
                )
        
        self.state = EngineState.IDLE
        self.progress_updated.emit(0, self._total_cells)
    
    def lock_cell(self, x: int, y: int, tile_id: str):
        """
        Lock a cell to a specific tile (user-placed constraint).
        This also propagates constraints to neighbors.
        """
        if (x, y) not in self.cells:
            return
        
        cell = self.cells[(x, y)]
        cell.collapsed_tile = tile_id
        cell.locked = True
        cell.possibilities = {tile_id}
        
        if not cell.is_collapsed or cell.collapsed_tile != tile_id:
            self._collapsed_count += 1
        
        self.cell_collapsed.emit(x, y, tile_id)
        self.progress_updated.emit(self._collapsed_count, self._total_cells)
        
        # Propagate constraints
        self._propagate(x, y)
    
    def unlock_cell(self, x: int, y: int):
        """Unlock a cell and restore its possibilities."""
        if (x, y) not in self.cells:
            return
        
        cell = self.cells[(x, y)]
        was_collapsed = cell.is_collapsed
        was_contradiction = len(cell.possibilities) == 0
        
        cell.locked = False
        cell.collapsed_tile = None
        cell.possibilities = self.atlas.get_enabled_tile_ids().copy()
        
        if was_collapsed:
            self._collapsed_count -= 1
        
        # If grid was finished or had contradiction, re-enable controls
        if was_collapsed or was_contradiction:
            if self.state in (EngineState.FINISHED, EngineState.CONTRADICTION):
                self.state = EngineState.IDLE
        
        self.cell_updated.emit(x, y)
        self.progress_updated.emit(self._collapsed_count, self._total_cells)
        
        # Re-propagate from neighbors
        for nx, ny in self._get_neighbors(x, y):
            if self.cells[(nx, ny)].is_collapsed:
                self._propagate(nx, ny)
    
    def start(self):
        """Start or resume the collapse process."""
        if self.state in (EngineState.FINISHED, EngineState.CONTRADICTION):
            return
        
        self.state = EngineState.RUNNING
        self._timer.start(self._step_delay)
    
    def pause(self):
        """Pause the collapse process."""
        if self.state == EngineState.RUNNING:
            self._timer.stop()
            self.state = EngineState.PAUSED
    
    def step(self):
        """Perform a single collapse step (manual stepping)."""
        if self.state in (EngineState.FINISHED, EngineState.CONTRADICTION):
            return
        
        self._step()
    
    def reset(self):
        """Reset the grid, keeping locked cells."""
        if self.atlas is None:
            return
        
        self._timer.stop()
        
        # Save locked cells
        locked_cells = {
            pos: cell.collapsed_tile 
            for pos, cell in self.cells.items() 
            if cell.locked
        }
        
        # Re-initialize
        self.initialize(self.atlas, self.width, self.height)
        
        # Restore locked cells
        for (x, y), tile_id in locked_cells.items():
            self.lock_cell(x, y, tile_id)
    
    def clear_all(self):
        """Clear all cells including locked ones."""
        if self.atlas is None:
            return
        
        self._timer.stop()
        self.initialize(self.atlas, self.width, self.height)
    
    def _step(self):
        """Perform one collapse iteration."""
        # Find cell with lowest entropy (most constrained)
        min_entropy = float('inf')
        candidates = []
        
        for pos, cell in self.cells.items():
            if cell.is_collapsed:
                continue
            
            entropy = cell.entropy
            if entropy == 0:
                # Contradiction - no possibilities left
                self._timer.stop()
                self.state = EngineState.CONTRADICTION
                self.contradiction_found.emit(pos[0], pos[1])
                self.finished.emit(False)
                return
            
            if entropy < min_entropy:
                min_entropy = entropy
                candidates = [pos]
            elif entropy == min_entropy:
                candidates.append(pos)
        
        if not candidates:
            # All cells collapsed - success!
            self._timer.stop()
            self.state = EngineState.FINISHED
            self.finished.emit(True)
            return
        
        # Pick random cell among lowest entropy candidates
        x, y = random.choice(candidates)
        cell = self.cells[(x, y)]
        
        # Recalculate valid possibilities RIGHT NOW based on all collapsed neighbors
        # This ensures we have the most up-to-date constraints
        valid_now = self.atlas.get_enabled_tile_ids().copy()
        for nx, ny, side in self._get_neighbors_with_sides(x, y):
            neighbor = self.cells.get((nx, ny))
            if neighbor is None or not neighbor.is_collapsed:
                continue
            neighbor_tile = neighbor.collapsed_tile
            opposite = {'left': 'right', 'right': 'left',
                       'top': 'bottom', 'bottom': 'top'}[side]
            # Neighbor must allow me
            neighbor_allows = set(self.atlas.get_valid_neighbors(neighbor_tile, opposite).keys())
            # I must allow neighbor  
            i_allow = self.atlas.get_tiles_allowing_neighbor(side, neighbor_tile)
            
            valid_now &= neighbor_allows
            valid_now &= i_allow
        
        if not valid_now:
            # Contradiction
            self._timer.stop()
            self.state = EngineState.CONTRADICTION
            self.contradiction_found.emit(x, y)
            self.finished.emit(False)
            return
        
        # Pick from the verified valid set
        tile_id = random.choice(list(valid_now))
        
        # Collapse the cell
        cell.collapsed_tile = tile_id
        cell.possibilities = {tile_id}
        self._collapsed_count += 1
        
        self.cell_collapsed.emit(x, y, tile_id)
        self.progress_updated.emit(self._collapsed_count, self._total_cells)
        
        # Propagate constraints
        self._propagate(x, y)
    
    def _weighted_choice(self, possibilities: Set[str]) -> str:
        """Choose a tile weighted by rule weights."""
        if not possibilities:
            raise ValueError("No possibilities to choose from")
        
        # For simplicity, use uniform random for now
        # Could be enhanced to use actual weights from rules
        return random.choice(list(possibilities))
    
    def _propagate(self, start_x: int, start_y: int):
        """Propagate constraints from collapsed cells."""
        from collections import deque
        queue = deque()
        
        # Add all uncollapsed neighbors of the starting cell
        for nx, ny, _ in self._get_neighbors_with_sides(start_x, start_y):
            neighbor = self.cells.get((nx, ny))
            if neighbor and not neighbor.is_collapsed:
                queue.append((nx, ny))
        
        while queue:
            x, y = queue.popleft()
            
            cell = self.cells.get((x, y))
            if cell is None or cell.is_collapsed:
                continue
            
            # Recalculate ALL valid possibilities for this cell
            # based on ALL its collapsed neighbors
            valid = self.atlas.get_enabled_tile_ids().copy()
            
            for nx, ny, side in self._get_neighbors_with_sides(x, y):
                neighbor = self.cells.get((nx, ny))
                if neighbor is None or not neighbor.is_collapsed:
                    continue
                
                neighbor_tile = neighbor.collapsed_tile
                opposite = {'left': 'right', 'right': 'left',
                           'top': 'bottom', 'bottom': 'top'}[side]
                
                # 1. Neighbor must allow me: I'm on neighbor's 'opposite' side
                neighbor_allows = set(self.atlas.get_valid_neighbors(neighbor_tile, opposite).keys())
                
                # 2. I must allow neighbor: neighbor is on my 'side'
                i_allow = self.atlas.get_tiles_allowing_neighbor(side, neighbor_tile)
                
                # Both constraints
                valid &= neighbor_allows
                valid &= i_allow
            
            # Update if changed
            if valid != cell.possibilities:
                old_possibilities = cell.possibilities
                cell.possibilities = valid
                self.cell_updated.emit(x, y)
                
                if len(valid) == 0:
                    # Contradiction
                    return
                elif len(valid) == 1:
                    # Auto-collapse
                    tile = next(iter(valid))
                    cell.collapsed_tile = tile
                    self._collapsed_count += 1
                    self.cell_collapsed.emit(x, y, tile)
                    self.progress_updated.emit(self._collapsed_count, self._total_cells)
                    # Add neighbors of newly collapsed cell
                    for nnx, nny, _ in self._get_neighbors_with_sides(x, y):
                        nn = self.cells.get((nnx, nny))
                        if nn and not nn.is_collapsed:
                            queue.append((nnx, nny))
                else:
                    # Possibilities reduced, propagate to neighbors
                    for nnx, nny, _ in self._get_neighbors_with_sides(x, y):
                        nn = self.cells.get((nnx, nny))
                        if nn and not nn.is_collapsed:
                            queue.append((nnx, nny))
    
    def _get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get valid neighbor positions."""
        neighbors = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                neighbors.append((nx, ny))
        return neighbors
    
    def _get_neighbors_with_sides(
        self, x: int, y: int
    ) -> List[Tuple[int, int, str]]:
        """Get valid neighbors with the side they're on."""
        neighbors = []
        directions = [
            (-1, 0, 'left'),
            (1, 0, 'right'),
            (0, -1, 'top'),
            (0, 1, 'bottom')
        ]
        for dx, dy, side in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                neighbors.append((nx, ny, side))
        return neighbors
    
    def get_cell(self, x: int, y: int) -> Optional[CellState]:
        """Get cell state at position."""
        return self.cells.get((x, y))
    
    def get_valid_tiles_for_cell(self, x: int, y: int) -> Set[str]:
        """
        Get tiles valid for a cell given its collapsed neighbors.
        
        For each collapsed neighbor N on side S, tile T is valid if:
        - N allows T on opposite(S): rule {tile: N, side: opposite(S), neighbor: T}
        - T allows N on S: rule {tile: T, side: S, neighbor: N}
        """
        if self.atlas is None:
            return set()
        
        valid = self.atlas.get_enabled_tile_ids().copy()
        
        for nx, ny, side in self._get_neighbors_with_sides(x, y):
            neighbor = self.cells.get((nx, ny))
            if neighbor is None or not neighbor.is_collapsed:
                continue
            
            neighbor_tile = neighbor.collapsed_tile
            opposite = {'left': 'right', 'right': 'left',
                       'top': 'bottom', 'bottom': 'top'}[side]
            
            # 1. Neighbor must allow me
            neighbor_allows = set(self.atlas.get_valid_neighbors(neighbor_tile, opposite).keys())
            
            # 2. I must allow neighbor
            i_allow = self.atlas.get_tiles_allowing_neighbor(side, neighbor_tile)
            
            valid &= neighbor_allows
            valid &= i_allow
        
        return valid
    
    def validate_grid(self) -> List[str]:
        """
        Validate all adjacencies in the current grid.
        Returns list of error messages (empty if valid).
        """
        errors = []
        
        if self.atlas is None:
            return ["No atlas loaded"]
        
        for y in range(self.height):
            for x in range(self.width):
                cell = self.get_cell(x, y)
                if cell is None or not cell.is_collapsed:
                    continue
                
                tile_id = cell.collapsed_tile
                
                # Check each neighbor
                for nx, ny, side in self._get_neighbors_with_sides(x, y):
                    neighbor = self.get_cell(nx, ny)
                    if neighbor is None or not neighbor.is_collapsed:
                        continue
                    
                    neighbor_tile = neighbor.collapsed_tile
                    
                    # Check if this tile allows the neighbor on this side
                    allowed = self.atlas.get_valid_neighbors(tile_id, side)
                    if neighbor_tile not in allowed:
                        errors.append(
                            f"({x},{y}) '{tile_id}' does not allow '{neighbor_tile}' on {side}"
                        )
        
        return errors

