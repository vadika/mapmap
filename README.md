# MapMap Tile Proxy

A Python tile proxy that provides seamless access to WMTS services through standard z/x/y tile URLs. Supports both direct Web Mercator passthrough and coordinate system transformations for specialized mapping services.

## Features

- **Direct Web Mercator Support** - Access WMTS services without coordinate transformation
- **Coordinate System Transformations** - WGS84 ↔ LKS_LVM, Web Mercator, and other projections
- **Multiple WMTS Endpoints** - Configure multiple tile sources with different coordinate systems
- **FastAPI-based HTTP Server** - High-performance async tile serving
- **Intelligent Caching** - In-memory tile caching with TTL for optimal performance
- **Tile Bounds Validation** - Automatic validation of tile coordinates and coverage areas
- **RESTful API** - Discover available endpoints and coordinate systems
- **Docker Support** - Easy deployment with Docker Compose

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and adjust settings:

```bash
cp .env.example .env
```

## Running

### Local Development
```bash
python app.py
```

### Docker
```bash
docker-compose up
```

## Usage

### Standard Web Mercator Tiles

For most mapping applications, use the Web Mercator endpoint (no coordinate transformation):

```
http://localhost:8000/tiles/{z}/{x}/{y}?endpoint=latvia_webmercator
```

**Examples:**
```
http://localhost:8000/tiles/10/585/311?endpoint=latvia_webmercator
http://localhost:8000/tiles/7/72/39?endpoint=latvia_webmercator
```

### Coordinate-Transformed Tiles

For specialized applications requiring LKS_LVM coordinate system:

```
http://localhost:8000/tiles/{z}/{x}/{y}?endpoint=latvia
```

**Example:**
```
http://localhost:8000/tiles/12/2321/1264?endpoint=latvia
```

### Integration with Mapping Software

**Leaflet:**
```javascript
L.tileLayer('http://localhost:8000/tiles/{z}/{x}/{y}?endpoint=latvia_webmercator', {
    attribution: 'LVM Latvia'
}).addTo(map);
```

**QGIS:**
- Add XYZ Tiles connection
- URL: `http://localhost:8000/tiles/{z}/{x}/{y}?endpoint=latvia_webmercator`

**OpenLayers:**
```javascript
new ol.layer.Tile({
  source: new ol.source.XYZ({
    url: 'http://localhost:8000/tiles/{z}/{x}/{y}?endpoint=latvia_webmercator'
  })
})
```

**Mapbox/MapLibre:**
```javascript
map.addSource('lvm-tiles', {
  type: 'raster',
  tiles: ['http://localhost:8000/tiles/{z}/{x}/{y}?endpoint=latvia_webmercator'],
  tileSize: 256
})
```

## API Endpoints

- `GET /` - Service info with available endpoints and coordinate systems
- `GET /tiles/{z}/{x}/{y}?endpoint={name}` - Get map tile from specified endpoint
- `GET /bounds/{endpoint}` - Get valid WGS84 bounds for endpoint coverage
- `POST /cache/clear` - Clear all cached tiles and coordinate transformers

## Available Endpoints

### Pre-configured Endpoints

- **`latvia_webmercator`** - LVM Latvia tiles via Web Mercator (recommended)
  - Full Latvia coverage at zoom levels 1-18
  - Direct passthrough, no coordinate transformation
  - Compatible with all standard mapping software

- **`latvia`** - LVM Latvia tiles via LKS_LVM transformation
  - Limited coverage (eastern Latvia at lower zoom levels)
  - Uses coordinate transformation from Web Mercator to LKS_LVM
  - Suitable for specialized GIS applications requiring LKS_LVM projection

### Coordinate Systems Supported

- **WebMercatorQuad** - Standard Web Mercator (EPSG:3857) - direct passthrough
- **LKS_LVM** (EPSG:3059) - Latvia TM coordinate system with transformation
- **EPSG:3857** - Web Mercator projection
- **EPSG:4326** - WGS84 Geographic
- **EPSG:25832** - European UTM zone 32N

## Configuration

### Adding New WMTS Endpoints

Edit `config.py` to add new endpoints:

```python
WMTS_ENDPOINTS: Dict[str, Dict[str, Any]] = {
    "latvia_webmercator": {
        "url": "https://lvmgeoproxy01.lvm.lv/wmts_...",
        "layer": "public:Topo10DTM",
        "coordinate_system": "WebMercatorQuad",  # Direct passthrough
        "app_id": "lvmgeo.lvm.lv/",
        "style": "raster",
        "format": "image/vnd.jpeg-png8"
    },
    "latvia": {
        "url": "https://lvmgeoproxy01.lvm.lv/wmts_...",
        "layer": "public:Topo10DTM", 
        "coordinate_system": "LKS_LVM",  # With transformation
        "app_id": "lvmgeo.lvm.lv/",
        "style": "raster",
        "format": "image/vnd.jpeg-png8"
    }
}
```

### Choosing Between WebMercator and Transformed Endpoints

**Use WebMercator (`coordinate_system: "WebMercatorQuad"`) when:**
- Integrating with standard web mapping libraries (Leaflet, OpenLayers, Mapbox)
- You need full geographic coverage at all zoom levels
- Performance is important (no coordinate transformation overhead)
- Your WMTS service supports WebMercatorQuad tile matrix set

**Use Coordinate Transformation (e.g., `coordinate_system: "LKS_LVM"`) when:**
- You specifically need tiles in a local coordinate system
- Working with GIS software that requires specific projections
- The WMTS service only supports custom coordinate systems

## Testing

### Unit Tests
```bash
python -m pytest test_coordinates.py -v
```

### Integration Tests
```bash
python -m pytest test_integration.py -v
```

### Docker Tests
```bash
# Run all tests in Docker
docker build -f Dockerfile.test -t mapmap-test .
docker run --rm mapmap-test

# Run specific test files
docker run --rm mapmap-test python -m pytest test_coordinates.py -v
```

### Interactive Map Testing

1. Start the MapMap server:
```bash
docker run -p 8000:8000 mapmap
```

2. In another terminal, serve the test map:
```bash
python3 serve_test.py
```

3. Open your browser to http://localhost:3000/test_map.html

The test map allows you to:
- Test different server URLs and endpoints
- Visualize tile loading from the proxy
- Compare with OpenStreetMap reference tiles
- Monitor tile URLs and loading status