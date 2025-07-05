"""
MapMap Tile Proxy Server

A FastAPI-based tile proxy that provides seamless access to WMTS services through 
standard z/x/y tile URLs. Supports both direct Web Mercator passthrough and 
coordinate system transformations.
"""

from fastapi import FastAPI, HTTPException, Response, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import httpx
import logging
from typing import Optional, Dict
import asyncio
from cachetools import TTLCache
import io
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from config import settings
from coordinates import TileCoordinate, CoordinateTransformer
from wmts_client import WMTSClient
from coordinate_systems import list_coordinate_systems, get_coordinate_system

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MapMap Tile Proxy",
    description="Production-ready WMTS tile proxy with coordinate transformation",
    version="1.0.0"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security middleware
if settings.get_allowed_hosts() != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.get_allowed_hosts())

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

# Metrics
REQUEST_COUNT = Counter('mapmap_requests_total', 'Total requests', ['endpoint', 'method', 'status'])
REQUEST_DURATION = Histogram('mapmap_request_duration_seconds', 'Request duration', ['endpoint'])
TILE_CACHE_HITS = Counter('mapmap_cache_hits_total', 'Cache hits')
TILE_CACHE_MISSES = Counter('mapmap_cache_misses_total', 'Cache misses')

tile_cache = TTLCache(maxsize=settings.CACHE_SIZE, ttl=settings.CACHE_TTL)
transformers: Dict[str, CoordinateTransformer] = {}
clients: Dict[str, WMTSClient] = {}


def get_transformer(endpoint_name: Optional[str] = None) -> CoordinateTransformer:
    name = endpoint_name or settings.DEFAULT_ENDPOINT
    if name not in transformers:
        endpoint = settings.get_endpoint(name)
        transformers[name] = CoordinateTransformer(endpoint.coordinate_system)
    return transformers[name]


def get_client(endpoint_name: Optional[str] = None) -> WMTSClient:
    name = endpoint_name or settings.DEFAULT_ENDPOINT
    if name not in clients:
        clients[name] = WMTSClient(name)
    return clients[name]


@app.get("/")
async def root():
    return {
        "message": "MapMap Tile Proxy", 
        "version": "1.0.0",
        "endpoints": list(settings.WMTS_ENDPOINTS.keys()),
        "coordinate_systems": list_coordinate_systems()
    }


@app.post("/cache/clear")
async def clear_cache():
    """Clear all caches including transformers and tiles"""
    global transformers, clients, tile_cache
    transformers.clear()
    clients.clear()
    tile_cache.clear()
    return {"message": "All caches cleared"}


@app.get("/bounds/{endpoint}")
async def get_bounds(endpoint: Optional[str] = None):
    """Get valid WGS84 bounds for a specific endpoint"""
    try:
        endpoint_name = endpoint or settings.DEFAULT_ENDPOINT
        transformer = get_transformer(endpoint_name)
        
        # Load WMTS parameters to get actual bounds
        await transformer.load_wmts_parameters()
        
        # Return the bounds from the transformer
        bounds = transformer.bounds
        
        return {
            "endpoint": endpoint_name,
            "bounds": {
                "southwest": [bounds.min_lat, bounds.min_lon],
                "northeast": [bounds.max_lat, bounds.max_lon],
                "min_lon": bounds.min_lon,
                "min_lat": bounds.min_lat, 
                "max_lon": bounds.max_lon,
                "max_lat": bounds.max_lat
            },
            "zoom_range": {
                "min_zoom": transformer.target_system_config.min_zoom,
                "max_zoom": transformer.target_system_config.max_zoom
            }
        }
    except Exception as e:
        logger.error(f"Failed to get bounds for endpoint {endpoint}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get bounds")


@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    duration = time.time() - start_time
    endpoint = request.url.path.split('/')[1] if len(request.url.path.split('/')) > 1 else "root"
    
    REQUEST_COUNT.labels(endpoint=endpoint, method=request.method, status=response.status_code).inc()
    REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)
    
    return response

@app.get("/tiles/{z}/{x}/{y}")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/hour" if settings.RATE_LIMIT_ENABLED else "10000/hour")
async def get_tile(
    request: Request,
    z: int, 
    x: int, 
    y: int,
    endpoint: Optional[str] = Query(None, description="WMTS endpoint name"),
    passthrough: bool = Query(False, description="Use WebMercator passthrough (no coordinate transformation)")
):
    try:
        # Validate coordinates first
        if z < 0 or x < 0 or y < 0:
            raise HTTPException(status_code=400, detail="Tile coordinates must be non-negative")
            
        endpoint_name = endpoint or settings.DEFAULT_ENDPOINT
        cache_key = f"{endpoint_name}-{z}-{x}-{y}"
        
        if cache_key in tile_cache:
            TILE_CACHE_HITS.inc()
            logger.debug(f"Cache hit for tile {z}/{x}/{y} from {endpoint_name}")
            return Response(content=tile_cache[cache_key], media_type="image/png")
        
        TILE_CACHE_MISSES.inc()
        
        tile_coord = TileCoordinate(z=z, x=x, y=y)
        
        transformer = get_transformer(endpoint_name)
        client = get_client(endpoint_name)
        
        if not await transformer.is_valid_tile(tile_coord):
            raise HTTPException(status_code=400, detail="Tile coordinates out of bounds")
        
        transformed_coords = await transformer.transform_tile(tile_coord)
        
        # Check if transformed coordinates are in the valid range for WMTS server
        # Skip bounds check for WebMercatorQuad as it uses different validation
        endpoint_config = settings.get_endpoint(endpoint_name)
        if endpoint_config.coordinate_system != "WebMercatorQuad":
            from tile_matrix_limits import is_tile_in_bounds
            zoom_level = int(transformed_coords.tile_matrix.split(":")[1])
            
            if not is_tile_in_bounds(zoom_level, transformed_coords.tile_col, transformed_coords.tile_row):
                logger.warning(f"Transformed tile {transformed_coords.tile_matrix}/{transformed_coords.tile_col}/{transformed_coords.tile_row} is outside WMTS server bounds")
                # Return a 1x1 transparent PNG instead of making the request
                import base64
                transparent_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
                return Response(content=transparent_png, media_type="image/png")
        
        tile_data = await client.fetch_tile(transformed_coords)
        
        if tile_data:
            tile_cache[cache_key] = tile_data
            return Response(content=tile_data, media_type="image/png")
        else:
            raise HTTPException(status_code=404, detail="Tile not found")
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching tile {z}/{x}/{y}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/coordinate-systems")
async def get_coordinate_systems():
    return list_coordinate_systems()


@app.get("/endpoints")
async def get_endpoints():
    endpoints = {}
    for name, config in settings.WMTS_ENDPOINTS.items():
        endpoints[name] = {
            "url": config["url"],
            "layer": config["layer"],
            "coordinate_system": config["coordinate_system"]
        }
    return endpoints


@app.get("/debug/{z}/{x}/{y}")
async def debug_tile(z: int, x: int, y: int):
    """Debug endpoint to show coordinate transformation without making WMTS request"""
    try:
        tile_coord = TileCoordinate(z=z, x=x, y=y)
        transformer = get_transformer("latvia")
        
        bbox = transformer.tile_to_bbox_wgs84(tile_coord)
        transformed = await transformer.transform_tile(tile_coord)
        
        return {
            "input": {"z": z, "x": x, "y": y},
            "wgs84_bbox": {
                "min_lon": bbox.min_lon,
                "min_lat": bbox.min_lat,
                "max_lon": bbox.max_lon,
                "max_lat": bbox.max_lat
            },
            "transformed": {
                "tile_matrix": transformed.tile_matrix,
                "tile_col": transformed.tile_col,
                "tile_row": transformed.tile_row
            },
            "valid": await transformer.is_valid_tile(tile_coord)
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy", 
        "cache_size": len(tile_cache),
        "version": "1.0.0",
        "timestamp": time.time()
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    if not settings.ENABLE_METRICS:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    try:
        # Test if we can create a transformer (basic functionality test)
        transformer = get_transformer()
        return {"status": "ready", "endpoints": list(settings.WMTS_ENDPOINTS.keys())}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)