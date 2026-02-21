"""Main map renderer: composites all layers into a matplotlib figure."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyproj

from wargame_cartographer.config.map_spec import MapSpec
from wargame_cartographer.hex.grid import HexGrid
from wargame_cartographer.rendering.styles import WargameStyle, get_style
from wargame_cartographer.terrain.types import TerrainType


class RenderContext:
    """Shared context passed to all rendering layers."""

    def __init__(
        self,
        spec: MapSpec,
        grid: HexGrid,
        hex_terrain: dict[tuple[int, int], dict],
        style: WargameStyle,
        elevation: np.ndarray | None = None,
        hillshade: np.ndarray | None = None,
        elevation_metadata: dict | None = None,
        vector_data=None,
    ):
        self.spec = spec
        self.grid = grid
        self.hex_terrain = hex_terrain
        self.style = style
        self.elevation = elevation
        self.hillshade = hillshade
        self.elevation_metadata = elevation_metadata
        self.vector_data = vector_data


class MapRenderer:
    """Composite renderer: runs layer stack to produce a matplotlib figure."""

    def render(self, context: RenderContext) -> plt.Figure:
        """Render the complete map."""
        spec = context.spec

        # Figure size in inches
        width_in = spec.output_width_mm / 25.4
        height_in = spec.output_height_mm / 25.4
        fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=spec.dpi)
        ax.set_aspect("equal")
        ax.axis("off")
        fig.patch.set_facecolor("white")

        # Compute display bounds from grid
        all_xs = [c.center_x for c in context.grid.cells.values()]
        all_ys = [c.center_y for c in context.grid.cells.values()]
        if not all_xs:
            return fig

        pad = context.grid.hex_radius_m * 2
        x_min, x_max = min(all_xs) - pad, max(all_xs) + pad
        y_min, y_max = min(all_ys) - pad, max(all_ys) + pad
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)

        # Layer 1: Background (water color)
        ax.set_facecolor(context.style.water_color)

        # Layer 2: Terrain fill
        from wargame_cartographer.rendering.terrain_layer import render_terrain_layer
        render_terrain_layer(ax, context)

        # Layer 3: Hillshade overlay
        if context.spec.show_elevation_shading and context.hillshade is not None:
            from wargame_cartographer.rendering.elevation_layer import render_elevation_layer
            render_elevation_layer(ax, context, x_min, x_max, y_min, y_max)

        # Layer 4: Vector overlays (rivers, coastlines)
        from wargame_cartographer.rendering.vector_layer import render_vector_layer
        render_vector_layer(ax, context)

        # Layer 5: Hex grid lines
        from wargame_cartographer.rendering.grid_layer import render_grid_layer
        render_grid_layer(ax, context)

        # Layer 6: Symbols (cities, ports)
        if context.spec.show_cities or context.spec.show_ports:
            from wargame_cartographer.rendering.symbol_layer import render_symbol_layer
            render_symbol_layer(ax, context)

        # Layer 7: Labels (hex numbers, city names)
        from wargame_cartographer.rendering.label_layer import render_label_layer
        render_label_layer(ax, context)

        # Layer 8: Cartouche (title, legend, scale bar)
        from wargame_cartographer.rendering.cartouche_layer import render_cartouche_layer
        render_cartouche_layer(ax, context, x_min, x_max, y_min, y_max)

        fig.tight_layout(pad=0.5)
        return fig
