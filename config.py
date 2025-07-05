"""
Configuration Management

Handles application configuration including WMTS endpoint definitions,
caching settings, and environment variable loading. Supports both
Web Mercator and coordinate transformation endpoints.
"""

from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any
import json


class WMTSEndpoint(BaseSettings):
    url: str
    layer: str
    coordinate_system: str
    app_id: Optional[str] = None
    style: str = "raster"
    format: str = "image/vnd.jpeg-png8"


class Settings(BaseSettings):
    WMTS_ENDPOINTS: Dict[str, Dict[str, Any]] = {
        "latvia": {
            "url": "https://lvmgeoproxy01.lvm.lv/wmts_b6948e305fb9446985a41b2aee54e07d/wmts",
            "layer": "public:Topo10DTM",
            "coordinate_system": "LKS_LVM",
            "app_id": "lvmgeo.lvm.lv/",
            "style": "raster",
            "format": "image/vnd.jpeg-png8"
        },
        "latvia_webmercator": {
            "url": "https://lvmgeoproxy01.lvm.lv/wmts_b6948e305fb9446985a41b2aee54e07d/wmts",
            "layer": "public:Topo10DTM",
            "coordinate_system": "WebMercatorQuad",
            "app_id": "lvmgeo.lvm.lv/",
            "style": "raster",
            "format": "image/vnd.jpeg-png8"
        }
    }
    
    DEFAULT_ENDPOINT: str = "latvia_webmercator"
    
    CACHE_SIZE: int = 1000
    CACHE_TTL: int = 3600
    
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name == "WMTS_ENDPOINTS":
                return json.loads(raw_val)
            return cls.json_loads(raw_val)
    
    def get_endpoint(self, name: Optional[str] = None) -> WMTSEndpoint:
        endpoint_name = name or self.DEFAULT_ENDPOINT
        endpoint_data = self.WMTS_ENDPOINTS.get(endpoint_name)
        
        if not endpoint_data:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")
        
        return WMTSEndpoint(**endpoint_data)


settings = Settings()