"""Cartouche layer: title, legend, scale bar, compass rose, coordinate ticks."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon as MplPolygon
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
import numpy as np

from wargame_cartographer.rendering.renderer import RenderContext
from wargame_cartographer.terrain.types import TerrainType, TERRAIN_EFFECTS


def render_cartouche_layer(
    ax: plt.Axes,
    context: RenderContext,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
):
    """Draw title, legend, scale bar, and compass rose."""
    style = context.style
    spec = context.spec
    width = x_max - x_min
    height = y_max - y_min

    # Title block (top-left)
    if spec.title:
        _draw_title_block(ax, context, x_min, y_max, width, height)

    # Scale bar and hex metrics are now inside the title block

    # Terrain legend (bottom-right)
    if spec.show_legend:
        _draw_legend(ax, context, x_min, x_max, y_min, y_max)

    # Compass rose (top-right)
    if spec.show_compass:
        _draw_compass_rose(ax, x_max - width * 0.06, y_max - height * 0.06, height * 0.04, style.typography)

    # Coordinate ticks along border
    _draw_coord_ticks(ax, context, x_min, x_max, y_min, y_max)

    # Map border
    border_rect = Rectangle(
        (x_min, y_min), width, height,
        linewidth=style.border_linewidth,
        edgecolor=style.border_color,
        facecolor="none",
        zorder=11,
    )
    ax.add_patch(border_rect)


def _draw_title_block(ax, context, x_min, y_max, width, height):
    """Draw title, subtitle, scenario, and scale info in one block."""
    style = context.style
    spec = context.spec
    typo = style.typography

    ts_title = typo.title
    ts_subtitle = typo.subtitle
    ts_scenario = typo.scenario
    ts_scale_label = typo.scale_label
    ts_scale_text = typo.scale_text

    line_gap = height * 0.015
    title_h = height * 0.025
    subtitle_h = height * 0.015
    scenario_h = height * 0.012
    scale_section_h = height * 0.045
    padding = height * 0.015

    # Compute total box height
    box_h = padding
    box_h += title_h
    if spec.subtitle:
        box_h += line_gap + subtitle_h
    if spec.scenario:
        box_h += line_gap + scenario_h
    if spec.show_scale_bar:
        box_h += line_gap + scale_section_h
    box_h += padding

    box_w = width * 0.32
    box_x = x_min + width * 0.02
    box_y = y_max - height * 0.02 - box_h

    bg = FancyBboxPatch(
        (box_x, box_y), box_w, box_h,
        boxstyle="round,pad=0.005",
        facecolor="white",
        edgecolor="#666666",
        linewidth=0.8,
        alpha=0.9,
        zorder=9.5,
    )
    ax.add_patch(bg)

    text_x = box_x + box_w * 0.05
    cursor_y = box_y + box_h - padding

    ax.text(
        text_x, cursor_y,
        spec.title.upper(),
        **ts_title.mpl_kwargs(),
        va="top",
        ha="left",
        zorder=10,
    )
    cursor_y -= title_h

    if spec.subtitle:
        cursor_y -= line_gap
        ax.text(
            text_x, cursor_y,
            spec.subtitle,
            **ts_subtitle.mpl_kwargs(),
            va="top",
            ha="left",
            zorder=10,
        )
        cursor_y -= subtitle_h

    if spec.scenario:
        cursor_y -= line_gap
        ax.text(
            text_x, cursor_y,
            spec.scenario,
            **ts_scenario.mpl_kwargs(),
            va="top",
            ha="left",
            zorder=10,
        )
        cursor_y -= scenario_h

    # Scale info section inside title block
    if spec.show_scale_bar:
        cursor_y -= line_gap
        # Separator line
        ax.plot(
            [box_x + box_w * 0.03, box_x + box_w * 0.97],
            [cursor_y, cursor_y],
            color="#AAAAAA", linewidth=0.5, zorder=10,
        )
        cursor_y -= height * 0.005

        # Scale bar (alternating black/white segments)
        hex_km = spec.hex_size_km
        candidates = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        target_km = hex_km * 3
        scale_km = min(candidates, key=lambda c: abs(c - target_km))
        scale_m = scale_km * 1000.0
        bar_w_data = min(scale_m, box_w * 0.85)
        n_segments = 4
        seg_len = bar_w_data / n_segments
        bar_x = text_x
        bar_y = cursor_y - height * 0.006
        bar_h = height * 0.004

        for i in range(n_segments):
            color = "black" if i % 2 == 0 else "white"
            rect = Rectangle(
                (bar_x + i * seg_len, bar_y),
                seg_len, bar_h,
                facecolor=color,
                edgecolor="black",
                linewidth=0.4,
                zorder=10,
            )
            ax.add_patch(rect)

        ax.text(bar_x, bar_y - bar_h * 0.3, "0",
                **ts_scale_label.mpl_kwargs(fontsize=ts_scale_label.fontsize * 0.8),
                ha="center", va="top", zorder=10)
        ax.text(bar_x + bar_w_data, bar_y - bar_h * 0.3, f"{scale_km} km",
                **ts_scale_label.mpl_kwargs(fontsize=ts_scale_label.fontsize * 0.8),
                ha="center", va="top", zorder=10)

        cursor_y = bar_y - bar_h * 2.5

        # Scale text info
        grid = context.grid
        hex_radius_m = grid.hex_radius_m
        hex_radius_km = hex_radius_m / 1000.0
        flat_to_flat_km = hex_radius_km * math.sqrt(3)

        output_width_m = spec.output_width_mm / 1000.0
        scale_ratio = int(width / output_width_m)
        if scale_ratio > 1000:
            scale_ratio = round(scale_ratio / 1000) * 1000

        scale_info = (
            f"1 hex = {hex_km:.0f} km  |  "
            f"Scale approx 1:{scale_ratio:,}  |  "
            f"{grid.hex_count} hexes"
        )
        ax.text(
            text_x, cursor_y, scale_info,
            **ts_scale_text.mpl_kwargs(),
            va="top", ha="left",
            zorder=10,
        )


def _draw_legend(ax, context, x_min, x_max, y_min, y_max):
    """Draw terrain effects legend at bottom-right of map."""
    style = context.style
    spec = context.spec
    width = x_max - x_min
    height = y_max - y_min

    terrains_present = set()
    for info in context.hex_terrain.values():
        terrains_present.add(info.get("terrain", TerrainType.CLEAR))

    if not terrains_present:
        return

    row_h = height * 0.018
    header_h = height * 0.022
    padding = height * 0.015

    box_h = padding + header_h + len(terrains_present) * row_h + padding
    box_w = width * 0.22
    box_x = x_max - width * 0.02 - box_w
    box_y = y_min + height * 0.02

    bg = FancyBboxPatch(
        (box_x, box_y), box_w, box_h,
        boxstyle="round,pad=0.005",
        facecolor="white",
        edgecolor="#666666",
        linewidth=0.8,
        alpha=0.9,
        zorder=9.5,
    )
    ax.add_patch(bg)

    text_x = box_x + box_w * 0.05
    cursor_y = box_y + box_h - padding

    typo = style.typography
    ts_header = typo.legend_header
    ts_label = typo.legend_label

    ax.text(
        text_x, cursor_y,
        "TERRAIN EFFECTS",
        **ts_header.mpl_kwargs(),
        ha="left", va="top", zorder=10,
    )
    cursor_y -= header_h

    swatch_w = box_w * 0.08
    swatch_h = row_h * 0.6

    for terrain in sorted(terrains_present, key=lambda t: t.value):
        effects = TERRAIN_EFFECTS.get(terrain)
        if effects is None:
            continue

        swatch_x = text_x
        swatch_y = cursor_y - swatch_h * 0.8
        color = style.terrain_colors.get(terrain, "#CCCCCC")

        swatch = Rectangle(
            (swatch_x, swatch_y), swatch_w, swatch_h,
            facecolor=color, edgecolor="#333333",
            linewidth=0.3, zorder=10,
        )
        ax.add_patch(swatch)

        hatch = style.terrain_hatches.get(terrain)
        if hatch:
            hatch_swatch = Rectangle(
                (swatch_x, swatch_y), swatch_w, swatch_h,
                facecolor="none", edgecolor=style.grid_color,
                hatch=hatch, linewidth=0, alpha=0.4, zorder=10.1,
            )
            ax.add_patch(hatch_swatch)

        label = f"{terrain.value.capitalize()}  MP:{effects.movement_cost}  Def:{effects.defensive_modifier:+d}"
        ax.text(
            text_x + swatch_w * 1.3, cursor_y - swatch_h * 0.1,
            label,
            **ts_label.mpl_kwargs(),
            va="top", ha="left", zorder=10,
        )
        cursor_y -= row_h


def _draw_scale_bar(ax, context, x_min, y_min, width, height):
    """Draw a scale bar with km markings and scale ratio."""
    hex_km = context.spec.hex_size_km
    spec = context.spec

    candidates = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    target_m = width * 0.15
    target_km = target_m / 1000.0
    scale_km = min(candidates, key=lambda c: abs(c - target_km))
    scale_m = scale_km * 1000.0

    bar_x = x_min + width * 0.03
    bar_y = y_min + height * 0.06
    bar_h = height * 0.005

    n_segments = 4
    seg_len = scale_m / n_segments
    for i in range(n_segments):
        color = "black" if i % 2 == 0 else "white"
        rect = Rectangle(
            (bar_x + i * seg_len, bar_y),
            seg_len, bar_h,
            facecolor=color,
            edgecolor="black",
            linewidth=0.5,
            zorder=10,
        )
        ax.add_patch(rect)

    ax.text(
        bar_x, bar_y - bar_h * 0.5,
        "0",
        fontsize=12, ha="center", va="top", zorder=10,
    )
    ax.text(
        bar_x + scale_m, bar_y - bar_h * 0.5,
        f"{scale_km} km",
        fontsize=12, ha="center", va="top", zorder=10,
    )

    ax.text(
        bar_x, bar_y + bar_h * 2,
        f"1 hex = {hex_km:.0f} km",
        fontsize=11, ha="left", va="bottom", color="#444444", zorder=10,
    )

    output_width_m = spec.output_width_mm / 1000.0
    scale_ratio = int(width / output_width_m)
    if scale_ratio > 1000:
        scale_ratio = round(scale_ratio / 1000) * 1000
    ax.text(
        bar_x, bar_y - bar_h * 3,
        f"Scale approx 1:{scale_ratio:,}",
        fontsize=11, ha="left", va="top", color="#666666", zorder=10,
    )


def _draw_hex_metrics(ax, context, x_min, y_min, width, height):
    """Draw pixel and vertex metrics in small type at bottom of map."""
    spec = context.spec
    grid = context.grid

    hex_radius_m = grid.hex_radius_m
    hex_radius_km = hex_radius_m / 1000.0
    flat_to_flat_km = hex_radius_km * math.sqrt(3)
    point_to_point_km = hex_radius_km * 2.0

    all_xs = [c.center_x for c in grid.cells.values()]
    if all_xs:
        data_width = max(all_xs) - min(all_xs) + 2 * hex_radius_m
        img_width_px = spec.output_width_mm / 25.4 * spec.dpi
        col_spacing_m = 1.5 * hex_radius_m
        approx_cols = data_width / col_spacing_m if col_spacing_m > 0 else 1
        px_per_hex = img_width_px / approx_cols if approx_cols > 0 else 0
    else:
        px_per_hex = 0

    metrics_text = (
        f"Hex: {flat_to_flat_km:.1f} km flat-to-flat, "
        f"{point_to_point_km:.1f} km point-to-point  |  "
        f"~{px_per_hex:.0f} px/hex @ {spec.dpi} DPI  |  "
        f"{grid.hex_count} hexes"
    )

    ax.text(
        x_min + width * 0.03,
        y_min + height * 0.012,
        metrics_text,
        fontsize=10.0,
        fontfamily="monospace",
        color="#666666",
        va="bottom",
        ha="left",
        zorder=10,
    )


def _draw_compass_rose(ax, cx, cy, size, typography=None):
    """Draw a 4-point star compass rose."""
    # Main N-S-E-W points
    point_len = size * 1.0
    inner_len = size * 0.3

    # North point (filled dark)
    n_verts = [
        (cx - inner_len * 0.3, cy),
        (cx, cy + point_len),
        (cx + inner_len * 0.3, cy),
    ]
    ax.fill(
        [v[0] for v in n_verts],
        [v[1] for v in n_verts],
        color="#333333", zorder=10.5,
    )

    # South point (lighter)
    s_verts = [
        (cx - inner_len * 0.3, cy),
        (cx, cy - point_len),
        (cx + inner_len * 0.3, cy),
    ]
    ax.fill(
        [v[0] for v in s_verts],
        [v[1] for v in s_verts],
        color="#999999", zorder=10.5,
    )

    # East point
    e_verts = [
        (cx, cy - inner_len * 0.3),
        (cx + point_len * 0.7, cy),
        (cx, cy + inner_len * 0.3),
    ]
    ax.fill(
        [v[0] for v in e_verts],
        [v[1] for v in e_verts],
        color="#666666", zorder=10.5,
    )

    # West point
    w_verts = [
        (cx, cy - inner_len * 0.3),
        (cx - point_len * 0.7, cy),
        (cx, cy + inner_len * 0.3),
    ]
    ax.fill(
        [v[0] for v in w_verts],
        [v[1] for v in w_verts],
        color="#AAAAAA", zorder=10.5,
    )

    # "N" label
    ts_compass = typography.compass_label if typography else None
    ax.text(
        cx, cy + point_len + size * 0.15,
        "N",
        fontsize=ts_compass.fontsize if ts_compass else 11,
        fontfamily=ts_compass.fontfamily if ts_compass else "sans-serif",
        fontweight=ts_compass.fontweight if ts_compass else "bold",
        ha="center", va="bottom",
        color=ts_compass.color if ts_compass else "#333333",
        zorder=10.6,
    )

    # Center circle
    circle = plt.Circle((cx, cy), inner_len * 0.2, color="white",
                         edgecolor="#333333", linewidth=0.5, zorder=10.6)
    ax.add_patch(circle)


def _draw_coord_ticks(ax, context, x_min, x_max, y_min, y_max):
    """Draw latitude/longitude tick marks along the map border."""
    grid = context.grid
    bbox = context.spec.bbox
    width = x_max - x_min
    height = y_max - y_min

    # Determine tick interval based on bbox span
    lon_span = bbox.max_lon - bbox.min_lon
    lat_span = bbox.max_lat - bbox.min_lat

    if max(lon_span, lat_span) > 10:
        interval = 2.0
    elif max(lon_span, lat_span) > 5:
        interval = 1.0
    elif max(lon_span, lat_span) > 1:
        interval = 0.5
    else:
        interval = 0.1

    ts_coord = context.style.typography.coord_tick
    tick_len = min(width, height) * 0.008
    tick_kw = dict(color=ts_coord.color, linewidth=0.5, zorder=10.5)
    text_kw = dict(fontsize=ts_coord.fontsize, color=ts_coord.color,
                   fontfamily=ts_coord.fontfamily, zorder=10.5)

    transformer = grid._to_proj

    # Longitude ticks along top and bottom edges
    lon_start = math.ceil(bbox.min_lon / interval) * interval
    lon = lon_start
    center_lat = (bbox.min_lat + bbox.max_lat) / 2.0
    while lon <= bbox.max_lon:
        try:
            tx, _ = transformer.transform(lon, center_lat)
            if x_min <= tx <= x_max:
                # Bottom tick
                ax.plot([tx, tx], [y_min, y_min + tick_len], **tick_kw)
                ax.text(tx, y_min - tick_len * 0.5,
                        f"{lon:.1f}°", ha="center", va="top", **text_kw)
                # Top tick
                ax.plot([tx, tx], [y_max - tick_len, y_max], **tick_kw)
        except Exception:
            pass
        lon += interval

    # Latitude ticks along left and right edges
    lat_start = math.ceil(bbox.min_lat / interval) * interval
    lat = lat_start
    center_lon = (bbox.min_lon + bbox.max_lon) / 2.0
    while lat <= bbox.max_lat:
        try:
            _, ty = transformer.transform(center_lon, lat)
            if y_min <= ty <= y_max:
                # Left tick
                ax.plot([x_min, x_min + tick_len], [ty, ty], **tick_kw)
                ax.text(x_min - tick_len * 0.5, ty,
                        f"{lat:.1f}°", ha="right", va="center", **text_kw)
                # Right tick
                ax.plot([x_max - tick_len, x_max], [ty, ty], **tick_kw)
        except Exception:
            pass
        lat += interval
