"""Sample geospatial data per hex to assign terrain types."""

from __future__ import annotations

import numpy as np
from shapely.geometry import Point

from wargame_cartographer.config.map_spec import BoundingBox
from wargame_cartographer.geo.elevation import ElevationProcessor
from wargame_cartographer.hex.grid import HexGrid
from wargame_cartographer.terrain.classifier import TerrainClassifier
from wargame_cartographer.terrain.types import TerrainType


class HexSampler:
    """Sample elevation, slope, and landcover to classify each hex."""

    def __init__(self):
        self.elevation_proc = ElevationProcessor()
        self.classifier = TerrainClassifier()

    def build_hex_terrain(
        self,
        grid: HexGrid,
        bbox: BoundingBox,
        vector_data=None,
    ) -> dict[tuple[int, int], dict]:
        """Build complete terrain data for every hex.

        Returns dict mapping (q, r) → {
            'terrain': TerrainType,
            'elevation_m': float,
            'slope_deg': float,
        }
        """
        # Get elevation data
        elevation, metadata = self.elevation_proc.get_elevation(bbox)
        slope = self.elevation_proc.compute_slope(elevation)

        # Build spatial indexes for vector features
        water_polys = None
        urban_points = set()
        forest_check = None

        if vector_data is not None:
            # Water: use lakes + ocean
            if hasattr(vector_data, 'lakes') and not vector_data.lakes.empty:
                from shapely.ops import unary_union
                try:
                    water_polys = unary_union(vector_data.lakes.geometry)
                except Exception:
                    pass

            # Cities: mark hexes containing cities as urban
            if hasattr(vector_data, 'cities') and not vector_data.cities.empty:
                for _, city in vector_data.cities.iterrows():
                    if hasattr(city.geometry, 'x'):
                        # Find which hex this city falls in
                        for (q, r), cell in grid.cells.items():
                            dx = cell.center_lon - city.geometry.x
                            dy = cell.center_lat - city.geometry.y
                            # Approximate: if within hex radius in degrees
                            if abs(dx) < 0.1 and abs(dy) < 0.1:
                                urban_points.add((q, r))
                                break

        result = {}
        for (q, r), cell in grid.cells.items():
            # Sample elevation at hex center
            elev = self.elevation_proc.sample_at_point(
                elevation, metadata, cell.center_lon, cell.center_lat
            )

            # Sample slope
            transform = metadata["transform"]
            col_idx, row_idx = ~transform * (cell.center_lon, cell.center_lat)
            row_idx, col_idx = int(round(row_idx)), int(round(col_idx))
            if 0 <= row_idx < slope.shape[0] and 0 <= col_idx < slope.shape[1]:
                slope_val = float(slope[row_idx, col_idx])
            else:
                slope_val = 0.0

            # Check water
            is_water = False
            if elev <= 0:
                is_water = True
            elif water_polys is not None:
                pt = Point(cell.center_lon, cell.center_lat)
                try:
                    is_water = water_polys.contains(pt)
                except Exception:
                    pass

            # Check urban
            is_urban = (q, r) in urban_points

            # Classify
            terrain = self.classifier.classify(
                elevation_m=elev,
                slope_deg=slope_val,
                is_water=is_water,
                is_urban=is_urban,
            )

            result[(q, r)] = {
                "terrain": terrain,
                "elevation_m": round(elev, 1),
                "slope_deg": round(slope_val, 1),
            }

        return result
