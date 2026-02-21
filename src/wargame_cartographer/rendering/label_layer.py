"""Label layer: hex numbers and city names."""

from __future__ import annotations

import matplotlib.pyplot as plt

from wargame_cartographer.rendering.renderer import RenderContext


def render_label_layer(ax: plt.Axes, context: RenderContext):
    """Draw hex numbers and city name labels."""
    style = context.style
    grid = context.grid

    # Hex numbers
    if context.spec.show_hex_numbers:
        for (q, r), cell in grid.cells.items():
            number = grid.wargame_number(q, r)
            # Position at top of hex
            y_offset = grid.hex_radius_m * 0.65
            ax.text(
                cell.center_x,
                cell.center_y + y_offset,
                number,
                fontsize=style.hex_number_fontsize,
                color=style.hex_number_color,
                ha="center",
                va="center",
                fontfamily="sans-serif",
                fontweight="normal",
                zorder=6,
            )

    # City names
    if context.spec.show_cities and context.vector_data is not None:
        if hasattr(context.vector_data, 'cities') and not context.vector_data.cities.empty:
            transformer = grid._to_proj
            for _, city in context.vector_data.cities.iterrows():
                name = city.get("name", "") if hasattr(city, "get") else getattr(city, "name", "")
                if not name or not isinstance(name, str):
                    continue
                if hasattr(city.geometry, 'x'):
                    px, py = transformer.transform(city.geometry.x, city.geometry.y)
                    ax.text(
                        px,
                        py - grid.hex_radius_m * 0.4,
                        name,
                        fontsize=style.city_label_fontsize,
                        color=style.city_label_color,
                        ha="center",
                        va="top",
                        fontfamily="sans-serif",
                        fontweight="bold",
                        zorder=6,
                        bbox=dict(
                            facecolor="white",
                            alpha=0.7,
                            edgecolor="none",
                            pad=0.5,
                        ),
                    )
