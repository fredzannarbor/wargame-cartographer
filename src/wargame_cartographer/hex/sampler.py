"""Sample geospatial data per hex to assign terrain types."""

from __future__ import annotations

import numpy as np
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.prepared import prep

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
        """Build complete terrain data for every hex."""
        elevation, metadata = self.elevation_proc.get_elevation(bbox)
        slope = self.elevation_proc.compute_slope(elevation)

        # Build spatial indexes for fast point-in-polygon tests
        land_prep = None
        lake_prep = None
        city_coords = {}

        if vector_data is not None:
            if hasattr(vector_data, 'land') and not vector_data.land.empty:
                try:
                    land_union = unary_union(vector_data.land.geometry)
                    land_prep = prep(land_union)
                except Exception:
                    pass

            if hasattr(vector_data, 'lakes') and not vector_data.lakes.empty:
                try:
                    lake_union = unary_union(vector_data.lakes.geometry)
                    lake_prep = prep(lake_union)
                except Exception:
                    pass

            if hasattr(vector_data, 'cities') and not vector_data.cities.empty:
                for _, city in vector_data.cities.iterrows():
                    if hasattr(city.geometry, 'x'):
                        name = ""
                        if hasattr(city, "get"):
                            name = city.get("name", "")
                        city_coords[(city.geometry.x, city.geometry.y)] = name

        # Find urban hexes (hexes containing or very near a city)
        urban_hexes = set()
        if city_coords:
            for (q, r), cell in grid.cells.items():
                for (cx, cy), cname in city_coords.items():
                    dlat = abs(cell.center_lat - cy)
                    dlon = abs(cell.center_lon - cx)
                    threshold = grid.hex_radius_m / 111320.0 * 0.8
                    cos_lat = max(0.5, abs(np.cos(np.radians(cell.center_lat))))
                    if dlat < threshold and dlon < threshold / cos_lat:
                        urban_hexes.add((q, r))
                        break

        result = {}
        for (q, r), cell in grid.cells.items():
            pt = Point(cell.center_lon, cell.center_lat)

            # Water: not on land polygon, or in a lake
            is_water = False
            if land_prep is not None:
                is_water = not land_prep.contains(pt)
            else:
                elev = self.elevation_proc.sample_at_point(
                    elevation, metadata, cell.center_lon, cell.center_lat
                )
                is_water = elev <= 0

            if not is_water and lake_prep is not None:
                if lake_prep.contains(pt):
                    is_water = True

            # Sample elevation
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

            is_urban = (q, r) in urban_hexes

            terrain = self.classifier.classify(
                elevation_m=max(0, elev) if not is_water else elev,
                slope_deg=slope_val,
                is_water=is_water,
                is_urban=is_urban,
                lat=cell.center_lat,
                lon=cell.center_lon,
            )

            result[(q, r)] = {
                "terrain": terrain,
                "elevation_m": round(elev, 1),
                "slope_deg": round(slope_val, 1),
            }

        return result
