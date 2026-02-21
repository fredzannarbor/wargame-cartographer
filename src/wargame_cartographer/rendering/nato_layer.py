"""NATO layer: unit counters and movement arrows (optional)."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.transforms import Bbox

from wargame_cartographer.rendering.renderer import RenderContext

# NATO unit type symbols (simplified)
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
    "blue": ("#3366CC", "#FFFFFF"),
    "red": ("#CC3333", "#FFFFFF"),
}


def _build_hex_lookup(grid) -> dict[str, tuple]:
    """Build hex_id → (q, r, cell) lookup for fast access."""
    lookup = {}
    for (q, r), cell in grid.cells.items():
        hex_id = grid.wargame_number(q, r)
        lookup[hex_id] = (q, r, cell)
    return lookup


def render_nato_layer(ax: plt.Axes, context: RenderContext):
    """Draw NATO unit counters and movement arrows."""
    if context.spec.nato_units is None:
        return

    grid = context.grid
    r = grid.hex_radius_m
    hex_lookup = _build_hex_lookup(grid)

    # Counter dimensions — fill most of the hex
    counter_w = r * 1.2
    counter_h = r * 0.85

    # Font sizes scale with font_scale from spec
    fs = context.spec.font_scale
    symbol_fontsize = 8 * fs
    size_fontsize = 5.5 * fs
    desig_fontsize = 5 * fs

    for unit in context.spec.nato_units:
        entry = hex_lookup.get(unit.hex_id)
        if entry is None:
            continue
        q, row, cell = entry

        bg_color, text_color = SIDE_COLORS.get(unit.side, SIDE_COLORS["blue"])

        # Counter box
        box = FancyBboxPatch(
            (cell.center_x - counter_w / 2, cell.center_y - counter_h / 2),
            counter_w, counter_h,
            boxstyle="round,pad=0.01",
            facecolor=bg_color,
            edgecolor="black",
            linewidth=1.5,
            zorder=7,
        )
        ax.add_patch(box)

        # Unit type symbol (center of counter)
        symbol = NATO_SYMBOLS.get(unit.unit_type, "?")
        ax.text(
            cell.center_x, cell.center_y + counter_h * 0.05,
            symbol,
            fontsize=symbol_fontsize,
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
                cell.center_x, cell.center_y + counter_h / 2 + r * 0.08,
                size_text,
                fontsize=size_fontsize,
                color="black",
                ha="center", va="bottom",
                fontfamily="sans-serif",
                fontweight="bold",
                zorder=8,
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=0.3),
            )

        # Designation below counter
        ax.text(
            cell.center_x, cell.center_y - counter_h / 2 - r * 0.08,
            unit.designation,
            fontsize=desig_fontsize,
            color="black",
            ha="center", va="top",
            fontfamily="sans-serif",
            fontweight="bold",
            zorder=8,
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=0.3),
        )

        # Combat/movement factors (bottom corners of counter)
        if unit.combat_factor > 0 or unit.movement_factor > 0:
            factor_fs = desig_fontsize * 0.85
            # Combat factor (left)
            ax.text(
                cell.center_x - counter_w * 0.3,
                cell.center_y - counter_h * 0.3,
                str(unit.combat_factor),
                fontsize=factor_fs,
                color=text_color,
                ha="center", va="center",
                fontfamily="sans-serif",
                zorder=8,
            )
            # Movement factor (right)
            ax.text(
                cell.center_x + counter_w * 0.3,
                cell.center_y - counter_h * 0.3,
                str(unit.movement_factor),
                fontsize=factor_fs,
                color=text_color,
                ha="center", va="center",
                fontfamily="sans-serif",
                zorder=8,
            )

    # Movement arrows
    if context.spec.movement_plans:
        for plan in context.spec.movement_plans:
            _draw_movement_arrow(ax, grid, plan, hex_lookup, r)


def _draw_movement_arrow(ax, grid, plan, hex_lookup, hex_radius):
    """Draw a movement arrow along a hex path — thick red arrows."""
    if len(plan.hex_path) < 2:
        return

    # Always red for movement arrows — highly visible
    color = "#CC0000"
    line_width = max(6.0, hex_radius * 0.15 / 1000)  # Scale with hex size, min 6pt

    centers = []
    for hex_id in plan.hex_path:
        entry = hex_lookup.get(hex_id)
        if entry:
            _, _, cell = entry
            centers.append((cell.center_x, cell.center_y))

    if len(centers) < 2:
        return

    # Draw thick red line through all waypoints
    xs = [c[0] for c in centers]
    ys = [c[1] for c in centers]

    ax.plot(
        xs, ys,
        color=color,
        linewidth=line_width,
        alpha=0.85,
        zorder=6.5,
        solid_capstyle="round",
        solid_joinstyle="round",
    )

    # Large arrowhead at the end
    dx = centers[-1][0] - centers[-2][0]
    dy = centers[-1][1] - centers[-2][1]
    ax.annotate(
        "",
        xy=centers[-1],
        xytext=(centers[-1][0] - dx * 0.3, centers[-1][1] - dy * 0.3),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=line_width,
            mutation_scale=40,
        ),
        zorder=6.5,
    )
