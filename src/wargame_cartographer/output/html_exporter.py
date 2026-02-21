"""Interactive HTML output via Folium/Leaflet."""

from __future__ import annotations

import json
from pathlib import Path

import folium

from wargame_cartographer.config.map_spec import MapSpec
from wargame_cartographer.hex.grid import HexGrid
from wargame_cartographer.hex.geojson import hex_grid_to_geojson
from wargame_cartographer.rendering.styles import get_style
from wargame_cartographer.terrain.types import TerrainType


def export_html(
    grid: HexGrid,
    hex_terrain: dict[tuple[int, int], dict],
    spec: MapSpec,
    path: Path,
) -> Path:
    """Export interactive HTML map with hex grid overlay."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    center_lat, center_lon = spec.bbox.center()
    style = get_style(spec.designer_style)

    # Determine zoom level from bbox extent
    zoom = _zoom_for_extent(spec.bbox.width_km())

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles="CartoDB Positron",
    )

    # Build GeoJSON
    geojson_data = hex_grid_to_geojson(grid, hex_terrain)

    # Color lookup for style function
    terrain_colors = {t.value: c for t, c in style.terrain_colors.items()}

    def style_function(feature):
        terrain = feature["properties"]["terrain"]
        color = terrain_colors.get(terrain, "#F5EDD5")
        return {
            "fillColor": color,
            "color": style.grid_color,
            "weight": 0.8,
            "fillOpacity": 0.7,
        }

    # Add hex grid as GeoJSON
    tooltip = folium.GeoJsonTooltip(
        fields=["hex_number", "terrain", "movement_cost", "defensive_modifier", "elevation_m"],
        aliases=["Hex", "Terrain", "MP Cost", "Defense Mod", "Elevation (m)"],
        localize=True,
    )

    folium.GeoJson(
        geojson_data,
        name="Hex Grid",
        style_function=style_function,
        tooltip=tooltip,
    ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Title
    if spec.title:
        title_html = f"""
        <div style="position:fixed;top:10px;left:60px;z-index:1000;
                    background:white;padding:8px 16px;border-radius:4px;
                    box-shadow:0 2px 6px rgba(0,0,0,0.3);
                    font-family:sans-serif;">
            <strong style="font-size:16px;">{spec.title}</strong>
            {f'<br><span style="font-size:12px;color:#666;">{spec.subtitle}</span>' if spec.subtitle else ''}
        </div>
        """
        m.get_root().html.add_child(folium.Element(title_html))

    m.save(str(path))
    return path


def _zoom_for_extent(width_km: float) -> int:
    """Estimate Leaflet zoom level from map extent."""
    if width_km < 10:
        return 13
    elif width_km < 50:
        return 11
    elif width_km < 200:
        return 9
    elif width_km < 500:
        return 7
    elif width_km < 2000:
        return 5
    else:
        return 3
