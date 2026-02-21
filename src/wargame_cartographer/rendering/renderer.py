"""Main map renderer: composites all layers into a matplotlib figure."""

from __future__ import annotations

import logging
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
import pyproj

from wargame_cartographer.config.map_spec import MapSpec
from wargame_cartographer.hex.grid import HexGrid
from wargame_cartographer.rendering.styles import WargameStyle, get_style
from wargame_cartographer.terrain.types import TerrainType

logger = logging.getLogger(__name__)


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

        # Readability state (computed during render)
        self.px_per_hex: float = 0.0
        self.skip_decorations: bool = False

        # Counter collision tracking — hex IDs occupied by NATO counters
        self.occupied_hexes: set[str] = set()


def _compute_px_per_hex(spec: MapSpec, grid: HexGrid, data_width: float) -> float:
    """Compute approximate pixels per hex (flat-to-flat) at current settings."""
    img_width_px = (spec.output_width_mm / 25.4) * spec.dpi
    hex_flat_to_flat_m = grid.hex_radius_m * math.sqrt(3)
    if hex_flat_to_flat_m <= 0 or data_width <= 0:
        return 0.0
    n_hexes_across = data_width / (1.5 * grid.hex_radius_m)
    if n_hexes_across <= 0:
        return 0.0
    return img_width_px / n_hexes_across


def _collect_occupied_hexes(spec: MapSpec) -> set[str]:
    """Collect hex IDs that have NATO unit counters placed on them."""
    occupied = set()
    if spec.nato_units:
        for unit in spec.nato_units:
            if unit.hex_id:
                occupied.add(unit.hex_id)
    return occupied


class MapRenderer:
    """Composite renderer: runs layer stack to produce a matplotlib figure."""

    def render(self, context: RenderContext) -> plt.Figure:
        """Render the complete map, optionally with side panels."""
        spec = context.spec

        # Collect occupied hexes for collision avoidance
        context.occupied_hexes = _collect_occupied_hexes(spec)

        # Determine if we need panels
        has_oob = spec.show_oob_panel and spec.oob_data
        has_modules = spec.show_module_panels and spec.module_panels

        # Figure size in inches
        width_in = spec.output_width_mm / 25.4
        height_in = spec.output_height_mm / 25.4

        if has_oob or has_modules:
            fig, ax = self._create_paneled_figure(
                context, width_in, height_in, has_oob, has_modules
            )
        else:
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

        # Hex readability check
        data_width = x_max - x_min
        context.px_per_hex = _compute_px_per_hex(spec, context.grid, data_width)

        if context.px_per_hex < spec.min_hex_px:
            logger.warning(
                "Hex pixel size (%.0f px) is below minimum (%d px). "
                "Terrain decorations will be skipped for readability.",
                context.px_per_hex,
                spec.min_hex_px,
            )
            context.skip_decorations = True

        if context.px_per_hex > 0 and context.px_per_hex < 25:
            adjusted_scale = context.px_per_hex / 40.0
            logger.warning(
                "Very small hexes (%.0f px). Auto-reducing font_scale to %.2f.",
                context.px_per_hex,
                adjusted_scale,
            )

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

        # Layer 7.5: NATO unit counters and movement arrows
        if context.spec.nato_units:
            from wargame_cartographer.rendering.nato_layer import render_nato_layer
            render_nato_layer(ax, context)

        # Layer 8: Cartouche (title, legend, scale bar)
        from wargame_cartographer.rendering.cartouche_layer import render_cartouche_layer
        render_cartouche_layer(ax, context, x_min, x_max, y_min, y_max)

        fig.tight_layout(pad=0.5)
        return fig

    def _create_paneled_figure(
        self,
        context: RenderContext,
        width_in: float,
        height_in: float,
        has_oob: bool,
        has_modules: bool,
    ) -> tuple[plt.Figure, plt.Axes]:
        """Create a figure with GridSpec layout for map + optional panels."""
        spec = context.spec

        # Determine grid layout ratios
        n_cols = 1
        width_ratios = [1.0]
        n_rows = 1
        height_ratios = [1.0]

        oob_col = None
        module_row = None

        # OOB panel (side panel)
        if has_oob:
            oob_ratio = spec.oob_panel_width_ratio
            if spec.oob_panel_position == "right":
                n_cols = 2
                width_ratios = [1.0 - oob_ratio, oob_ratio]
                oob_col = 1
            elif spec.oob_panel_position == "left":
                n_cols = 2
                width_ratios = [oob_ratio, 1.0 - oob_ratio]
                oob_col = 0
            elif spec.oob_panel_position == "bottom":
                n_rows = 2
                height_ratios = [1.0 - oob_ratio, oob_ratio]
                module_row = 1  # OOB takes module row position

        # Module panels (bottom panel)
        if has_modules and spec.module_panel_position == "bottom":
            mod_ratio = 0.20
            if n_rows == 1:
                n_rows = 2
                height_ratios = [1.0 - mod_ratio, mod_ratio]
                module_row = 1
            else:
                # Already have 2 rows, add a third
                n_rows = 3
                height_ratios = [height_ratios[0] - mod_ratio, height_ratios[1] if len(height_ratios) > 1 else 0, mod_ratio]
                module_row = 2
        elif has_modules and spec.module_panel_position in ("right", "left"):
            mod_ratio = 0.20
            if n_cols == 1:
                n_cols = 2
                if spec.module_panel_position == "right":
                    width_ratios = [1.0 - mod_ratio, mod_ratio]
                else:
                    width_ratios = [mod_ratio, 1.0 - mod_ratio]

        fig = plt.figure(figsize=(width_in, height_in), dpi=spec.dpi)
        gs = GridSpec(n_rows, n_cols, figure=fig,
                      width_ratios=width_ratios, height_ratios=height_ratios,
                      wspace=0.02, hspace=0.02)

        # Map axes — always at position (0, 0) unless OOB is on left
        map_row, map_col = 0, 0
        if has_oob and spec.oob_panel_position == "left":
            map_col = 1

        ax = fig.add_subplot(gs[map_row, map_col])

        # OOB panel axes
        if has_oob and oob_col is not None:
            oob_ax = fig.add_subplot(gs[0, oob_col])
            oob_ax.axis("off")
            from wargame_cartographer.rendering.oob_panel import render_oob_panel
            render_oob_panel(oob_ax, context)
        elif has_oob and spec.oob_panel_position == "bottom" and module_row is not None:
            oob_ax = fig.add_subplot(gs[module_row, :])
            oob_ax.axis("off")
            from wargame_cartographer.rendering.oob_panel import render_oob_panel
            render_oob_panel(oob_ax, context)

        # Module panel axes
        if has_modules and module_row is not None:
            mod_ax = fig.add_subplot(gs[module_row, :])
            mod_ax.axis("off")
            from wargame_cartographer.rendering.module_panel import render_module_panels
            render_module_panels(mod_ax, context)

        return fig, ax
