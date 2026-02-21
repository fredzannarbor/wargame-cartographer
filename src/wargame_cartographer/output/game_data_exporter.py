"""Game data export: JSON hex terrain data for wargame mechanics."""

from __future__ import annotations

import json
from pathlib import Path

from wargame_cartographer.config.map_spec import MapSpec
from wargame_cartographer.hex.grid import HexGrid
from wargame_cartographer.terrain.types import TerrainType, TERRAIN_EFFECTS


def export_game_data(
    grid: HexGrid,
    hex_terrain: dict[tuple[int, int], dict],
    spec: MapSpec,
    path: Path,
) -> Path:
    """Export complete game data JSON for all hexes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    hexes = []
    for (q, r), cell in grid.cells.items():
        info = hex_terrain.get((q, r), {})
        terrain = info.get("terrain", TerrainType.CLEAR)
        if isinstance(terrain, TerrainType):
            terrain_name = terrain.value
        else:
            terrain_name = str(terrain)

        effects = TERRAIN_EFFECTS.get(terrain, TERRAIN_EFFECTS[TerrainType.CLEAR])

        hex_data = {
            "id": grid.wargame_number(q, r),
            "q": q,
            "r": r,
            "terrain": terrain_name,
            "movement_cost": effects.movement_cost,
            "defensive_modifier": effects.defensive_modifier,
            "blocks_los": effects.blocks_los,
            "elevation_m": info.get("elevation_m", 0),
            "slope_deg": info.get("slope_deg", 0),
            "center_lat": round(cell.center_lat, 6),
            "center_lon": round(cell.center_lon, 6),
        }
        hexes.append(hex_data)

    # Sort by hex number for readability
    hexes.sort(key=lambda h: h["id"])

    terrain_effects = {}
    for tt in TerrainType:
        effects = TERRAIN_EFFECTS[tt]
        terrain_effects[tt.value] = {
            "movement_cost": effects.movement_cost,
            "defensive_modifier": effects.defensive_modifier,
            "blocks_los": effects.blocks_los,
            "description": effects.description,
        }

    # Terrain distribution summary
    terrain_counts = {}
    for info in hex_terrain.values():
        t = info.get("terrain", TerrainType.CLEAR)
        name = t.value if isinstance(t, TerrainType) else str(t)
        terrain_counts[name] = terrain_counts.get(name, 0) + 1

    data = {
        "map_name": spec.name,
        "title": spec.title,
        "hex_size_km": spec.hex_size_km,
        "designer_style": spec.designer_style,
        "bbox": {
            "min_lon": spec.bbox.min_lon,
            "min_lat": spec.bbox.min_lat,
            "max_lon": spec.bbox.max_lon,
            "max_lat": spec.bbox.max_lat,
        },
        "hex_count": len(hexes),
        "terrain_distribution": terrain_counts,
        "terrain_effects": terrain_effects,
        "hexes": hexes,
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return path
