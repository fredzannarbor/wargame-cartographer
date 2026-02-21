"""Terrain classification: elevation + slope + landcover → TerrainType."""

from __future__ import annotations

import numpy as np

from wargame_cartographer.terrain.types import TerrainType


class TerrainClassifier:
    """Classify terrain type from geographic data.

    Decision tree:
    1. Water body overlap → WATER
    2. Urban area overlap → URBAN
    3. Forest/woodland overlap → FOREST
    4. Wetland overlap → MARSH
    5. Slope > 25 degrees → MOUNTAIN
    6. Slope > 10 degrees → ROUGH
    7. Elevation > 1500m and slope > 8 → MOUNTAIN
    8. Arid regions (low precip proxy: elev < 500, slope < 5) → heuristic
    9. Default → CLEAR
    """

    def __init__(
        self,
        mountain_slope_threshold: float = 25.0,
        rough_slope_threshold: float = 10.0,
        mountain_elevation_threshold: float = 1500.0,
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
        if slope_deg > self.mountain_slope:
            return TerrainType.MOUNTAIN
        if elevation_m > self.mountain_elevation and slope_deg > 8.0:
            return TerrainType.MOUNTAIN
        if slope_deg > self.rough_slope:
            return TerrainType.ROUGH
        return TerrainType.CLEAR
