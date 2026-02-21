"""Map specification and bounding box models."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from shapely.geometry import box as shapely_box


class BoundingBox(BaseModel):
    """Geographic bounding box in WGS84 (lon/lat)."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @classmethod
    def from_center(
        cls, lat: float, lon: float, width_km: float, height_km: float
    ) -> BoundingBox:
        """Create bbox from center point and dimensions in km."""
        # Approximate degrees per km
        km_per_deg_lat = 111.32
        km_per_deg_lon = 111.32 * math.cos(math.radians(lat))
        half_w = (width_km / 2.0) / km_per_deg_lon
        half_h = (height_km / 2.0) / km_per_deg_lat
        return cls(
            min_lon=lon - half_w,
            min_lat=lat - half_h,
            max_lon=lon + half_w,
            max_lat=lat + half_h,
        )

    def center(self) -> tuple[float, float]:
        """Return (lat, lon) center."""
        return (
            (self.min_lat + self.max_lat) / 2.0,
            (self.min_lon + self.max_lon) / 2.0,
        )

    def width_km(self) -> float:
        center_lat = (self.min_lat + self.max_lat) / 2.0
        km_per_deg_lon = 111.32 * math.cos(math.radians(center_lat))
        return (self.max_lon - self.min_lon) * km_per_deg_lon

    def height_km(self) -> float:
        return (self.max_lat - self.min_lat) * 111.32

    def to_shapely(self):
        return shapely_box(self.min_lon, self.min_lat, self.max_lon, self.max_lat)

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return (min_lon, min_lat, max_lon, max_lat)."""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)


class NATOUnit(BaseModel):
    """A NATO-style unit counter for deployment overlay."""

    designation: str
    unit_type: str = "infantry"  # infantry, armor, artillery, etc.
    size: str = "division"  # squad, platoon, company, battalion, regiment, brigade, division, corps, army
    hex_id: str = ""  # Wargame hex number e.g. "2013"
    side: str = "blue"  # blue (friendly) or red (enemy)
    combat_factor: int = 0
    movement_factor: int = 0


class MovementPlan(BaseModel):
    """A movement arrow from one hex to another."""

    unit_designation: str
    hex_path: list[str]  # List of hex IDs
    side: str = "blue"


class MapSpec(BaseModel):
    """Complete specification for generating a wargame map."""

    name: str = "Untitled Map"
    title: str = ""
    subtitle: str = ""
    scenario: str = ""

    bbox: BoundingBox

    map_style: Literal["hex", "area", "point_to_point"] = "hex"
    designer_style: Literal["simonitch", "simonsen", "kibler"] = "simonitch"

    hex_size_km: float = 10.0
    output_width_mm: float = 500.0
    output_height_mm: float = 700.0
    dpi: int = 150

    crs: str | None = None  # Auto-selected if None
    font_scale: float = 1.0  # Multiply all font sizes by this factor

    show_elevation_shading: bool = True
    show_rivers: bool = True
    show_roads: bool = False  # Can be noisy at strategic scale
    show_railways: bool = False
    show_cities: bool = True
    show_ports: bool = True
    show_airfields: bool = False
    show_hex_numbers: bool = True
    show_legend: bool = True
    show_scale_bar: bool = True
    show_compass: bool = True

    nato_units: list[NATOUnit] | None = None
    movement_plans: list[MovementPlan] | None = None

    output_dir: Path = Field(default_factory=lambda: Path("./output"))
    output_formats: list[Literal["png", "pdf", "html", "json"]] = Field(
        default_factory=lambda: ["png", "html", "json"]
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> MapSpec:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        with open(path, "w") as f:
            yaml.dump(self.model_dump(mode="json"), f, default_flow_style=False)
