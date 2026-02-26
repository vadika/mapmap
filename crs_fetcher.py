"""
CRS (Coordinate Reference System) Fetcher

Fetches coordinate reference system information from spatialreference.org
including Proj4 strings, WKT definitions, and metadata for EPSG codes.
"""
import httpx
import logging
from typing import Optional, Dict
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class CRSInfo:
    epsg_code: int
    name: str
    proj4_text: Optional[str]
    wkt: Optional[str]
    esri_wkt: Optional[str]
    authority: str
    authority_code: str
    area_of_use: Optional[str]
    scope: Optional[str]

class CRSFetcher:
    def __init__(self):
        self.base_url = "https://spatialreference.org"
        self.timeout = 30.0
        
    async def fetch_crs_info(self, epsg_code: int) -> Optional[CRSInfo]:
        """Fetch CRS information from spatialreference.org"""
        try:
            # Fetch JSON format for structured data
            json_url = f"{self.base_url}/ref/epsg/{epsg_code}/json/"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(json_url)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_crs_json(data, epsg_code)
                else:
                    logger.warning(f"Failed to fetch CRS info for EPSG:{epsg_code}, status: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching CRS info for EPSG:{epsg_code}: {e}")
            return None
    
    def _parse_crs_json(self, data: dict, epsg_code: int) -> CRSInfo:
        """Parse CRS information from JSON response"""
        name = data.get('name', f'EPSG:{epsg_code}')
        
        # Extract different format representations
        proj4_text = None
        wkt = None
        esri_wkt = None
        
        # Try to get Proj4 format
        try:
            proj4_url = f"{self.base_url}/ref/epsg/{epsg_code}/proj4/"
            # We'll fetch this separately if needed
        except:
            pass
            
        # Try to get WKT format  
        try:
            wkt_data = data.get('wkt')
            if wkt_data:
                wkt = wkt_data
        except:
            pass
        
        return CRSInfo(
            epsg_code=epsg_code,
            name=name,
            proj4_text=proj4_text,
            wkt=wkt,
            esri_wkt=esri_wkt,
            authority="EPSG",
            authority_code=str(epsg_code),
            area_of_use=data.get('area'),
            scope=data.get('scope')
        )
    
    async def fetch_proj4_string(self, epsg_code: int) -> Optional[str]:
        """Fetch Proj4 string specifically"""
        try:
            proj4_url = f"{self.base_url}/ref/epsg/{epsg_code}/proj4/"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(proj4_url)
                
                if response.status_code == 200:
                    # Response is plain text Proj4 string
                    proj4_str = response.text.strip()
                    logger.info(f"Fetched Proj4 for EPSG:{epsg_code}: {proj4_str}")
                    return proj4_str
                else:
                    logger.warning(f"Failed to fetch Proj4 for EPSG:{epsg_code}, status: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Proj4 for EPSG:{epsg_code}: {e}")
            return None
    
    async def fetch_wkt_string(self, epsg_code: int) -> Optional[str]:
        """Fetch WKT string specifically"""
        try:
            wkt_url = f"{self.base_url}/ref/epsg/{epsg_code}/ogcwkt/"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(wkt_url)
                
                if response.status_code == 200:
                    # Response is plain text WKT string
                    wkt_str = response.text.strip()
                    logger.info(f"Fetched WKT for EPSG:{epsg_code}: {wkt_str[:100]}...")
                    return wkt_str
                else:
                    logger.warning(f"Failed to fetch WKT for EPSG:{epsg_code}, status: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching WKT for EPSG:{epsg_code}: {e}")
            return None

# Cache for CRS info to avoid repeated requests
_crs_cache: Dict[int, CRSInfo] = {}

async def get_crs_info(epsg_code: int) -> Optional[CRSInfo]:
    """Get CRS information with caching"""
    if epsg_code in _crs_cache:
        logger.info(f"Using cached CRS info for EPSG:{epsg_code}")
        return _crs_cache[epsg_code]
    
    fetcher = CRSFetcher()
    crs_info = await fetcher.fetch_crs_info(epsg_code)
    
    if crs_info:
        _crs_cache[epsg_code] = crs_info
        logger.info(f"Cached CRS info for EPSG:{epsg_code}: {crs_info.name}")
    
    return crs_info

async def get_proj4_string(epsg_code: int) -> Optional[str]:
    """Get Proj4 string with caching"""
    cache_key = f"proj4_{epsg_code}"
    
    # Check if we have it in the CRS info cache
    if epsg_code in _crs_cache and _crs_cache[epsg_code].proj4_text:
        return _crs_cache[epsg_code].proj4_text
    
    fetcher = CRSFetcher()
    proj4_str = await fetcher.fetch_proj4_string(epsg_code)
    
    # Update cache
    if proj4_str and epsg_code in _crs_cache:
        _crs_cache[epsg_code].proj4_text = proj4_str
    
    return proj4_str

async def get_wkt_string(epsg_code: int) -> Optional[str]:
    """Get WKT string with caching"""
    # Check if we have it in the CRS info cache
    if epsg_code in _crs_cache and _crs_cache[epsg_code].wkt:
        return _crs_cache[epsg_code].wkt
    
    fetcher = CRSFetcher()
    wkt_str = await fetcher.fetch_wkt_string(epsg_code)
    
    # Update cache
    if wkt_str and epsg_code in _crs_cache:
        _crs_cache[epsg_code].wkt = wkt_str
    
    return wkt_str