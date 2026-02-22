"""Map specification and bounding box models."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator
from shapely.geometry import box as shapely_box

logger = logging.getLogger(__name__)

# Standard wargame map sheet sizes (width_inches, height_inches) in landscape
MAP_SHEET_SIZES: dict[str, tuple[float, float]] = {
    "11x17": (17.0, 11.0),
    "17x22": (22.0, 17.0),
    "22x34": (34.0, 22.0),
    "34x44": (44.0, 34.0),
}

INCHES_TO_MM = 25.4


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
    unit_type: str = "infantry"
    size: str = "division"
    hex_id: str = ""
    side: str = "blue"
    combat_factor: int = 0
    movement_factor: int = 0


class MovementPlan(BaseModel):
    """A movement arrow from one hex to another."""

    unit_designation: str
    hex_path: list[str]
    side: str = "blue"


class OOBUnit(BaseModel):
    """A unit entry in an Order of Battle."""

    designation: str
    unit_type: str = "infantry"
    size: str = "division"
    combat_factor: int = 0
    movement_factor: int = 0
    setup_hex: str = ""
    strength: str = ""


class OOBEntry(BaseModel):
    """An Order of Battle formation entry."""

    side: str
    formation: str
    units: list[OOBUnit] = Field(default_factory=list)
    setup_turn: int = 1
    setup_zone: str = ""
    notes: str = ""


class ModulePanel(BaseModel):
    """A game module panel (CRT, TEC, etc.)."""

    panel_type: Literal["crt", "tec", "sequence_of_play", "custom"] = "crt"
    title: str = ""
    custom_data: dict | None = None


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

    # Standard map sheet sizes — overrides output_width_mm/output_height_mm when set
    map_size: str | None = None
    map_sheets: int = 1
    map_orientation: Literal["portrait", "landscape"] = "landscape"

    crs: str | None = None
    font_scale: float = 1.0

    # Hex readability
    min_hex_px: int = 40

    # Counter-to-hex sizing
    counter_hex_ratio: float = 0.65

    show_elevation_shading: bool = True
    show_rivers: bool = True
    show_roads: bool = False
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

    # Side panels
    show_oob_panel: bool = False
    oob_panel_position: Literal["right", "left", "bottom"] = "right"
    oob_panel_width_ratio: float = 0.25
    oob_data: list[OOBEntry] | None = None
    oob_commentary: list[str] | None = None

    show_module_panels: bool = False
    module_panel_position: Literal["bottom", "right", "left"] = "bottom"
    module_panels: list[ModulePanel] | None = None

    output_dir: Path = Field(default_factory=lambda: Path("./output"))
    output_formats: list[Literal["png", "pdf", "html", "json"]] = Field(
        default_factory=lambda: ["png", "html", "json"]
    )

    @model_validator(mode="after")
    def _resolve_map_size(self) -> MapSpec:
        """If map_size is set, compute output dimensions from standard sheet sizes."""
        if self.map_size is None:
            return self

        size_key = self.map_size.lower().replace(" ", "")
        if size_key in MAP_SHEET_SIZES:
            w_in, h_in = MAP_SHEET_SIZES[size_key]
        else:
            try:
                parts = size_key.split("x")
                w_in, h_in = float(parts[0]), float(parts[1])
            except (ValueError, IndexError):
                logger.warning(
                    "Unknown map_size '%s'. Valid: %s or 'WxH' in inches.",
                    self.map_size,
                    list(MAP_SHEET_SIZES.keys()),
                )
                return self

        if self.map_orientation == "portrait":
            w_in, h_in = min(w_in, h_in), max(w_in, h_in)
        else:
            w_in, h_in = max(w_in, h_in), min(w_in, h_in)

        if self.map_sheets == 2:
            w_in *= 2
        elif self.map_sheets == 4:
            w_in *= 2
            h_in *= 2

        self.output_width_mm = w_in * INCHES_TO_MM
        self.output_height_mm = h_in * INCHES_TO_MM
        return self

    @classmethod
    def from_yaml(cls, path: str | Path) -> MapSpec:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        with open(path, "w") as f:
            yaml.dump(self.model_dump(mode="json"), f, default_flow_style=False)
