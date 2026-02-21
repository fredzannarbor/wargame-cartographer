"""Cartouche layer: title, legend, scale bar, compass rose."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
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

    # Title block (top-left) — all text inside a single background box
    if spec.title:
        _draw_title_block(ax, context, x_min, y_max, width, height)

    # Scale bar (bottom-left)
    if spec.show_scale_bar:
        _draw_scale_bar(ax, context, x_min, y_min, width, height)

    # Legend (bottom-right)
    if spec.show_legend:
        _draw_legend(ax, context, x_max, y_min, width, height)

    # Compass rose (top-right)
    if spec.show_compass:
        _draw_compass(ax, x_max - width * 0.06, y_max - height * 0.06, height * 0.04)

    # Hex metrics info (bottom-left, below scale bar)
    _draw_hex_metrics(ax, context, x_min, y_min, width, height)

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
    """Draw title, subtitle, and scenario in a properly sized background box."""
    style = context.style
    spec = context.spec

    # Measure text lines to compute box size
    # Use half the title fontsize for cartouche text (2x smaller)
    title_fs = style.title_fontsize * 0.5
    subtitle_fs = title_fs * 0.5
    scenario_fs = title_fs * 0.4

    # Vertical spacing in data coordinates
    line_gap = height * 0.015
    title_h = height * 0.025
    subtitle_h = height * 0.015
    scenario_h = height * 0.012
    padding = height * 0.015

    # Calculate total box height
    box_h = padding  # top padding
    box_h += title_h  # title
    if spec.subtitle:
        box_h += line_gap + subtitle_h
    if spec.scenario:
        box_h += line_gap + scenario_h
    box_h += padding  # bottom padding (more space underneath title)

    box_w = width * 0.30
    box_x = x_min + width * 0.02
    box_y = y_max - height * 0.02 - box_h

    # Background box
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

    # Title text — positioned within box
    text_x = box_x + box_w * 0.05
    cursor_y = box_y + box_h - padding

    ax.text(
        text_x, cursor_y,
        spec.title.upper(),
        fontsize=title_fs,
        fontfamily="sans-serif",
        fontweight="bold",
        color="#222222",
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
            fontsize=subtitle_fs,
            fontfamily="sans-serif",
            color="#444444",
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
            fontsize=scenario_fs,
            fontfamily="sans-serif",
            fontstyle="italic",
            color="#666666",
            va="top",
            ha="left",
            zorder=10,
        )


def _draw_scale_bar(ax, context, x_min, y_min, width, height):
    """Draw a scale bar with km markings and scale ratio."""
    hex_km = context.spec.hex_size_km
    spec = context.spec

    # Choose scale bar length: nice round number of km
    candidates = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    # Aim for scale bar ~15% of map width
    target_m = width * 0.15
    target_km = target_m / 1000.0
    scale_km = min(candidates, key=lambda c: abs(c - target_km))
    scale_m = scale_km * 1000.0

    bar_x = x_min + width * 0.03
    bar_y = y_min + height * 0.06
    bar_h = height * 0.005

    # Draw alternating black/white segments
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

    # Labels
    ax.text(
        bar_x, bar_y - bar_h * 0.5,
        "0",
        fontsize=5, ha="center", va="top", zorder=10,
    )
    ax.text(
        bar_x + scale_m, bar_y - bar_h * 0.5,
        f"{scale_km} km",
        fontsize=5, ha="center", va="top", zorder=10,
    )

    # Hex size annotation
    ax.text(
        bar_x, bar_y + bar_h * 2,
        f"1 hex = {hex_km:.0f} km",
        fontsize=4, ha="left", va="bottom", color="#666666", zorder=10,
    )

    # Compute and show map scale ratio
    # output_width_mm is the physical print width; width is data extent in meters
    output_width_m = spec.output_width_mm / 1000.0  # mm → m
    scale_ratio = int(width / output_width_m)
    # Round to a nice number
    if scale_ratio > 1000:
        scale_ratio = round(scale_ratio / 1000) * 1000
    ax.text(
        bar_x, bar_y - bar_h * 3,
        f"Scale approx 1:{scale_ratio:,}",
        fontsize=3.5, ha="left", va="top", color="#888888", zorder=10,
    )


def _draw_hex_metrics(ax, context, x_min, y_min, width, height):
    """Draw pixel and vertex metrics in small type at bottom of map."""
    spec = context.spec
    grid = context.grid

    hex_radius_m = grid.hex_radius_m
    hex_radius_km = hex_radius_m / 1000.0
    flat_to_flat_km = hex_radius_km * math.sqrt(3)
    point_to_point_km = hex_radius_km * 2.0

    # Compute approximate pixels per hex
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
        fontsize=3.0,
        fontfamily="monospace",
        color="#999999",
        va="bottom",
        ha="left",
        zorder=10,
    )


def _draw_legend(ax, context, x_max, y_min, width, height):
    """Draw terrain effects legend."""
    style = context.style

    # Collect terrain types actually present
    terrains_present = set()
    for info in context.hex_terrain.values():
        terrains_present.add(info.get("terrain", TerrainType.CLEAR))

    if not terrains_present:
        return

    # Legend box — compact with 2x smaller fonts
    legend_w = width * 0.14
    row_h = height * 0.015
    legend_h = row_h * (len(terrains_present) + 1.5)
    lx = x_max - width * 0.02 - legend_w
    ly = y_min + height * 0.04

    bg = FancyBboxPatch(
        (lx, ly), legend_w, legend_h,
        boxstyle="round,pad=0.005",
        facecolor=style.legend_bg_color,
        edgecolor="#666666",
        linewidth=0.5,
        zorder=9,
    )
    ax.add_patch(bg)

    # Header
    ax.text(
        lx + legend_w * 0.5, ly + legend_h - row_h * 0.3,
        "TERRAIN EFFECTS",
        fontsize=3.0, fontweight="bold", ha="center", va="top",
        fontfamily="sans-serif", zorder=10,
    )

    # Terrain entries
    for i, terrain in enumerate(sorted(terrains_present, key=lambda t: t.value)):
        effects = TERRAIN_EFFECTS.get(terrain)
        if effects is None:
            continue

        y_pos = ly + legend_h - row_h * 1.2 - i * row_h
        color = style.terrain_colors.get(terrain, "#CCCCCC")

        # Color swatch
        swatch = Rectangle(
            (lx + legend_w * 0.05, y_pos - row_h * 0.3),
            legend_w * 0.08, row_h * 0.6,
            facecolor=color,
            edgecolor="#333333",
            linewidth=0.3,
            zorder=10,
        )
        ax.add_patch(swatch)

        # Terrain name + movement cost
        label = f"{terrain.value.capitalize()}  MP:{effects.movement_cost}  Def:{effects.defensive_modifier:+d}"
        ax.text(
            lx + legend_w * 0.18, y_pos,
            label,
            fontsize=2.0, va="center", ha="left",
            fontfamily="sans-serif", zorder=10,
        )


def _draw_compass(ax, cx, cy, size):
    """Draw a simple compass rose."""
    # North arrow
    ax.annotate(
        "N",
        xy=(cx, cy + size),
        xytext=(cx, cy),
        fontsize=8, fontweight="bold",
        ha="center", va="center",
        arrowprops=dict(arrowstyle="->", color="black", lw=1.5),
        zorder=10,
    )
