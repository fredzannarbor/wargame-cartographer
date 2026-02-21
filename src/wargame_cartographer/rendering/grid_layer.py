"""Grid layer: hex outline grid lines."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from wargame_cartographer.rendering.renderer import RenderContext


def render_grid_layer(ax: plt.Axes, context: RenderContext):
    """Draw hex grid outlines."""
    style = context.style
    grid = context.grid

    for (q, r) in grid.all_hexes():
        verts = grid.hex_vertices(q, r)
        # Close the polygon
        xs = [v[0] for v in verts] + [verts[0][0]]
        ys = [v[1] for v in verts] + [verts[0][1]]

        ax.plot(
            xs, ys,
            color=style.grid_color,
            linewidth=style.grid_linewidth,
            alpha=style.grid_alpha,
            zorder=4,
            solid_joinstyle="round",
        )
