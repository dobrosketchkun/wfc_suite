# .tr File Format Specification

## Overview

The `.tr` (Tiles Rules) format is a self-contained archive for Wave Function Collapse (WFC) tile atlases. It bundles tile images with their adjacency rules in a single portable file.

## File Structure

A `.tr` file is a **ZIP archive** with the following structure:

```
archive.tr (ZIP)
├── atlas.json          # Atlas metadata, tiles, and rules
└── tiles/              # Folder containing tile images
    ├── tile1.png
    ├── tile2.png
    └── ...
```

## atlas.json Schema

```json
{
  "version": "1.0",
  "settings": {
    "auto_propagate_rotations": true,
    "auto_propagate_mirrors": true
  },
  "base_tiles": [
    {
      "id": "grass",
      "source": "tiles/grass.png",
      "width": 16,
      "height": 16
    }
  ],
  "tiles": [
    {
      "id": "grass",
      "base_tile_id": "grass",
      "rotation": 0,
      "flip_x": false,
      "flip_y": false,
      "enabled": true
    },
    {
      "id": "grass_r90",
      "base_tile_id": "grass",
      "rotation": 90,
      "flip_x": false,
      "flip_y": false,
      "enabled": true
    }
  ],
  "rules": [
    {
      "tile": "grass",
      "side": "right",
      "neighbor": "grass_r90",
      "weight": 100.0,
      "auto": false
    }
  ]
}
```

## Field Descriptions

### base_tiles
Original imported images. Each entry has:
- `id`: Unique identifier (typically filename without extension)
- `source`: **Relative path** inside the archive (always `tiles/<filename>`)
- `width`, `height`: Image dimensions in pixels

### tiles
Tile variants (original + rotations/flips). Each entry has:
- `id`: Unique identifier (e.g., `grass`, `grass_r90`, `grass_fx`)
- `base_tile_id`: Reference to the base_tile this variant derives from
- `rotation`: Clockwise rotation in degrees (0, 90, 180, 270)
- `flip_x`: Horizontal flip (boolean)
- `flip_y`: Vertical flip (boolean)
- `enabled`: Whether tile is active for WFC generation

### rules
Adjacency rules defining which tiles can be neighbors. Each entry has:
- `tile`: Source tile ID
- `side`: Which side of the source tile (`top`, `right`, `bottom`, `left`)
- `neighbor`: Tile ID that can be placed adjacent on that side
- `weight`: Probability weight (0-100, higher = more likely)
- `auto`: Whether rule was auto-generated from propagation

## Tile ID Naming Convention

Variant IDs follow this pattern:
- Original: `{base_id}` (e.g., `grass`)
- Rotated: `{base_id}_r{degrees}` (e.g., `grass_r90`, `grass_r180`)
- Flipped X: `{base_id}_fx` (e.g., `grass_fx`)
- Flipped Y: `{base_id}_fy` (e.g., `grass_fy`)
- Combined: `{base_id}_r{degrees}_fx` (e.g., `grass_r90_fx`)

## Notes

- All image paths are **relative to the archive root**
- Images are stored in the `tiles/` folder
- The format is fully self-contained and portable
- Supported image formats: PNG (recommended), JPG, GIF

