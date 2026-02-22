"""Label layer: hex numbers and city names with collision avoidance."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt

from wargame_cartographer.rendering.renderer import RenderContext


def render_label_layer(ax: plt.Axes, context: RenderContext):
    """Draw hex numbers and city name labels with collision avoidance."""
    style = context.style
    grid = context.grid
    typo = style.typography

    # Track placed label bounding boxes for collision avoidance
    placed_bboxes: list[tuple[float, float, float, float]] = []

    # Hex numbers
    if context.spec.show_hex_numbers:
        ts = typo.hex_number
        for (q, r), cell in grid.cells.items():
            number = grid.wargame_number(q, r)
            hex_id = number

            # Default position: top of hex
            y_offset = grid.hex_radius_m * 0.65
            label_x = cell.center_x
            label_y = cell.center_y + y_offset
            fontsize = ts.fontsize
            label_alpha = 1.0

            # If counter occupies this hex, shift number to top-left corner
            if hex_id in context.occupied_hexes:
                label_x = cell.center_x - grid.hex_radius_m * 0.55
                label_y = cell.center_y + grid.hex_radius_m * 0.70
                fontsize = ts.fontsize * 0.85

            ax.text(
                label_x,
                label_y,
                number,
                fontsize=fontsize,
                color=ts.color,
                ha="center",
                va="center",
                fontfamily=ts.fontfamily,
                fontweight=ts.fontweight,
                zorder=6,
                bbox=dict(
                    facecolor="white",
                    alpha=0.6 if hex_id in context.occupied_hexes else 0.0,
                    edgecolor="none",
                    pad=0.2,
                ) if hex_id in context.occupied_hexes else None,
            )

    # City names with collision avoidance
    if context.spec.show_cities and context.vector_data is not None:
        if hasattr(context.vector_data, 'cities') and not context.vector_data.cities.empty:
            transformer = grid._to_proj
            r = grid.hex_radius_m
            ts_city = typo.city_label

            # 8 candidate offset positions (data coords)
            offsets = [
                (0, -r * 0.4),        # S (default - below)
                (0, r * 0.5),          # N
                (r * 0.5, 0),          # E
                (-r * 0.5, 0),         # W
                (r * 0.4, -r * 0.3),   # SE
                (-r * 0.4, -r * 0.3),  # SW
                (r * 0.4, r * 0.3),    # NE
                (-r * 0.4, r * 0.3),   # NW
            ]

            for _, city in context.vector_data.cities.iterrows():
                name = city.get("name", "") if hasattr(city, "get") else getattr(city, "name", "")
                if not name or not isinstance(name, str):
                    continue
                if not hasattr(city.geometry, 'x'):
                    continue

                px, py = transformer.transform(city.geometry.x, city.geometry.y)

                # Approximate label extent in data coords
                label_w = len(name) * r * 0.12
                label_h = r * 0.25

                # Try each offset position, pick first non-overlapping
                best_x, best_y = px + offsets[0][0], py + offsets[0][1]
                for dx, dy in offsets:
                    lx, ly = px + dx, py + dy
                    lbox = (lx - label_w / 2, ly - label_h / 2,
                            lx + label_w / 2, ly + label_h / 2)
                    if not _overlaps_any(lbox, placed_bboxes):
                        best_x, best_y = lx, ly
                        placed_bboxes.append(lbox)
                        break
                else:
                    best_x, best_y = px + offsets[0][0], py + offsets[0][1]
                    lbox = (best_x - label_w / 2, best_y - label_h / 2,
                            best_x + label_w / 2, best_y + label_h / 2)
                    placed_bboxes.append(lbox)

                ax.text(
                    best_x,
                    best_y,
                    name,
                    **ts_city.mpl_kwargs(),
                    ha="center",
                    va="top",
                    zorder=6,
                    bbox=dict(
                        facecolor="white",
                        alpha=0.7,
                        edgecolor="none",
                        pad=0.5,
                    ),
                )


def _overlaps_any(
    box: tuple[float, float, float, float],
    existing: list[tuple[float, float, float, float]],
) -> bool:
    """Check if a bounding box overlaps any existing bounding boxes."""
    x1, y1, x2, y2 = box
    for ex1, ey1, ex2, ey2 in existing:
        if x1 < ex2 and x2 > ex1 and y1 < ey2 and y2 > ey1:
            return True
    return False
