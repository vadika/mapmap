# Claude Context - MapMap Tile Proxy

## Project Overview
MapMap is a production-ready WMTS tile proxy that provides standard z/x/y tile access with coordinate transformation capabilities. Originally created to fix coordinate issues with Latvia's WMTS service.

## Current State
- **Repository**: git@github.com:vadika/mapmap.git
- **Status**: Production-ready, fully deployed
- **Last commit**: "Add automated VPS deployment with cloud-init"

## Key Problems Solved
1. **Initial Issue**: WMTS tiles showed only 4 tiles centered on Latvia's east border at zoom 7
2. **Root Cause**: Unnecessary coordinate transformation for WebMercatorQuad
3. **Solution**: Implemented direct passthrough for WebMercator while keeping LKS_LVM transformation

## Technical Implementation

### Core Features
- FastAPI-based tile proxy server
- Dual endpoint support: WebMercatorQuad (passthrough) and LKS_LVM (transformation)
- Production-ready with Docker, monitoring, and security
- Automatic coordinate transformation using pyproj
- In-memory caching with TTL
- Rate limiting and CORS protection

### Key Files
- `app.py` - Main FastAPI application with metrics and health checks
- `coordinates.py` - Coordinate transformation logic (fixed Y-axis inversion)
- `config.py` - Configuration management with environment variables
- `docker-compose.production.yml` - Production stack with Nginx and Redis
- `cloud-init.yaml` - Automated VPS deployment (includes user's SSH key)

### Important Code Fixes
1. **Y-coordinate inversion fix** (coordinates.py:264):
   ```python
   wmts_tile_row = int((origin_y - center_y) / wmts_tile_size_y)
   ```

2. **WebMercatorQuad passthrough** (coordinates.py:199-207):
   ```python
   if self.target_system_config.name == "WebMercatorQuad":
       return TransformedTileCoordinate(
           tile_matrix=str(tile.z),
           tile_col=tile.x,
           tile_row=tile.y,
           quadrant_x=0,
           quadrant_y=0
       )
   ```

## Production Deployment

### Docker Production Setup
- Multi-stage Dockerfile with non-root user
- Gunicorn with 4 workers
- Nginx reverse proxy with SSL support
- Redis for distributed caching (optional)
- Prometheus metrics and health checks

### Security Features
- Configurable CORS with domain restrictions
- Rate limiting (1000 req/hour default)
- Trusted host middleware
- Security headers via Nginx
- Non-root containers
- Fail2ban on VPS

### VPS Deployment
- **cloud-init.yaml** - Complete automated setup
- **User SSH key**: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJKQ+6iZKKw0eMJbuMTIyoZ9940ecNlac6dqCpy3eiCq
- Supports all major VPS providers
- Includes SSL setup script with Let's Encrypt

## Environment Configuration

### Key Settings
```env
DEFAULT_ENDPOINT=latvia_webmercator  # Use WebMercator by default
CACHE_SIZE=10000
CACHE_TTL=7200
ALLOWED_ORIGINS=https://yourdomain.com
RATE_LIMIT_ENABLED=true
ENABLE_METRICS=true
```

## API Endpoints
- `GET /tiles/{z}/{x}/{y}?endpoint=latvia_webmercator` - Tile access
- `GET /health` - Health check
- `GET /ready` - Readiness probe
- `GET /metrics` - Prometheus metrics
- `GET /bounds/{endpoint}` - Get valid bounds

## Testing
- **test_map.html** - Interactive Leaflet map for testing
- Default view centered on Latvia with proper bounds
- Dropdown to switch between endpoints

## Deployment Commands
```bash
# Local development
docker-compose up -d

# Production deployment
docker-compose -f docker-compose.production.yml up -d

# VPS deployment
./generate-cloud-init.sh
# Upload cloud-init.yaml to VPS provider
ssh mapmap@server-ip
sudo -u mapmap /home/mapmap/setup-ssl.sh yourdomain.com
```

## Repository Structure
```
mapmap/
├── app.py                  # Main FastAPI application
├── coordinates.py          # Coordinate transformation
├── config.py              # Configuration management
├── docker-compose.yml     # Development stack
├── docker-compose.production.yml  # Production stack
├── Dockerfile             # Development container
├── Dockerfile.production  # Production container
├── cloud-init.yaml       # VPS automation (refactored)
├── nginx.conf           # Nginx configuration
├── requirements.txt     # Python dependencies
├── scripts/             # Deployment and maintenance scripts
│   ├── init-server.sh   # Server initialization
│   ├── deploy-mapmap.sh # Deploy updates
│   ├── setup-ssl.sh     # SSL setup
│   └── monitor-mapmap.sh # Service monitoring
├── README.md           # User documentation
├── DEPLOYMENT.md       # Production deployment guide
├── VPS-DEPLOYMENT.md   # VPS-specific guide
├── CLAUDE.md          # Context for Claude sessions
└── test_map.html       # Interactive test interface
```

## Next Session Context
When continuing work on MapMap:
1. Default endpoint is `latvia_webmercator` (WebMercator passthrough)
2. Production deployment is fully automated with cloud-init
3. User's SSH key is already configured in cloud-init.yaml
4. All coordinate transformation issues have been resolved
5. Repository is pushed to GitHub at vadika/mapmap

## Potential Improvements
- Redis integration for distributed caching
- Kubernetes Helm chart
- CDN integration for global distribution
- Additional coordinate system support
- Tile pre-warming/pre-caching
- WebP format support for smaller tiles

## Important Notes
- WMTS server only covers eastern Latvia (25.1°E to 32.3°E)
- Tiles are 512x512 from WMTS, divided into 256x256 for Leaflet
- WebMercatorQuad needs no transformation (direct passthrough)
- LKS_LVM requires complex coordinate transformation
- Production setup includes monitoring, security, and auto-scaling