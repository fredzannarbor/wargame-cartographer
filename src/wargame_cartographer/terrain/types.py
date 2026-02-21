"""Wargame terrain types and their game-mechanical properties."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TerrainType(Enum):
    WATER = "water"
    CLEAR = "clear"
    ROUGH = "rough"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    MARSH = "marsh"
    DESERT = "desert"
    URBAN = "urban"


@dataclass(frozen=True)
class TerrainData:
    """Game-mechanical properties of a terrain type."""

    movement_cost: int  # Movement points to enter
    defensive_modifier: int  # Combat modifier for defender
    blocks_los: bool  # Blocks line of sight
    description: str


TERRAIN_EFFECTS: dict[TerrainType, TerrainData] = {
    TerrainType.WATER: TerrainData(
        movement_cost=99, defensive_modifier=0, blocks_los=False,
        description="Impassable except by naval/amphibious movement",
    ),
    TerrainType.CLEAR: TerrainData(
        movement_cost=1, defensive_modifier=0, blocks_los=False,
        description="Open terrain, no obstacles",
    ),
    TerrainType.ROUGH: TerrainData(
        movement_cost=2, defensive_modifier=1, blocks_los=False,
        description="Uneven ground, scrub, broken terrain",
    ),
    TerrainType.FOREST: TerrainData(
        movement_cost=2, defensive_modifier=1, blocks_los=True,
        description="Wooded terrain, limited visibility",
    ),
    TerrainType.MOUNTAIN: TerrainData(
        movement_cost=3, defensive_modifier=2, blocks_los=True,
        description="High elevation, steep slopes",
    ),
    TerrainType.MARSH: TerrainData(
        movement_cost=3, defensive_modifier=0, blocks_los=False,
        description="Wetlands, bogs, swamps",
    ),
    TerrainType.DESERT: TerrainData(
        movement_cost=2, defensive_modifier=0, blocks_los=False,
        description="Arid terrain, sand, limited water",
    ),
    TerrainType.URBAN: TerrainData(
        movement_cost=1, defensive_modifier=2, blocks_los=True,
        description="Cities, towns, built-up areas",
    ),
}
