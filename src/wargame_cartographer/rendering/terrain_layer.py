"""Terrain layer: colored hex fills using PatchCollection for performance."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.collections import PatchCollection
import numpy as np

from wargame_cartographer.rendering.renderer import RenderContext
from wargame_cartographer.terrain.types import TerrainType


def render_terrain_layer(ax: plt.Axes, context: RenderContext):
    """Draw terrain-colored hex fills."""
    style = context.style
    grid = context.grid

    patches = []
    facecolors = []
    hatches = []

    for (q, r) in grid.all_hexes():
        verts = grid.hex_vertices(q, r)
        verts_arr = np.array(verts + [verts[0]])  # Close the polygon

        codes = (
            [MplPath.MOVETO]
            + [MplPath.LINETO] * (len(verts_arr) - 2)
            + [MplPath.CLOSEPOLY]
        )
        path = MplPath(verts_arr, codes)

        terrain_info = context.hex_terrain.get((q, r), {})
        terrain = terrain_info.get("terrain", TerrainType.CLEAR)
        color = style.terrain_colors.get(terrain, "#F5EDD5")
        hatch = style.terrain_hatches.get(terrain)

        patch = PathPatch(
            path,
            facecolor=color,
            edgecolor="none",
            hatch=hatch,
            linewidth=0,
            zorder=1,
        )
        ax.add_patch(patch)
