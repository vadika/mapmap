"""
WMTS Capabilities Parser

Dynamically fetches and parses WMTS GetCapabilities XML to extract tile matrix
parameters, layer information, and coordinate system details.
"""
import xml.etree.ElementTree as ET
import httpx
import logging
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TileMatrix:
    identifier: str
    scale_denominator: float
    top_left_corner: Tuple[float, float]
    tile_width: int
    tile_height: int
    matrix_width: int
    matrix_height: int

@dataclass
class LayerInfo:
    identifier: str
    title: str
    abstract: Optional[str]
    wgs84_bounding_box: Optional[Tuple[float, float, float, float]]  # min_lon, min_lat, max_lon, max_lat
    tile_matrix_set_links: List[str]
    formats: List[str]
    styles: List[str]

@dataclass
class TileMatrixSet:
    identifier: str
    supported_crs: str
    epsg_code: Optional[int]
    well_known_scale_set: Optional[str]
    tile_matrices: Dict[int, TileMatrix]

class WMTSCapabilitiesParser:
    def __init__(self, capabilities_url: str):
        self.capabilities_url = capabilities_url
        self.namespaces = {
            'wmts': 'http://www.opengis.net/wmts/1.0',
            'ows': 'http://www.opengis.net/ows/1.1'
        }
        
    async def fetch_capabilities(self) -> str:
        """Fetch WMTS GetCapabilities document"""
        params = {
            'SERVICE': 'WMTS',
            'REQUEST': 'GetCapabilities',
            'VERSION': '1.0.0'
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.capabilities_url, params=params)
            response.raise_for_status()
            return response.text
    
    def parse_tile_matrix_set(self, capabilities_xml: str, tile_matrix_set_id: str) -> Optional[TileMatrixSet]:
        """Parse a specific TileMatrixSet from capabilities"""
        try:
            root = ET.fromstring(capabilities_xml)
            
            # Find the TileMatrixSet
            for tms_elem in root.findall('.//wmts:TileMatrixSet', self.namespaces):
                identifier_elem = tms_elem.find('ows:Identifier', self.namespaces)
                if identifier_elem is not None and identifier_elem.text == tile_matrix_set_id:
                    return self._parse_tile_matrix_set_element(tms_elem)
            
            return None
        except Exception as e:
            logger.error(f"Failed to parse TileMatrixSet {tile_matrix_set_id}: {e}")
            return None
    
    def parse_layer_info(self, capabilities_xml: str, layer_id: str) -> Optional[LayerInfo]:
        """Parse layer information from capabilities"""
        try:
            root = ET.fromstring(capabilities_xml)
            
            # Find the Layer
            for layer_elem in root.findall('.//wmts:Layer', self.namespaces):
                identifier_elem = layer_elem.find('ows:Identifier', self.namespaces)
                if identifier_elem is not None and identifier_elem.text == layer_id:
                    return self._parse_layer_element(layer_elem)
            
            return None
        except Exception as e:
            logger.error(f"Failed to parse Layer {layer_id}: {e}")
            return None
    
    def _parse_layer_element(self, layer_elem) -> LayerInfo:
        """Parse a Layer element"""
        identifier = layer_elem.find('ows:Identifier', self.namespaces).text
        title_elem = layer_elem.find('ows:Title', self.namespaces)
        title = title_elem.text if title_elem is not None else identifier
        
        abstract_elem = layer_elem.find('ows:Abstract', self.namespaces)
        abstract = abstract_elem.text if abstract_elem is not None else None
        
        # Parse WGS84BoundingBox
        wgs84_bbox = None
        bbox_elem = layer_elem.find('ows:WGS84BoundingBox', self.namespaces)
        if bbox_elem is not None:
            lower_corner = bbox_elem.find('ows:LowerCorner', self.namespaces)
            upper_corner = bbox_elem.find('ows:UpperCorner', self.namespaces)
            if lower_corner is not None and upper_corner is not None:
                lower_coords = [float(x) for x in lower_corner.text.strip().split()]
                upper_coords = [float(x) for x in upper_corner.text.strip().split()]
                # WGS84BoundingBox format: LowerCorner="min_lon min_lat" UpperCorner="max_lon max_lat"
                wgs84_bbox = (lower_coords[0], lower_coords[1], upper_coords[0], upper_coords[1])
        
        # Parse TileMatrixSetLink
        tile_matrix_set_links = []
        for link_elem in layer_elem.findall('wmts:TileMatrixSetLink', self.namespaces):
            tms_ref = link_elem.find('wmts:TileMatrixSet', self.namespaces)
            if tms_ref is not None:
                tile_matrix_set_links.append(tms_ref.text)
        
        # Parse formats
        formats = []
        for format_elem in layer_elem.findall('wmts:Format', self.namespaces):
            formats.append(format_elem.text)
        
        # Parse styles
        styles = []
        for style_elem in layer_elem.findall('wmts:Style', self.namespaces):
            style_id = style_elem.find('ows:Identifier', self.namespaces)
            if style_id is not None:
                styles.append(style_id.text)
        
        logger.info(f"Parsed Layer '{identifier}': title='{title}', bbox={wgs84_bbox}, TileMatrixSets={tile_matrix_set_links}")
        
        return LayerInfo(
            identifier=identifier,
            title=title,
            abstract=abstract,
            wgs84_bounding_box=wgs84_bbox,
            tile_matrix_set_links=tile_matrix_set_links,
            formats=formats,
            styles=styles
        )
    
    def _parse_tile_matrix_set_element(self, tms_elem) -> TileMatrixSet:
        """Parse a TileMatrixSet element"""
        identifier = tms_elem.find('ows:Identifier', self.namespaces).text
        supported_crs = tms_elem.find('ows:SupportedCRS', self.namespaces).text
        
        # Extract EPSG code from CRS string (e.g., "urn:ogc:def:crs:EPSG:6.18:3:3059" -> 3059)
        epsg_code = None
        if supported_crs:
            if 'EPSG' in supported_crs:
                # Handle various EPSG URI formats
                if ':' in supported_crs:
                    parts = supported_crs.split(':')
                    for i, part in enumerate(parts):
                        if part == 'EPSG' and i + 1 < len(parts):
                            # Try to find the numeric EPSG code
                            for j in range(i + 1, len(parts)):
                                try:
                                    epsg_code = int(parts[j])
                                    break
                                except ValueError:
                                    continue
                            break
                else:
                    # Simple EPSG:XXXX format
                    try:
                        epsg_code = int(supported_crs.replace('EPSG:', ''))
                    except ValueError:
                        pass
        
        # Check for WellKnownScaleSet
        well_known_scale_set_elem = tms_elem.find('wmts:WellKnownScaleSet', self.namespaces)
        well_known_scale_set = well_known_scale_set_elem.text if well_known_scale_set_elem is not None else None
        
        tile_matrices = {}
        
        for tm_elem in tms_elem.findall('wmts:TileMatrix', self.namespaces):
            tile_matrix = self._parse_tile_matrix_element(tm_elem)
            # Extract zoom level from identifier (e.g., "LKS_LVM:10" -> 10)
            zoom_level = int(tile_matrix.identifier.split(':')[1])
            tile_matrices[zoom_level] = tile_matrix
        
        logger.info(f"Parsed TileMatrixSet '{identifier}': CRS={supported_crs}, EPSG={epsg_code}, WellKnownScaleSet={well_known_scale_set}")
        
        return TileMatrixSet(
            identifier=identifier,
            supported_crs=supported_crs,
            epsg_code=epsg_code,
            well_known_scale_set=well_known_scale_set,
            tile_matrices=tile_matrices
        )
    
    def _parse_tile_matrix_element(self, tm_elem) -> TileMatrix:
        """Parse a TileMatrix element"""
        identifier = tm_elem.find('ows:Identifier', self.namespaces).text
        scale_denominator = float(tm_elem.find('wmts:ScaleDenominator', self.namespaces).text)
        
        # Parse TopLeftCorner
        top_left_text = tm_elem.find('wmts:TopLeftCorner', self.namespaces).text
        top_left_coords = [float(x) for x in top_left_text.strip().split()]
        top_left_corner = (top_left_coords[0], top_left_coords[1])
        
        tile_width = int(tm_elem.find('wmts:TileWidth', self.namespaces).text)
        tile_height = int(tm_elem.find('wmts:TileHeight', self.namespaces).text)
        matrix_width = int(tm_elem.find('wmts:MatrixWidth', self.namespaces).text)
        matrix_height = int(tm_elem.find('wmts:MatrixHeight', self.namespaces).text)
        
        return TileMatrix(
            identifier=identifier,
            scale_denominator=scale_denominator,
            top_left_corner=top_left_corner,
            tile_width=tile_width,
            tile_height=tile_height,
            matrix_width=matrix_width,
            matrix_height=matrix_height
        )

# Cache for capabilities to avoid repeated requests
_capabilities_cache = {}

async def get_tile_matrix_set(capabilities_url: str, tile_matrix_set_id: str) -> Optional[TileMatrixSet]:
    """Get TileMatrixSet with caching"""
    cache_key = f"{capabilities_url}#tms#{tile_matrix_set_id}"
    
    if cache_key in _capabilities_cache:
        logger.info(f"Using cached TileMatrixSet for {tile_matrix_set_id}")
        return _capabilities_cache[cache_key]
    
    parser = WMTSCapabilitiesParser(capabilities_url)
    capabilities_xml = await parser.fetch_capabilities()
    tile_matrix_set = parser.parse_tile_matrix_set(capabilities_xml, tile_matrix_set_id)
    
    if tile_matrix_set:
        _capabilities_cache[cache_key] = tile_matrix_set
        logger.info(f"Cached TileMatrixSet for {tile_matrix_set_id} with {len(tile_matrix_set.tile_matrices)} zoom levels, EPSG: {tile_matrix_set.epsg_code}")
    
    return tile_matrix_set

async def get_layer_info(capabilities_url: str, layer_id: str) -> Optional[LayerInfo]:
    """Get LayerInfo with caching"""
    cache_key = f"{capabilities_url}#layer#{layer_id}"
    
    if cache_key in _capabilities_cache:
        logger.info(f"Using cached LayerInfo for {layer_id}")
        return _capabilities_cache[cache_key]
    
    parser = WMTSCapabilitiesParser(capabilities_url)
    capabilities_xml = await parser.fetch_capabilities()
    layer_info = parser.parse_layer_info(capabilities_xml, layer_id)
    
    if layer_info:
        _capabilities_cache[cache_key] = layer_info
        logger.info(f"Cached LayerInfo for {layer_id}")
    
    return layer_info

async def get_wmts_info(capabilities_url: str, layer_id: str, tile_matrix_set_id: str) -> Tuple[Optional[LayerInfo], Optional[TileMatrixSet]]:
    """Get both layer and tile matrix set information in one call"""
    # Fetch capabilities once and parse both
    parser = WMTSCapabilitiesParser(capabilities_url)
    capabilities_xml = await parser.fetch_capabilities()
    
    layer_info = parser.parse_layer_info(capabilities_xml, layer_id)
    tile_matrix_set = parser.parse_tile_matrix_set(capabilities_xml, tile_matrix_set_id)
    
    # Cache individually
    if layer_info:
        _capabilities_cache[f"{capabilities_url}#layer#{layer_id}"] = layer_info
    if tile_matrix_set:
        _capabilities_cache[f"{capabilities_url}#tms#{tile_matrix_set_id}"] = tile_matrix_set
    
    return layer_info, tile_matrix_set