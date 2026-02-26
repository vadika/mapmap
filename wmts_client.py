"""
WMTS Client

HTTP client for fetching tiles from WMTS servers. Handles tile requests,
quadrant extraction for 512x512 WMTS tiles, and error handling.
"""

import httpx
import logging
from urllib.parse import urlencode, quote
from typing import Optional
from coordinates import TransformedTileCoordinate
from config import settings, WMTSEndpoint
from PIL import Image
import io

logger = logging.getLogger(__name__)


class WMTSClient:
    def __init__(self, endpoint_name: Optional[str] = None):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.endpoint = settings.get_endpoint(endpoint_name)
    
    async def fetch_tile(self, tile_coord: TransformedTileCoordinate) -> Optional[bytes]:
        params = {
            "layer": self.endpoint.layer,
            "style": self.endpoint.style,
            "tilematrixset": self.endpoint.coordinate_system,
            "Service": "WMTS",
            "Request": "GetTile",
            "Version": "1.0.0",
            "Format": self.endpoint.format,
            "TileMatrix": tile_coord.tile_matrix,
            "TileCol": str(tile_coord.tile_col),
            "TileRow": str(tile_coord.tile_row)
        }
        
        if self.endpoint.app_id:
            params["appid"] = self.endpoint.app_id
        
        url = f"{self.endpoint.url}?{self._build_query_string(params)}"
        
        try:
            logger.info(f"Fetching tile from: {url}")
            response = await self.client.get(url)
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "image" in content_type:
                    logger.info(f"Successfully fetched tile: {tile_coord.tile_matrix}/{tile_coord.tile_col}/{tile_coord.tile_row}")
                    
                    # Handle 512x512 tiles for Leaflet compatibility
                    try:
                        # Open the image
                        image = Image.open(io.BytesIO(response.content))
                        original_size = image.size
                        
                        if image.size == (512, 512):
                            # Cut 512x512 tile into the appropriate 256x256 quadrant
                            quadrant_x = getattr(tile_coord, 'quadrant_x', 0)
                            quadrant_y = getattr(tile_coord, 'quadrant_y', 0)
                            
                            # Calculate crop coordinates
                            left = quadrant_x * 256
                            top = quadrant_y * 256
                            right = left + 256
                            bottom = top + 256
                            
                            # Crop the appropriate quadrant
                            image = image.crop((left, top, right, bottom))
                            logger.info(f"Cut tile from {original_size} to 256x256 quadrant ({quadrant_x},{quadrant_y})")
                        elif image.size != (256, 256):
                            # Resize other sizes to 256x256
                            image = image.resize((256, 256), Image.Resampling.LANCZOS)
                            logger.info(f"Resized tile from {original_size} to 256x256")
                        
                        # Convert back to bytes as PNG for better compatibility
                        output = io.BytesIO()
                        image.save(output, format='PNG')
                        return output.getvalue()
                    except Exception as e:
                        logger.warning(f"Failed to process tile, returning original: {e}")
                        return response.content
                else:
                    logger.error(f"Invalid content type: {content_type}")
                    return None
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching tile: {str(e)}")
            return None
    
    def _build_query_string(self, params: dict) -> str:
        encoded_params = []
        for key, value in params.items():
            if key == "layer":
                encoded_params.append(f"{key}={quote(value, safe=':')}")
            elif key == "TileMatrix":
                encoded_params.append(f"{key}={quote(value, safe=':')}")
            else:
                encoded_params.append(f"{key}={value}")
        return "&".join(encoded_params)
    
    async def close(self):
        await self.client.aclose()