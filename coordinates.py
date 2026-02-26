"""
Coordinate System Transformations

Handles coordinate transformations between Web Mercator (Leaflet) tiles and various
target coordinate systems including LKS_LVM. Supports both direct passthrough for
WebMercatorQuad and complex transformations for local coordinate systems.
"""

import math
import asyncio
from dataclasses import dataclass
from pyproj import Transformer, CRS
import logging
from typing import Optional
from coordinate_systems import CoordinateSystemConfig, get_coordinate_system
from wmts_capabilities import get_tile_matrix_set, get_layer_info, get_wmts_info, TileMatrixSet, LayerInfo
from crs_fetcher import get_crs_info, get_proj4_string, get_wkt_string

logger = logging.getLogger(__name__)


@dataclass
class TileCoordinate:
    z: int
    x: int
    y: int


@dataclass
class BoundingBox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


@dataclass
class TransformedTileCoordinate:
    tile_matrix: str
    tile_col: int
    tile_row: int
    quadrant_x: int = 0  # 0 = left, 1 = right
    quadrant_y: int = 0  # 0 = top, 1 = bottom


class CoordinateTransformer:
    def __init__(self, target_system: str = "LKS_LVM"):
        self.target_system_config = get_coordinate_system(target_system)
        
        if not self.target_system_config:
            raise ValueError(f"Unknown coordinate system: {target_system}")
        
        # CRS objects will be initialized dynamically
        self.wgs84_crs: Optional[CRS] = None
        self.target_crs: Optional[CRS] = None
        self.transformer_to_target: Optional[Transformer] = None
        self.transformer_to_wgs84: Optional[Transformer] = None
        
        # Bounds will be updated from WMTS layer info
        self.bounds = BoundingBox(
            min_lon=self.target_system_config.bounds[0],
            min_lat=self.target_system_config.bounds[1],
            max_lon=self.target_system_config.bounds[2],
            max_lat=self.target_system_config.bounds[3]
        )
        
        self.tile_size = 256
        self.tile_matrix_set: Optional[TileMatrixSet] = None
        self.layer_info: Optional[LayerInfo] = None
    
    async def load_wmts_parameters(self):
        """Load tile matrix parameters and CRS info from WMTS capabilities and spatialreference.org"""
        if (self.target_system_config.wmts_url and 
            self.target_system_config.tile_matrix_set_id and 
            not self.tile_matrix_set):
            
            # Fetch both layer and tile matrix set info
            self.layer_info, self.tile_matrix_set = await get_wmts_info(
                self.target_system_config.wmts_url,
                self.target_system_config.layer_id or "unknown",
                self.target_system_config.tile_matrix_set_id
            )
            
            if self.tile_matrix_set:
                logger.info(f"Loaded WMTS TileMatrixSet for {self.target_system_config.name}")
                
                # Update bounds from layer info if available, but use actual coverage for LKS_LVM
                if self.layer_info and self.layer_info.wgs84_bounding_box:
                    if self.target_system_config.name == "LKS_LVM":
                        # Use actual WMTS coverage bounds instead of layer bounds
                        self.bounds = BoundingBox(
                            min_lon=25.1,  # Actual western boundary of WMTS coverage
                            min_lat=55.6,
                            max_lon=32.3,  # Actual eastern boundary of WMTS coverage
                            max_lat=58.1
                        )
                        logger.info(f"Using actual WMTS coverage bounds for LKS_LVM: {self.bounds}")
                    else:
                        self.bounds = BoundingBox(
                            min_lon=self.layer_info.wgs84_bounding_box[0],
                            min_lat=self.layer_info.wgs84_bounding_box[1],
                            max_lon=self.layer_info.wgs84_bounding_box[2],
                            max_lat=self.layer_info.wgs84_bounding_box[3]
                        )
                        logger.info(f"Updated bounds from WMTS layer: {self.bounds}")
                
                # Initialize CRS objects dynamically
                await self._initialize_crs()
            else:
                logger.warning(f"Failed to load WMTS parameters for {self.target_system_config.name}")
    
    async def _initialize_crs(self):
        """Initialize CRS objects using dynamic EPSG fetching"""
        try:
            # Always use WGS84 as source
            self.wgs84_crs = CRS.from_epsg(4326)
            
            # Get target EPSG from WMTS or config
            target_epsg = None
            if self.tile_matrix_set and self.tile_matrix_set.epsg_code:
                target_epsg = self.tile_matrix_set.epsg_code
                logger.info(f"Using EPSG code from WMTS: {target_epsg}")
            elif self.target_system_config.epsg:
                target_epsg = self.target_system_config.epsg
                logger.info(f"Using fallback EPSG code: {target_epsg}")
            else:
                raise ValueError("No EPSG code available for target CRS")
            
            # Fetch CRS info from spatialreference.org
            crs_info = await get_crs_info(target_epsg)
            if crs_info:
                logger.info(f"Fetched CRS info from spatialreference.org: {crs_info.name}")
            
            # Try to create CRS from spatialreference.org data, fallback to EPSG
            try:
                # First try with Proj4 string if available
                proj4_str = await get_proj4_string(target_epsg)
                if proj4_str:
                    self.target_crs = CRS.from_proj4(proj4_str)
                    logger.info(f"Created target CRS from Proj4: {proj4_str}")
                else:
                    # Fallback to EPSG code
                    self.target_crs = CRS.from_epsg(target_epsg)
                    logger.info(f"Created target CRS from EPSG: {target_epsg}")
            except Exception as e:
                logger.warning(f"Failed to create CRS from spatialreference.org data: {e}")
                # Final fallback to EPSG
                self.target_crs = CRS.from_epsg(target_epsg)
                logger.info(f"Using fallback EPSG CRS: {target_epsg}")
            
            # Create transformers
            self.transformer_to_target = Transformer.from_crs(
                self.wgs84_crs, self.target_crs, always_xy=True
            )
            self.transformer_to_wgs84 = Transformer.from_crs(
                self.target_crs, self.wgs84_crs, always_xy=True
            )
            
            logger.info(f"Initialized CRS transformers: WGS84 <-> {self.target_crs.to_string()}")
            
        except Exception as e:
            logger.error(f"Failed to initialize CRS: {e}")
            # Emergency fallback
            self.wgs84_crs = CRS.from_epsg(4326)
            self.target_crs = CRS.from_epsg(self.target_system_config.epsg or 3059)
            self.transformer_to_target = Transformer.from_crs(
                self.wgs84_crs, self.target_crs, always_xy=True
            )
            self.transformer_to_wgs84 = Transformer.from_crs(
                self.target_crs, self.wgs84_crs, always_xy=True
            )
    
    def get_tile_matrix(self, zoom_level: int):
        """Get tile matrix for zoom level, with fallback to static parameters"""
        if self.tile_matrix_set and zoom_level in self.tile_matrix_set.tile_matrices:
            return self.tile_matrix_set.tile_matrices[zoom_level]
        return None
    
    def tile_to_bbox_wgs84(self, tile: TileCoordinate) -> BoundingBox:
        n = 2.0 ** tile.z
        lon_min = tile.x / n * 360.0 - 180.0
        lon_max = (tile.x + 1) / n * 360.0 - 180.0
        
        lat_max_rad = math.atan(math.sinh(math.pi * (1 - 2 * tile.y / n)))
        lat_max = math.degrees(lat_max_rad)
        
        lat_min_rad = math.atan(math.sinh(math.pi * (1 - 2 * (tile.y + 1) / n)))
        lat_min = math.degrees(lat_min_rad)
        
        return BoundingBox(
            min_lon=lon_min,
            min_lat=lat_min,
            max_lon=lon_max,
            max_lat=lat_max
        )
    
    async def transform_tile(self, tile: TileCoordinate) -> TransformedTileCoordinate:
        # Special case: WebMercatorQuad uses direct tile coordinates (no transformation)
        if self.target_system_config.name == "WebMercatorQuad":
            tile_matrix_id = str(tile.z)  # WebMercator uses simple zoom levels
            return TransformedTileCoordinate(
                tile_matrix=tile_matrix_id,
                tile_col=tile.x,
                tile_row=tile.y,
                quadrant_x=0,
                quadrant_y=0
            )
        
        # Ensure WMTS parameters are loaded
        await self.load_wmts_parameters()
        
        # Ensure transformers are initialized
        if not self.transformer_to_target:
            await self._initialize_crs()
        
        zoom_level = min(tile.z, self.target_system_config.max_zoom)
        if zoom_level < self.target_system_config.min_zoom:
            zoom_level = self.target_system_config.min_zoom
        
        # Get tile matrix from WMTS or fallback to static parameters
        tile_matrix = self.get_tile_matrix(zoom_level)
        
        if tile_matrix:
            # Use dynamic WMTS parameters
            scale_denominator = tile_matrix.scale_denominator
            origin_x, origin_y = tile_matrix.top_left_corner
            wmts_tile_width = tile_matrix.tile_width
            wmts_tile_height = tile_matrix.tile_height
            
            # WMTS standard: pixel size = scale_denominator * 0.00028 (meters per pixel)
            wmts_pixel_size = scale_denominator * 0.00028
            
            logger.info(f"Using WMTS parameters: scale={scale_denominator}, origin=({origin_x}, {origin_y}), tile_size={wmts_tile_width}x{wmts_tile_height}")
        else:
            # Fallback to static parameters
            if self.target_system_config.tile_matrix_scales:
                scale_denominator = self.target_system_config.tile_matrix_scales.get(
                    zoom_level, 
                    self.target_system_config.tile_matrix_scales[10]
                )
                wmts_pixel_size = scale_denominator * 0.00028
            else:
                wmts_pixel_size = self._calculate_pixel_size(zoom_level) * 2  # Scale for 512px tiles
            
            origin_x, origin_y = self.target_system_config.origin or (0, 0)
            wmts_tile_width = 512
            wmts_tile_height = 512
            
            logger.warning(f"Using fallback parameters for zoom {zoom_level}")
        
        # Calculate the bounds of the Leaflet tile in WGS84
        bbox_wgs84 = self.tile_to_bbox_wgs84(tile)
        
        # Transform the four corners to target coordinate system
        corners_wgs84 = [
            (bbox_wgs84.min_lon, bbox_wgs84.max_lat),  # top-left
            (bbox_wgs84.max_lon, bbox_wgs84.max_lat),  # top-right
            (bbox_wgs84.min_lon, bbox_wgs84.min_lat),  # bottom-left
            (bbox_wgs84.max_lon, bbox_wgs84.min_lat),  # bottom-right
        ]
        
        corners_target = []
        for lon, lat in corners_wgs84:
            x, y = self.transformer_to_target.transform(lon, lat)
            corners_target.append((x, y))
        
        # Find the bounding box in target coordinates
        min_x = min(x for x, y in corners_target)
        max_x = max(x for x, y in corners_target)
        min_y = min(y for x, y in corners_target)
        max_y = max(y for x, y in corners_target)
        
        # Calculate center in target coordinates
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Calculate WMTS tile coordinates using center point
        # Each WMTS tile covers wmts_tile_width x wmts_tile_height pixels
        wmts_tile_size_x = wmts_tile_width * wmts_pixel_size
        wmts_tile_size_y = wmts_tile_height * wmts_pixel_size
        
        wmts_tile_col = int((center_x - origin_x) / wmts_tile_size_x)
        wmts_tile_row = int((origin_y - center_y) / wmts_tile_size_y)
        
        # Calculate which quadrant of the WMTS tile this Leaflet tile represents
        # Each WMTS tile (512x512) contains 4 Leaflet tiles (256x256) in a 2x2 grid
        tiles_per_wmts_tile = wmts_tile_width // 256
        
        # Calculate position within the WMTS tile
        wmts_tile_left = origin_x + wmts_tile_col * wmts_tile_size_x
        wmts_tile_top = origin_y - wmts_tile_row * wmts_tile_size_y
        
        # Position of this Leaflet tile's center relative to WMTS tile origin
        relative_x = center_x - wmts_tile_left
        relative_y = wmts_tile_top - center_y
        
        # Calculate quadrant (0,0 = top-left, 1,1 = bottom-right)
        leaflet_tile_size_x = wmts_tile_size_x / tiles_per_wmts_tile
        leaflet_tile_size_y = wmts_tile_size_y / tiles_per_wmts_tile
        
        quadrant_x = int(relative_x / leaflet_tile_size_x)
        quadrant_y = int(relative_y / leaflet_tile_size_y)
        
        # Ensure quadrants are within bounds
        quadrant_x = max(0, min(tiles_per_wmts_tile - 1, quadrant_x))
        quadrant_y = max(0, min(tiles_per_wmts_tile - 1, quadrant_y))
        
        tile_matrix_id = f"{self.target_system_config.tile_matrix_prefix}:{zoom_level}"
        
        logger.info(f"Transformed WGS84 tile {tile.z}/{tile.x}/{tile.y} -> center ({center_x:.2f}, {center_y:.2f}) -> WMTS {tile_matrix_id}/{wmts_tile_col}/{wmts_tile_row} quadrant ({quadrant_x},{quadrant_y})")
        
        return TransformedTileCoordinate(
            tile_matrix=tile_matrix_id,
            tile_col=wmts_tile_col,
            tile_row=wmts_tile_row,
            quadrant_x=quadrant_x,
            quadrant_y=quadrant_y
        )
    
    def _calculate_pixel_size(self, zoom_level: int) -> float:
        return 156543.03392804062 / (2 ** zoom_level)
    
    async def is_valid_tile(self, tile: TileCoordinate) -> bool:
        # For WebMercatorQuad, use standard Web Mercator validation
        if self.target_system_config.name == "WebMercatorQuad":
            if tile.z < 0 or tile.z > 20:
                return False
            max_tile = 2 ** tile.z
            if tile.x < 0 or tile.x >= max_tile:
                return False
            if tile.y < 0 or tile.y >= max_tile:
                return False
            return True
        
        # For other coordinate systems, use LKS_LVM validation
        if tile.z < 0 or tile.z > 20:
            return False
        
        max_tile = 2 ** tile.z
        if tile.x < 0 or tile.x >= max_tile:
            return False
        if tile.y < 0 or tile.y >= max_tile:
            return False
        
        # Check if the transformed coordinates would be valid
        try:
            transformed = await self.transform_tile(tile)
            zoom_level = int(transformed.tile_matrix.split(":")[1])
            
            # Check against WMTS server bounds
            from tile_matrix_limits import is_tile_in_bounds
            return is_tile_in_bounds(zoom_level, transformed.tile_col, transformed.tile_row)
        except:
            return False