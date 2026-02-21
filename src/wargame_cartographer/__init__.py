"""Wargame Cartographer — Generate playable wargame-style maps at any scale."""

from wargame_cartographer.config.map_spec import MapSpec, BoundingBox
from wargame_cartographer.hex.grid import HexGrid
from wargame_cartographer.terrain.types import TerrainType

__all__ = ["MapSpec", "BoundingBox", "HexGrid", "TerrainType"]
__version__ = "0.1.0"
