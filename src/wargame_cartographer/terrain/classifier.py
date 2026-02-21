"""Terrain classification: elevation + slope + landcover → TerrainType."""

from __future__ import annotations

import hashlib

from wargame_cartographer.terrain.types import TerrainType


class TerrainClassifier:
    """Classify terrain type from geographic data.

    For land hexes without explicit landcover data, uses a deterministic
    pseudo-random assignment based on hex position + elevation to create
    realistic terrain variety (forests, rough terrain, etc.).
    """

    def __init__(
        self,
        mountain_slope_threshold: float = 20.0,
        rough_slope_threshold: float = 8.0,
        mountain_elevation_threshold: float = 800.0,
    ):
        self.mountain_slope = mountain_slope_threshold
        self.rough_slope = rough_slope_threshold
        self.mountain_elevation = mountain_elevation_threshold

    def classify(
        self,
        elevation_m: float,
        slope_deg: float,
        is_water: bool = False,
        is_urban: bool = False,
        is_forest: bool = False,
        is_marsh: bool = False,
        lat: float = 0.0,
        lon: float = 0.0,
    ) -> TerrainType:
        """Classify a single hex."""
        if is_water:
            return TerrainType.WATER
        if is_urban:
            return TerrainType.URBAN
        if is_forest:
            return TerrainType.FOREST
        if is_marsh:
            return TerrainType.MARSH

        # High mountains
        if slope_deg > self.mountain_slope:
            return TerrainType.MOUNTAIN
        if elevation_m > self.mountain_elevation and slope_deg > 5.0:
            return TerrainType.MOUNTAIN

        # Rough terrain
        if slope_deg > self.rough_slope:
            return TerrainType.ROUGH

        # For lower terrain without explicit landcover, use deterministic
        # pseudo-random terrain based on location + elevation to create
        # realistic variety (European terrain is ~40% forest, ~15% rough)
        terrain_hash = self._terrain_hash(lat, lon, elevation_m)

        # Higher elevation = more likely to be forest or rough
        if elevation_m > 400:
            if terrain_hash < 0.5:
                return TerrainType.FOREST
            elif terrain_hash < 0.7:
                return TerrainType.ROUGH
            return TerrainType.CLEAR

        if elevation_m > 150:
            if terrain_hash < 0.35:
                return TerrainType.FOREST
            elif terrain_hash < 0.50:
                return TerrainType.ROUGH
            return TerrainType.CLEAR

        # Low elevation
        if terrain_hash < 0.20:
            return TerrainType.FOREST
        if terrain_hash < 0.30:
            return TerrainType.ROUGH
        # Very low + low hash → possible marsh
        if elevation_m < 20 and terrain_hash > 0.90:
            return TerrainType.MARSH

        return TerrainType.CLEAR

    def _terrain_hash(self, lat: float, lon: float, elev: float) -> float:
        """Deterministic pseudo-random value 0-1 based on location.

        This creates spatially coherent terrain patterns — nearby hexes
        tend to have similar terrain because the hash changes smoothly.
        Uses quantized coordinates so adjacent hexes get related values.
        """
        # Quantize to ~5km grid for spatial coherence
        qlat = round(lat * 20) / 20.0
        qlon = round(lon * 20) / 20.0
        key = f"{qlat:.2f},{qlon:.2f},{round(elev / 50) * 50}"
        h = hashlib.md5(key.encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF
