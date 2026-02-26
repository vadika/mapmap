"""
Coordinate System Configurations

Defines coordinate system configurations for various projection systems including
LKS_LVM (Latvia), WebMercatorQuad, and other EPSG systems. Provides both dynamic
WMTS-based configurations and static fallback configurations.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from pyproj import CRS
import asyncio


@dataclass
class CoordinateSystemConfig:
    name: str
    description: str
    bounds: Tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    tile_matrix_prefix: str
    min_zoom: int = 0
    max_zoom: int = 20
    # Dynamic parameters from WMTS
    wmts_url: Optional[str] = None
    tile_matrix_set_id: Optional[str] = None
    layer_id: Optional[str] = None
    # Static fallback parameters (will be overridden by WMTS data)
    epsg: Optional[int] = None
    origin: Optional[Tuple[float, float]] = None
    tile_matrix_scales: Optional[Dict[int, float]] = None


COORDINATE_SYSTEMS = {
    "LKS_LVM": CoordinateSystemConfig(
        name="LKS_LVM", 
        description="Latvia TM coordinate system (dynamic from WMTS)",
        bounds=(25.1, 55.6, 32.3, 58.1),  # Actual WMTS coverage bounds
        tile_matrix_prefix="LKS_LVM",
        min_zoom=7,
        max_zoom=18,
        # Dynamic WMTS parameters
        wmts_url="https://lvmgeoproxy01.lvm.lv/wmts_b6948e305fb9446985a41b2aee54e07d/wmts",
        tile_matrix_set_id="LKS_LVM",
        layer_id="public:Topo10DTM",
        # Static fallback (will be overridden)
        epsg=3059
    ),
    "WebMercatorQuad": CoordinateSystemConfig(
        name="WebMercatorQuad",
        description="Web Mercator Quad (standard web mapping)",
        bounds=(20.0, 55.0, 29.0, 59.0),  # Latvia bounds in WGS84
        tile_matrix_prefix="",  # WebMercator uses simple zoom levels
        min_zoom=1,
        max_zoom=18,
        # Dynamic WMTS parameters
        wmts_url="https://lvmgeoproxy01.lvm.lv/wmts_b6948e305fb9446985a41b2aee54e07d/wmts",
        tile_matrix_set_id="WebMercatorQuad",
        layer_id="public:Topo10DTM",
        # Static fallback
        epsg=3857
    ),
    "EPSG:3857": CoordinateSystemConfig(
        name="Web Mercator",
        description="Web Mercator projection used by most web maps",
        bounds=(-180.0, -85.0511, 180.0, 85.0511),
        tile_matrix_prefix="EPSG:3857",
        min_zoom=0,
        max_zoom=20,
        # Static parameters (no WMTS source)
        epsg=3857,
        origin=(-20037508.342789244, 20037508.342789244)
    ),
    "EPSG:4326": CoordinateSystemConfig(
        name="WGS84",
        epsg=4326,
        description="WGS84 Geographic coordinate system",
        bounds=(-180.0, -90.0, 180.0, 90.0),
        origin=(-180.0, 90.0),
        tile_matrix_prefix="EPSG:4326",
        min_zoom=0,
        max_zoom=20
    ),
    "EPSG:25832": CoordinateSystemConfig(
        name="ETRS89 / UTM zone 32N",
        epsg=25832,
        description="European UTM zone 32N",
        bounds=(5.0, 47.0, 15.0, 55.0),
        origin=(166021.44, 6500000.0),
        tile_matrix_prefix="EPSG:25832",
        min_zoom=0,
        max_zoom=20
    )
}


def get_coordinate_system(name: str) -> Optional[CoordinateSystemConfig]:
    return COORDINATE_SYSTEMS.get(name)


def list_coordinate_systems() -> Dict[str, str]:
    return {key: config.description for key, config in COORDINATE_SYSTEMS.items()}