"""NATO layer: unit counters and movement arrows (optional)."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from wargame_cartographer.rendering.renderer import RenderContext

# NATO unit type symbols (simplified single-character versions)
NATO_SYMBOLS = {
    "infantry": "X",
    "armor": "//",
    "artillery": "O",
    "cavalry": "/",
    "airborne": "^",
    "marine": "~",
    "mechanized": "X/",
    "headquarters": "HQ",
}

# Unit size indicators
UNIT_SIZES = {
    "squad": ".",
    "platoon": "..",
    "company": "|",
    "battalion": "||",
    "regiment": "|||",
    "brigade": "X",
    "division": "XX",
    "corps": "XXX",
    "army": "XXXX",
}

SIDE_COLORS = {
    "blue": ("#3366CC", "#FFFFFF"),  # bg, text
    "red": ("#CC3333", "#FFFFFF"),
}


def render_nato_layer(ax: plt.Axes, context: RenderContext):
    """Draw NATO unit counters and movement arrows."""
    if context.spec.nato_units is None:
        return

    grid = context.grid
    r = grid.hex_radius_m

    for unit in context.spec.nato_units:
        # Find hex for this unit
        hex_id = unit.hex_id
        cell = None
        for (q, row), c in grid.cells.items():
            if grid.wargame_number(q, row) == hex_id:
                cell = c
                break
        if cell is None:
            continue

        bg_color, text_color = SIDE_COLORS.get(unit.side, SIDE_COLORS["blue"])

        # Draw counter box
        counter_w = r * 0.8
        counter_h = r * 0.6
        box = FancyBboxPatch(
            (cell.center_x - counter_w / 2, cell.center_y - counter_h / 2),
            counter_w, counter_h,
            boxstyle="round,pad=0.02",
            facecolor=bg_color,
            edgecolor="black",
            linewidth=1.0,
            zorder=7,
        )
        ax.add_patch(box)

        # Unit type symbol
        symbol = NATO_SYMBOLS.get(unit.unit_type, "?")
        ax.text(
            cell.center_x, cell.center_y,
            symbol,
            fontsize=max(3, r * 0.003),
            color=text_color,
            ha="center", va="center",
            fontfamily="sans-serif",
            fontweight="bold",
            zorder=8,
        )

        # Size indicator above counter
        size_text = UNIT_SIZES.get(unit.size, "")
        if size_text:
            ax.text(
                cell.center_x, cell.center_y + counter_h / 2 + r * 0.05,
                size_text,
                fontsize=max(2, r * 0.002),
                color="black",
                ha="center", va="bottom",
                fontfamily="sans-serif",
                zorder=8,
            )

        # Designation below counter
        ax.text(
            cell.center_x, cell.center_y - counter_h / 2 - r * 0.05,
            unit.designation,
            fontsize=max(2, r * 0.002),
            color="black",
            ha="center", va="top",
            fontfamily="sans-serif",
            fontweight="bold",
            zorder=8,
        )

    # Movement arrows
    if context.spec.movement_plans:
        for plan in context.spec.movement_plans:
            _draw_movement_arrow(ax, grid, plan)


def _draw_movement_arrow(ax, grid, plan):
    """Draw a movement arrow along a hex path."""
    if len(plan.hex_path) < 2:
        return

    color = "#3366CC" if plan.side == "blue" else "#CC3333"

    # Find cell centers for the path
    centers = []
    for hex_id in plan.hex_path:
        for (q, r), cell in grid.cells.items():
            if grid.wargame_number(q, r) == hex_id:
                centers.append((cell.center_x, cell.center_y))
                break

    if len(centers) < 2:
        return

    # Draw arrow segments
    for i in range(len(centers) - 1):
        start = centers[i]
        end = centers[i + 1]
        is_last = i == len(centers) - 2

        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops=dict(
                arrowstyle="->" if is_last else "-",
                color=color,
                lw=2.0,
                connectionstyle="arc3,rad=0.1",
            ),
            zorder=7,
        )
