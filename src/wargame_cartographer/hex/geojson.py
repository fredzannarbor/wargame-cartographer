"""Export hex grid as GeoJSON for Folium interactive maps."""

from __future__ import annotations

import json
from pathlib import Path

from wargame_cartographer.hex.grid import HexGrid
from wargame_cartographer.terrain.types import TerrainType, TERRAIN_EFFECTS


def hex_grid_to_geojson(
    grid: HexGrid,
    hex_terrain: dict[tuple[int, int], dict],
) -> dict:
    """Convert hex grid + terrain data to a GeoJSON FeatureCollection."""
    features = []

    for (q, r), cell in grid.cells.items():
        # Get hex polygon vertices in geographic coords
        verts_proj = grid.hex_vertices(q, r)
        # Transform back to lon/lat
        verts_geo = []
        for vx, vy in verts_proj:
            lon, lat = grid._to_geo.transform(vx, vy)
            verts_geo.append([lon, lat])
        # Close the ring
        verts_geo.append(verts_geo[0])

        terrain_info = hex_terrain.get((q, r), {})
        terrain_type = terrain_info.get("terrain", TerrainType.CLEAR)
        if isinstance(terrain_type, TerrainType):
            terrain_name = terrain_type.value
        else:
            terrain_name = str(terrain_type)

        effects = TERRAIN_EFFECTS.get(terrain_type, TERRAIN_EFFECTS[TerrainType.CLEAR])

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [verts_geo],
            },
            "properties": {
                "hex_number": grid.wargame_number(q, r),
                "q": q,
                "r": r,
                "terrain": terrain_name,
                "elevation_m": terrain_info.get("elevation_m", 0),
                "slope_deg": terrain_info.get("slope_deg", 0),
                "movement_cost": effects.movement_cost,
                "defensive_modifier": effects.defensive_modifier,
                "center_lon": cell.center_lon,
                "center_lat": cell.center_lat,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }
