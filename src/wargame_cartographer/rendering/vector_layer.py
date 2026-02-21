"""Vector layer: rivers, coastlines, and other line features with hierarchy."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon

from wargame_cartographer.rendering.renderer import RenderContext


def render_vector_layer(ax: plt.Axes, context: RenderContext):
    """Draw rivers and coastlines as projected line features with hierarchy."""
    if context.vector_data is None:
        return

    transformer = context.grid._to_proj
    style = context.style

    # Coastlines
    if hasattr(context.vector_data, 'coastline') and not context.vector_data.coastline.empty:
        _draw_geodataframe_lines(
            ax, context.vector_data.coastline, transformer,
            color=style.coastline_color,
            base_linewidth=style.coastline_linewidth,
            zorder=3,
            use_hierarchy=False,
        )

    # Rivers with hierarchy
    if context.spec.show_rivers and hasattr(context.vector_data, 'rivers') and not context.vector_data.rivers.empty:
        _draw_geodataframe_lines(
            ax, context.vector_data.rivers, transformer,
            color=style.river_color,
            base_linewidth=style.river_linewidth,
            zorder=3,
            use_hierarchy=True,
        )

    # Roads with hierarchy
    if context.spec.show_roads and hasattr(context.vector_data, 'roads') and not context.vector_data.roads.empty:
        _draw_geodataframe_lines(
            ax, context.vector_data.roads, transformer,
            color=style.road_color,
            base_linewidth=style.road_linewidth,
            zorder=3,
            use_hierarchy=True,
        )


def _get_feature_scale(row, base_linewidth: float) -> float:
    """Scale linewidth based on feature importance (scalerank attribute)."""
    scalerank = None
    for attr in ('scalerank', 'SCALERANK', 'strokeweig', 'scale_rank'):
        val = getattr(row, attr, None)
        if val is not None:
            try:
                scalerank = float(val)
                break
            except (ValueError, TypeError):
                continue

    if scalerank is None:
        return base_linewidth

    # scalerank 0 = most important, 10 = least
    scale_factor = max(0.5, 1.8 - scalerank * 0.13)
    return base_linewidth * scale_factor


def _draw_geodataframe_lines(ax, gdf, transformer, color, base_linewidth, zorder,
                              use_hierarchy=False):
    """Draw all line geometries in a GeoDataFrame."""
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            continue
        lw = _get_feature_scale(row, base_linewidth) if use_hierarchy else base_linewidth
        _draw_geometry_lines(ax, geom, transformer, color, lw, zorder)


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
