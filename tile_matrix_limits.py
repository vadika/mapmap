"""
Tile Matrix Limits

Predefined tile matrix limits extracted from WMTS GetCapabilities for the
LKS_LVM coordinate system. Used for bounds checking to prevent invalid tile requests.
"""

# Tile matrix limits for the Topo10DTM layer in LKS_LVM coordinate system
LKS_LVM_TILE_LIMITS = {
    7: {"min_col": 19, "max_col": 99, "min_row": 1, "max_row": 48},
    8: {"min_col": 28, "max_col": 133, "min_row": 2, "max_row": 64},
    9: {"min_col": 42, "max_col": 199, "min_row": 3, "max_row": 97},
    10: {"min_col": 56, "max_col": 266, "min_row": 4, "max_row": 129},
    11: {"min_col": 84, "max_col": 399, "min_row": 6, "max_row": 194},
    12: {"min_col": 168, "max_col": 799, "min_row": 13, "max_row": 389},
    13: {"min_col": 420, "max_col": 2000, "min_row": 32, "max_row": 974},
    14: {"min_col": 841, "max_col": 4000, "min_row": 65, "max_row": 1948},
    15: {"min_col": 1121, "max_col": 5333, "min_row": 87, "max_row": 2598},
    16: {"min_col": 1682, "max_col": 8000, "min_row": 131, "max_row": 3897},
    17: {"min_col": 3364, "max_col": 16000, "min_row": 262, "max_row": 7795},
    18: {"min_col": 8410, "max_col": 40000, "min_row": 655, "max_row": 19488},
}


def is_tile_in_bounds(zoom_level: int, tile_col: int, tile_row: int) -> bool:
    """Check if a tile coordinate is within the valid bounds for LKS_LVM"""
    if zoom_level not in LKS_LVM_TILE_LIMITS:
        return False
    
    limits = LKS_LVM_TILE_LIMITS[zoom_level]
    return (limits["min_col"] <= tile_col <= limits["max_col"] and 
            limits["min_row"] <= tile_row <= limits["max_row"])


def get_tile_limits(zoom_level: int) -> dict:
    """Get the tile limits for a specific zoom level"""
    return LKS_LVM_TILE_LIMITS.get(zoom_level, {})