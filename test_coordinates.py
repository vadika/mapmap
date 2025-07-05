import pytest
from coordinates import TileCoordinate, CoordinateTransformer, BoundingBox, TransformedTileCoordinate
import math


class TestCoordinateTransformer:
    def setup_method(self):
        self.transformer_lks = CoordinateTransformer("LKS_LVM")
        self.transformer_mercator = CoordinateTransformer("EPSG:3857")
    
    def test_tile_to_bbox_wgs84(self):
        tile = TileCoordinate(z=10, x=580, y=316)
        bbox = self.transformer_lks.tile_to_bbox_wgs84(tile)
        
        # Verify longitude calculation
        n = 2.0 ** tile.z
        expected_min_lon = tile.x / n * 360.0 - 180.0
        expected_max_lon = (tile.x + 1) / n * 360.0 - 180.0
        
        assert bbox.min_lon == pytest.approx(expected_min_lon, rel=1e-6)
        assert bbox.max_lon == pytest.approx(expected_max_lon, rel=1e-6)
        
        # Verify latitude bounds are reasonable
        assert -90 < bbox.min_lat < bbox.max_lat < 90
        assert bbox.min_lat > 50  # Should be in northern hemisphere
        assert bbox.max_lat < 70  # But not too far north
    
    def test_transform_tile_lks_lvm(self):
        tile = TileCoordinate(z=12, x=2321, y=1264)
        
        result = self.transformer_lks.transform_tile(tile)
        
        assert isinstance(result, TransformedTileCoordinate)
        assert result.tile_matrix.startswith("LKS_LVM:")
        assert isinstance(result.tile_col, int)
        assert isinstance(result.tile_row, int)
    
    def test_transform_tile_web_mercator(self):
        tile = TileCoordinate(z=10, x=580, y=316)
        
        result = self.transformer_mercator.transform_tile(tile)
        
        assert isinstance(result, TransformedTileCoordinate)
        assert result.tile_matrix.startswith("EPSG:3857:")
        assert isinstance(result.tile_col, int)
        assert isinstance(result.tile_row, int)
    
    def test_is_valid_tile_valid_cases(self):
        valid_tiles = [
            TileCoordinate(z=10, x=580, y=316),
            TileCoordinate(z=12, x=2321, y=1264),
            TileCoordinate(z=8, x=145, y=79),
        ]
        
        for tile in valid_tiles:
            assert self.transformer_lks.is_valid_tile(tile) is True
    
    def test_is_valid_tile_invalid_cases(self):
        invalid_tiles = [
            TileCoordinate(z=-1, x=0, y=0),
            TileCoordinate(z=25, x=0, y=0),
            TileCoordinate(z=10, x=-1, y=0),
            TileCoordinate(z=10, x=0, y=-1),
            TileCoordinate(z=10, x=2000, y=0),
            TileCoordinate(z=10, x=0, y=2000),
            TileCoordinate(z=10, x=0, y=0),
            TileCoordinate(z=10, x=1000, y=1000),
        ]
        
        for tile in invalid_tiles:
            assert self.transformer_lks.is_valid_tile(tile) is False
    
    def test_zoom_level_mapping(self):
        test_cases = [
            (TileCoordinate(z=5, x=10, y=10), 7),
            (TileCoordinate(z=7, x=50, y=50), 7),
            (TileCoordinate(z=10, x=580, y=316), 10),
            (TileCoordinate(z=15, x=10000, y=10000), 14),
            (TileCoordinate(z=20, x=100000, y=100000), 14),
        ]
        
        for tile, expected_zoom in test_cases:
            result = self.transformer_lks.transform_tile(tile)
            actual_zoom = int(result.tile_matrix.split(":")[1])
            assert actual_zoom == expected_zoom
    
    def test_coordinate_consistency(self):
        tile1 = TileCoordinate(z=12, x=2321, y=1264)
        tile2 = TileCoordinate(z=12, x=2321, y=1264)
        
        result1 = self.transformer_lks.transform_tile(tile1)
        result2 = self.transformer_lks.transform_tile(tile2)
        
        assert result1.tile_matrix == result2.tile_matrix
        assert result1.tile_col == result2.tile_col
        assert result1.tile_row == result2.tile_row
    
    def test_coordinate_systems(self):
        from coordinate_systems import COORDINATE_SYSTEMS
        
        for name, config in COORDINATE_SYSTEMS.items():
            transformer = CoordinateTransformer(name)
            assert transformer.target_system_config.name == config.name
            assert transformer.target_system_config.epsg == config.epsg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])