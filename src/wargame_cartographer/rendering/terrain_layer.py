"""Terrain layer: colored hex fills with custom terrain patterns."""

from __future__ import annotations

import math
import hashlib

import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Circle, FancyBboxPatch
from matplotlib.path import Path as MplPath
import numpy as np

from wargame_cartographer.rendering.renderer import RenderContext
from wargame_cartographer.terrain.types import TerrainType


def render_terrain_layer(ax: plt.Axes, context: RenderContext):
    """Draw terrain-colored hex fills with custom decorative patterns."""
    style = context.style
    grid = context.grid
    r = grid.hex_radius_m

    for (q, row) in grid.all_hexes():
        verts = grid.hex_vertices(q, row)
        verts_arr = np.array(verts + [verts[0]])

        codes = (
            [MplPath.MOVETO]
            + [MplPath.LINETO] * (len(verts_arr) - 2)
            + [MplPath.CLOSEPOLY]
        )
        path = MplPath(verts_arr, codes)

        terrain_info = context.hex_terrain.get((q, row), {})
        terrain = terrain_info.get("terrain", TerrainType.CLEAR)
        color = style.terrain_colors.get(terrain, "#F5EDD5")

        # Base fill — no hatch, we draw custom patterns instead
        patch = PathPatch(
            path,
            facecolor=color,
            edgecolor="none",
            linewidth=0,
            zorder=1,
        )
        ax.add_patch(patch)

        cell = grid.cells[(q, row)]
        cx, cy = cell.center_x, cell.center_y

        # Custom terrain decorations
        if terrain == TerrainType.URBAN:
            _draw_urban_grid(ax, cx, cy, r)
        elif terrain == TerrainType.FOREST:
            _draw_forest_trees(ax, cx, cy, r, q, row)
        elif terrain == TerrainType.ROUGH:
            _draw_rough_blotches(ax, cx, cy, r, q, row)


def _draw_urban_grid(ax, cx, cy, r):
    """Draw a black-and-white street grid pattern inside the hex."""
    # White base
    size = r * 0.55
    rect = FancyBboxPatch(
        (cx - size, cy - size), size * 2, size * 2,
        boxstyle="round,pad=0",
        facecolor="#F0F0F0",
        edgecolor="none",
        zorder=1.2,
        clip_on=True,
    )
    ax.add_patch(rect)

    # Grid lines — streets
    spacing = r * 0.22
    line_kw = dict(color="#333333", linewidth=0.6, zorder=1.3, alpha=0.8)
    # Horizontal streets
    for offset in np.arange(-size, size + spacing, spacing):
        y = cy + offset
        ax.plot([cx - size, cx + size], [y, y], **line_kw)
    # Vertical streets
    for offset in np.arange(-size, size + spacing, spacing):
        x = cx + offset
        ax.plot([x, x], [cy - size, cy + size], **line_kw)

    # City block fills (dark grey small rectangles)
    block_size = spacing * 0.35
    for xo in np.arange(-size + spacing * 0.3, size, spacing):
        for yo in np.arange(-size + spacing * 0.3, size, spacing):
            bx, by = cx + xo, cy + yo
            block = FancyBboxPatch(
                (bx - block_size, by - block_size),
                block_size * 2, block_size * 2,
                boxstyle="round,pad=0",
                facecolor="#888888",
                edgecolor="none",
                zorder=1.25,
                alpha=0.5,
            )
            ax.add_patch(block)


def _draw_forest_trees(ax, cx, cy, r, q, row):
    """Draw small tree symbols (stylized triangles) scattered in the hex."""
    # Deterministic pseudo-random positions
    seed = int(hashlib.md5(f"{q},{row}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)

    n_trees = 8
    spread = r * 0.55

    for i in range(n_trees):
        # Random offset within hex, clustered near center
        tx = cx + rng.uniform(-spread, spread)
        ty = cy + rng.uniform(-spread, spread)

        # Small triangle (tree top)
        tree_h = r * 0.18
        tree_w = r * 0.10
        tri_x = [tx - tree_w, tx + tree_w, tx, tx - tree_w]
        tri_y = [ty, ty, ty + tree_h, ty]
        ax.fill(tri_x, tri_y, color="#1B5E20", zorder=1.4, alpha=0.85)

        # Trunk
        trunk_h = r * 0.06
        ax.plot(
            [tx, tx], [ty - trunk_h, ty],
            color="#5D4037", linewidth=1.0, zorder=1.35,
        )


def _draw_rough_blotches(ax, cx, cy, r, q, row):
    """Draw irregular tan blotches for rough terrain."""
    seed = int(hashlib.md5(f"rough_{q},{row}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)

    n_blotches = 6
    spread = r * 0.5

    for i in range(n_blotches):
        bx = cx + rng.uniform(-spread, spread)
        by = cy + rng.uniform(-spread, spread)
        blob_r = r * rng.uniform(0.06, 0.14)

        # Irregular blob: circle with varying radius
        angles = np.linspace(0, 2 * math.pi, 12)
        radii = blob_r * (1.0 + 0.3 * rng.randn(12))
        xs = bx + radii * np.cos(angles)
        ys = by + radii * np.sin(angles)

        ax.fill(
            xs, ys,
            color="#A0855A",
            alpha=0.6,
            zorder=1.3,
            edgecolor="#8B7040",
            linewidth=0.3,
        )
