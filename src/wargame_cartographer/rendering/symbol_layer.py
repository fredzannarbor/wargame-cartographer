"""Symbol layer: city, port, and airfield markers with prominence scaling."""

from __future__ import annotations

import matplotlib.pyplot as plt

from wargame_cartographer.rendering.renderer import RenderContext


def _get_city_scale(city_row) -> float:
    """Get prominence scale factor from city scalerank attribute."""
    scalerank = None
    for attr in ('scalerank', 'SCALERANK', 'scale_rank'):
        val = getattr(city_row, attr, None)
        if val is not None:
            try:
                scalerank = float(val)
                break
            except (ValueError, TypeError):
                continue

    if scalerank is None:
        return 1.0

    # Capitals (0-2): 2x, major cities (3-5): 1.5x, towns (6+): 1x
    if scalerank <= 2:
        return 2.0
    elif scalerank <= 5:
        return 1.5
    return 1.0


def render_symbol_layer(ax: plt.Axes, context: RenderContext):
    """Draw city, port, and airfield symbols with prominence scaling."""
    if context.vector_data is None:
        return

    style = context.style
    transformer = context.grid._to_proj

    # Cities
    if context.spec.show_cities and hasattr(context.vector_data, 'cities') and not context.vector_data.cities.empty:
        for _, city in context.vector_data.cities.iterrows():
            if hasattr(city.geometry, 'x'):
                px, py = transformer.transform(city.geometry.x, city.geometry.y)
                scale = _get_city_scale(city)
                ax.plot(
                    px, py,
                    marker=style.city_marker,
                    markersize=style.city_marker_size * scale,
                    color=style.city_marker_color,
                    markeredgecolor="white",
                    markeredgewidth=0.5,
                    zorder=5,
                    linestyle="none",
                )

    # Ports
    if context.spec.show_ports and hasattr(context.vector_data, 'ports') and not context.vector_data.ports.empty:
        for _, port in context.vector_data.ports.iterrows():
            if hasattr(port.geometry, 'x'):
                px, py = transformer.transform(port.geometry.x, port.geometry.y)
            elif hasattr(port.geometry, 'centroid'):
                c = port.geometry.centroid
                px, py = transformer.transform(c.x, c.y)
            else:
                continue
            ax.plot(
                px, py,
                marker=style.port_marker,
                markersize=style.port_marker_size,
                color=style.port_marker_color,
                markeredgecolor="white",
                markeredgewidth=0.5,
                zorder=5,
                linestyle="none",
            )
