"""Symbol layer: city, port, and airfield markers."""

from __future__ import annotations

import matplotlib.pyplot as plt

from wargame_cartographer.rendering.renderer import RenderContext


def render_symbol_layer(ax: plt.Axes, context: RenderContext):
    """Draw city, port, and airfield symbols."""
    if context.vector_data is None:
        return

    style = context.style
    transformer = context.grid._to_proj

    # Cities
    if context.spec.show_cities and hasattr(context.vector_data, 'cities') and not context.vector_data.cities.empty:
        for _, city in context.vector_data.cities.iterrows():
            if hasattr(city.geometry, 'x'):
                px, py = transformer.transform(city.geometry.x, city.geometry.y)
                ax.plot(
                    px, py,
                    marker=style.city_marker,
                    markersize=style.city_marker_size,
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
