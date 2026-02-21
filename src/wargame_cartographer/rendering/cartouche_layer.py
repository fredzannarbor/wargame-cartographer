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

    # Title block (top-left)
    if spec.title:
        ax.text(
            x_min + width * 0.02,
            y_max - height * 0.02,
            spec.title.upper(),
            fontsize=style.title_fontsize,
            fontfamily="sans-serif",
            fontweight="bold",
            color="#222222",
            va="top",
            ha="left",
            zorder=10,
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=3),
        )

    if spec.subtitle:
        ax.text(
            x_min + width * 0.02,
            y_max - height * 0.07,
            spec.subtitle,
            fontsize=style.title_fontsize * 0.5,
            fontfamily="sans-serif",
            color="#444444",
            va="top",
            ha="left",
            zorder=10,
        )

    if spec.scenario:
        ax.text(
            x_min + width * 0.02,
            y_max - height * 0.10,
            spec.scenario,
            fontsize=style.title_fontsize * 0.4,
            fontfamily="sans-serif",
            fontstyle="italic",
            color="#666666",
            va="top",
            ha="left",
            zorder=10,
        )

    # Scale bar (bottom-left)
    if spec.show_scale_bar:
        _draw_scale_bar(ax, context, x_min, y_min, width, height)

    # Legend (bottom-right)
    if spec.show_legend:
        _draw_legend(ax, context, x_max, y_min, width, height)

    # Compass rose (top-right)
    if spec.show_compass:
        _draw_compass(ax, x_max - width * 0.06, y_max - height * 0.06, height * 0.04)

    # Map border
    border_rect = Rectangle(
        (x_min, y_min), width, height,
        linewidth=style.border_linewidth,
        edgecolor=style.border_color,
        facecolor="none",
        zorder=11,
    )
    ax.add_patch(border_rect)


def _draw_scale_bar(ax, context, x_min, y_min, width, height):
    """Draw a scale bar with km markings."""
    hex_km = context.spec.hex_size_km

    # Choose scale bar length: nice round number of km
    candidates = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    # Aim for scale bar ~15% of map width
    target_m = width * 0.15
    target_km = target_m / 1000.0
    scale_km = min(candidates, key=lambda c: abs(c - target_km))
    scale_m = scale_km * 1000.0

    bar_x = x_min + width * 0.03
    bar_y = y_min + height * 0.04
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


def _draw_legend(ax, context, x_max, y_min, width, height):
    """Draw terrain effects legend."""
    style = context.style

    # Collect terrain types actually present
    terrains_present = set()
    for info in context.hex_terrain.values():
        terrains_present.add(info.get("terrain", TerrainType.CLEAR))

    if not terrains_present:
        return

    # Legend box
    legend_w = width * 0.18
    legend_h = height * 0.03 * (len(terrains_present) + 1)
    lx = x_max - width * 0.02 - legend_w
    ly = y_min + height * 0.03

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
        lx + legend_w * 0.5, ly + legend_h - height * 0.01,
        "TERRAIN EFFECTS",
        fontsize=5, fontweight="bold", ha="center", va="top",
        fontfamily="sans-serif", zorder=10,
    )

    # Terrain entries
    row_h = height * 0.025
    for i, terrain in enumerate(sorted(terrains_present, key=lambda t: t.value)):
        effects = TERRAIN_EFFECTS.get(terrain)
        if effects is None:
            continue

        y_pos = ly + legend_h - height * 0.025 - i * row_h
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
            fontsize=3.5, va="center", ha="left",
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
