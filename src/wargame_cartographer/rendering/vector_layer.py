"""Vector layer: rivers, coastlines, and other line features."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon

from wargame_cartographer.rendering.renderer import RenderContext


def render_vector_layer(ax: plt.Axes, context: RenderContext):
    """Draw rivers and coastlines as projected line features."""
    if context.vector_data is None:
        return

    transformer = context.grid._to_proj
    style = context.style

    # Coastlines
    if hasattr(context.vector_data, 'coastline') and not context.vector_data.coastline.empty:
        _draw_geodataframe_lines(
            ax, context.vector_data.coastline, transformer,
            color=style.coastline_color,
            linewidth=style.coastline_linewidth,
            zorder=3,
        )

    # Rivers
    if context.spec.show_rivers and hasattr(context.vector_data, 'rivers') and not context.vector_data.rivers.empty:
        _draw_geodataframe_lines(
            ax, context.vector_data.rivers, transformer,
            color=style.river_color,
            linewidth=style.river_linewidth,
            zorder=3,
        )


def _draw_geodataframe_lines(ax, gdf, transformer, color, linewidth, zorder):
    """Draw all line geometries in a GeoDataFrame."""
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            continue
        _draw_geometry_lines(ax, geom, transformer, color, linewidth, zorder)


def _draw_geometry_lines(ax, geom, transformer, color, linewidth, zorder):
    """Draw a shapely geometry as projected lines."""
    if isinstance(geom, LineString):
        coords = list(geom.coords)
        if len(coords) < 2:
            return
        projected = [transformer.transform(x, y) for x, y in coords]
        xs = [p[0] for p in projected]
        ys = [p[1] for p in projected]
        ax.plot(xs, ys, color=color, linewidth=linewidth, zorder=zorder, solid_capstyle="round")

    elif isinstance(geom, MultiLineString):
        for line in geom.geoms:
            _draw_geometry_lines(ax, line, transformer, color, linewidth, zorder)

    elif isinstance(geom, (Polygon, MultiPolygon)):
        # Draw polygon boundaries as lines (for coastlines that come as polygons)
        if isinstance(geom, MultiPolygon):
            polys = list(geom.geoms)
        else:
            polys = [geom]
        for poly in polys:
            coords = list(poly.exterior.coords)
            if len(coords) < 2:
                continue
            projected = [transformer.transform(x, y) for x, y in coords]
            xs = [p[0] for p in projected]
            ys = [p[1] for p in projected]
            ax.plot(xs, ys, color=color, linewidth=linewidth, zorder=zorder, solid_capstyle="round")
