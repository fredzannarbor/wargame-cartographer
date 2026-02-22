"""Pydantic models for scenario analysis — the contract between Claude Code and the CLI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GeographicPoint(BaseModel):
    """A point of interest relevant to the scenario."""

    name: str
    lat: float
    lon: float
    category: Literal[
        "city",
        "port",
        "airfield",
        "river_crossing",
        "ridge",
        "pass",
        "fortification",
        "headquarters",
        "other",
    ] = "other"
    significance: str = ""


class ForceEntry(BaseModel):
    """A unit in the order of battle."""

    side: Literal["blue", "red"]
    designation: str
    unit_type: Literal[
        "infantry",
        "cavalry",
        "armor",
        "artillery",
        "naval",
        "air",
        "headquarters",
    ] = "infantry"
    size: Literal[
        "army_group",
        "army",
        "corps",
        "division",
        "brigade",
        "regiment",
        "battalion",
    ] = "division"
    approximate_location: str = ""
    strength: str = ""
    is_off_map: bool = False


class ScenarioAnalysis(BaseModel):
    """Complete scenario analysis produced by Claude Code, consumed by the CLI."""

    scenario_name: str
    date_range: str = ""
    theater: str = ""

    blue_side_name: str = "Blue"
    red_side_name: str = "Red"
    blue_objectives: list[str] = Field(default_factory=list)
    red_objectives: list[str] = Field(default_factory=list)

    # Geographic framing — center + extent is more natural than raw bbox
    center_lat: float
    center_lon: float
    area_width_km: float
    area_height_km: float
    margin_percent: float = 15.0

    # Scale
    recommended_scale: Literal["tactical", "operational", "strategic"] = "operational"
    recommended_hex_size_km: float = 10.0
    scale_rationale: str = ""

    # Key terrain and forces
    key_terrain: list[GeographicPoint] = Field(default_factory=list)
    forces: list[ForceEntry] = Field(default_factory=list)

    # Feature toggles
    show_rivers: bool = True
    show_roads: bool = False
    show_railways: bool = False
    show_ports: bool = False
    show_airfields: bool = False

    # Rationale
    bbox_rationale: str = ""
    designer_style_recommendation: Literal[
        "simonitch", "simonsen", "kibler"
    ] = "simonitch"
    style_rationale: str = ""
