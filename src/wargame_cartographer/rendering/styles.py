"""Wargame designer styles: color palettes, fonts, line styles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from wargame_cartographer.terrain.types import TerrainType


@dataclass(frozen=True)
class WargameStyle:
    """Complete visual specification for a designer style."""

    name: str

    # Terrain colors (hex color codes)
    terrain_colors: dict[TerrainType, str]

    # Terrain hatch patterns (matplotlib hatch strings, None = solid fill)
    terrain_hatches: dict[TerrainType, str | None]

    # Grid
    grid_color: str = "#8B7355"
    grid_linewidth: float = 0.4
    grid_alpha: float = 0.7

    # Water
    water_color: str = "#7BB3D0"

    # Typography
    hex_number_fontsize: float = 4.5
    hex_number_color: str = "#555555"
    city_label_fontsize: float = 7.0
    city_label_color: str = "#222222"
    title_fontsize: float = 24.0

    # Symbols
    city_marker: str = "o"
    city_marker_size: float = 4.0
    city_marker_color: str = "#333333"
    port_marker: str = "^"
    port_marker_size: float = 5.0
    port_marker_color: str = "#0055AA"
    airfield_marker: str = "P"
    airfield_marker_size: float = 5.0
    airfield_marker_color: str = "#666666"

    # Cartouche
    border_color: str = "#333333"
    border_linewidth: float = 2.0
    legend_bg_color: str = "#FFFFFFDD"

    # Hillshade
    hillshade_alpha: float = 0.35
    hillshade_azimuth: float = 315.0
    hillshade_altitude: float = 45.0

    # River/road/coastline
    river_color: str = "#4A90D9"
    river_linewidth: float = 1.0
    coastline_color: str = "#333333"
    coastline_linewidth: float = 0.8
    road_color: str = "#8B4513"
    road_linewidth: float = 0.5


# --- Mark Simonitch Style ---
# Warm earth tones, muted greens, crisp thin grid lines
# Inspired by GMT games: Normandy '44, Ukraine '43, Ardennes '44

SIMONITCH = WargameStyle(
    name="simonitch",
    terrain_colors={
        TerrainType.CLEAR: "#F5EDD5",
        TerrainType.FOREST: "#4A7C3F",
        TerrainType.MOUNTAIN: "#9B8B78",
        TerrainType.ROUGH: "#C4AE87",
        TerrainType.WATER: "#7BB3D0",
        TerrainType.URBAN: "#D4A07A",
        TerrainType.MARSH: "#8FAF7F",
        TerrainType.DESERT: "#E8D5A0",
    },
    terrain_hatches={
        TerrainType.CLEAR: None,
        TerrainType.FOREST: "///",
        TerrainType.MOUNTAIN: "^^^",
        TerrainType.ROUGH: "...",
        TerrainType.WATER: None,
        TerrainType.URBAN: "xxx",
        TerrainType.MARSH: "---",
        TerrainType.DESERT: None,
    },
    grid_color="#8B7355",
    grid_linewidth=0.4,
    grid_alpha=0.7,
    water_color="#7BB3D0",
    hex_number_fontsize=4.5,
    hex_number_color="#6B5B45",
    river_color="#5B8FAF",
    river_linewidth=1.2,
    coastline_color="#4A3F35",
    hillshade_alpha=0.30,
)


# --- Redmond Simonsen Style (SPI Classic) ---
# High contrast, bold primary-adjacent colors, strong typography
# Inspired by SPI/Avalon Hill: PanzerBlitz, Squad Leader, War in Europe

SIMONSEN = WargameStyle(
    name="simonsen",
    terrain_colors={
        TerrainType.CLEAR: "#E8E0C0",
        TerrainType.FOREST: "#228B22",
        TerrainType.MOUNTAIN: "#8B6914",
        TerrainType.ROUGH: "#CD853F",
        TerrainType.WATER: "#4169E1",
        TerrainType.URBAN: "#E8E0C0",  # Light base; street grid pattern overlays
        TerrainType.MARSH: "#2E8B57",
        TerrainType.DESERT: "#F4D03F",
    },
    terrain_hatches={
        TerrainType.CLEAR: None,
        TerrainType.FOREST: "///",
        TerrainType.MOUNTAIN: None,
        TerrainType.ROUGH: "...",
        TerrainType.WATER: None,
        TerrainType.URBAN: "xxx",
        TerrainType.MARSH: "|||",
        TerrainType.DESERT: None,
    },
    grid_color="#000000",
    grid_linewidth=0.6,
    grid_alpha=0.8,
    water_color="#4169E1",
    hex_number_fontsize=5.0,
    hex_number_color="#000000",
    city_marker_color="#B22222",
    city_label_color="#000000",
    coastline_color="#000000",
    coastline_linewidth=1.2,
    river_color="#4169E1",
    hillshade_alpha=0.25,
    border_linewidth=3.0,
)


# --- Charles Kibler Style ---
# Painterly, saturated, strong outlines, organic feel
# Inspired by Avalon Hill: Third Reich, Breakout: Normandy

KIBLER = WargameStyle(
    name="kibler",
    terrain_colors={
        TerrainType.CLEAR: "#F0E6C8",
        TerrainType.FOREST: "#2D5A27",
        TerrainType.MOUNTAIN: "#6B4E3D",
        TerrainType.ROUGH: "#A0855A",
        TerrainType.WATER: "#3A6F9F",
        TerrainType.URBAN: "#C07040",
        TerrainType.MARSH: "#5A7A4A",
        TerrainType.DESERT: "#D4BC78",
    },
    terrain_hatches={
        TerrainType.CLEAR: None,
        TerrainType.FOREST: "\\\\\\",
        TerrainType.MOUNTAIN: "ooo",
        TerrainType.ROUGH: None,
        TerrainType.WATER: None,
        TerrainType.URBAN: "+++",
        TerrainType.MARSH: "---",
        TerrainType.DESERT: None,
    },
    grid_color="#4A3525",
    grid_linewidth=0.5,
    grid_alpha=0.75,
    water_color="#3A6F9F",
    hex_number_fontsize=4.0,
    hex_number_color="#4A3525",
    river_color="#3A6F9F",
    river_linewidth=1.5,
    coastline_color="#2A1A0A",
    coastline_linewidth=1.0,
    hillshade_alpha=0.40,
    border_linewidth=2.5,
)


def scale_style(base: WargameStyle, font_scale: float = 1.0, name: str | None = None) -> WargameStyle:
    """Create a scaled copy of a style with larger/smaller fonts and markers."""
    return WargameStyle(
        name=name or base.name,
        terrain_colors=base.terrain_colors,
        terrain_hatches=base.terrain_hatches,
        grid_color=base.grid_color,
        grid_linewidth=base.grid_linewidth * font_scale,
        grid_alpha=base.grid_alpha,
        water_color=base.water_color,
        hex_number_fontsize=base.hex_number_fontsize * font_scale,
        hex_number_color=base.hex_number_color,
        city_label_fontsize=base.city_label_fontsize * font_scale,
        city_label_color=base.city_label_color,
        title_fontsize=base.title_fontsize * font_scale,
        city_marker=base.city_marker,
        city_marker_size=base.city_marker_size * font_scale,
        city_marker_color=base.city_marker_color,
        port_marker=base.port_marker,
        port_marker_size=base.port_marker_size * font_scale,
        port_marker_color=base.port_marker_color,
        airfield_marker=base.airfield_marker,
        airfield_marker_size=base.airfield_marker_size * font_scale,
        airfield_marker_color=base.airfield_marker_color,
        border_color=base.border_color,
        border_linewidth=base.border_linewidth,
        legend_bg_color=base.legend_bg_color,
        hillshade_alpha=base.hillshade_alpha,
        hillshade_azimuth=base.hillshade_azimuth,
        hillshade_altitude=base.hillshade_altitude,
        river_color=base.river_color,
        river_linewidth=base.river_linewidth,
        coastline_color=base.coastline_color,
        coastline_linewidth=base.coastline_linewidth,
        road_color=base.road_color,
        road_linewidth=base.road_linewidth,
    )


STYLES: dict[str, WargameStyle] = {
    "simonitch": SIMONITCH,
    "simonsen": SIMONSEN,
    "kibler": KIBLER,
}


def get_style(name: str, font_scale: float = 1.0) -> WargameStyle:
    """Get a designer style by name, optionally scaled."""
    if name not in STYLES:
        raise ValueError(f"Unknown style: {name}. Available: {list(STYLES.keys())}")
    style = STYLES[name]
    if font_scale != 1.0:
        style = scale_style(style, font_scale)
    return style
