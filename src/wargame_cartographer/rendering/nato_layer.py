"""NATO layer: professional unit counters and movement arrows."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.transforms import Bbox

from wargame_cartographer.rendering.renderer import RenderContext

# Expanded NATO unit type symbols
NATO_SYMBOLS = {
    "infantry": "X",
    "armor": "//",
    "artillery": "O",
    "cavalry": "/",
    "airborne": "^",
    "marine": "~",
    "mechanized": "X/",
    "headquarters": "HQ",
    "engineer": "E",
    "signal": "S",
    "medical": "+",
    "supply": "[]",
    "anti_armor": "//X",
    "air_defense": "ADA",
    "reconnaissance": "R",
    "special_forces": "SF",
    "air_fighter": "F",
    "air_bomber": "B",
    "air_helicopter": "H",
    "air_transport": "T",
    "naval_surface": "NS",
    "naval_submarine": "SUB",
    "naval_carrier": "CV",
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
    "green": ("#338833", "#FFFFFF"),
    "yellow": ("#CCAA33", "#000000"),
}


def _build_hex_lookup(grid) -> dict[str, tuple]:
    """Build hex_id -> (q, r, cell) lookup for fast access."""
    lookup = {}
    for (q, r), cell in grid.cells.items():
        hex_id = grid.wargame_number(q, r)
        lookup[hex_id] = (q, r, cell)
    return lookup


def _count_units_per_hex(units) -> dict[str, int]:
    """Count how many units are stacked in each hex."""
    counts: dict[str, int] = {}
    for unit in units:
        if unit.hex_id:
            counts[unit.hex_id] = counts.get(unit.hex_id, 0) + 1
    return counts


def render_nato_layer(ax: plt.Axes, context: RenderContext):
    """Draw NATO unit counters and movement arrows."""
    if context.spec.nato_units is None:
        return

    grid = context.grid
    r = grid.hex_radius_m
    hex_lookup = _build_hex_lookup(grid)

    # Counter dimensions based on hex proportion (Phase 0.2)
    hex_flat_to_flat = r * math.sqrt(3)
    counter_w = hex_flat_to_flat * context.spec.counter_hex_ratio
    counter_h = counter_w  # Square counters (wargame standard)

    # Font sizes scale with counter size
    fs = context.spec.font_scale
    symbol_fontsize = max(6.0, 9.0 * fs * (context.spec.counter_hex_ratio / 0.65))
    size_fontsize = max(5.0, 5.5 * fs * (context.spec.counter_hex_ratio / 0.65))
    desig_fontsize = max(5.0, 5.5 * fs * (context.spec.counter_hex_ratio / 0.65))
    factor_fontsize = max(5.0, 6.0 * fs * (context.spec.counter_hex_ratio / 0.65))

    # Track stacking: offset multiple units in same hex
    hex_stack_index: dict[str, int] = {}
    units_per_hex = _count_units_per_hex(context.spec.nato_units)

    has_shadow = getattr(context.style, 'counter_shadow', True)

    for unit in context.spec.nato_units:
        entry = hex_lookup.get(unit.hex_id)
        if entry is None:
            continue
        q, row, cell = entry

        # Stacking offset
        stack_idx = hex_stack_index.get(unit.hex_id, 0)
        hex_stack_index[unit.hex_id] = stack_idx + 1
        stack_offset_y = stack_idx * counter_h * 0.15

        cx = cell.center_x
        cy = cell.center_y + stack_offset_y

        bg_color, text_color = SIDE_COLORS.get(unit.side, SIDE_COLORS["blue"])

        # Drop shadow
        if has_shadow:
            shadow_offset = counter_w * 0.03
            shadow = FancyBboxPatch(
                (cx - counter_w / 2 + shadow_offset,
                 cy - counter_h / 2 - shadow_offset),
                counter_w, counter_h,
                boxstyle="round,pad=0.01",
                facecolor="#00000033",
                edgecolor="none",
                linewidth=0,
                zorder=8.0,
            )
            ax.add_patch(shadow)

        # Main counter box
        box = FancyBboxPatch(
            (cx - counter_w / 2, cy - counter_h / 2),
            counter_w, counter_h,
            boxstyle="round,pad=0.01",
            facecolor=bg_color,
            edgecolor="black",
            linewidth=1.5,
            zorder=8.5,
        )
        ax.add_patch(box)

        # Nationality stripe at top
        stripe_h = counter_h * 0.08
        stripe = Rectangle(
            (cx - counter_w / 2 + counter_w * 0.05,
             cy + counter_h / 2 - stripe_h - counter_h * 0.02),
            counter_w * 0.9, stripe_h,
            facecolor=bg_color,
            edgecolor="none",
            alpha=0.8,
            zorder=8.6,
        )
        ax.add_patch(stripe)

        # White symbol area (center box)
        sym_area_w = counter_w * 0.75
        sym_area_h = counter_h * 0.40
        sym_area = Rectangle(
            (cx - sym_area_w / 2, cy - sym_area_h / 2 + counter_h * 0.05),
            sym_area_w, sym_area_h,
            facecolor="white",
            edgecolor=bg_color,
            linewidth=0.5,
            zorder=8.7,
        )
        ax.add_patch(sym_area)

        # Unit type symbol (center of white area)
        symbol = NATO_SYMBOLS.get(unit.unit_type, "?")
        ax.text(
            cx, cy + counter_h * 0.05,
            symbol,
            fontsize=symbol_fontsize,
            color="black",
            ha="center", va="center",
            fontfamily="sans-serif",
            fontweight="bold",
            zorder=9,
        )

        # Size indicator above counter
        size_text = UNIT_SIZES.get(unit.size, "")
        if size_text:
            ax.text(
                cx, cy + counter_h / 2 + r * 0.06,
                size_text,
                fontsize=size_fontsize,
                color="black",
                ha="center", va="bottom",
                fontfamily="sans-serif",
                fontweight="bold",
                zorder=9,
                bbox=dict(facecolor="white", alpha=0.8, edgecolor="none", pad=0.3),
            )

        # Designation below counter
        ax.text(
            cx, cy - counter_h / 2 - r * 0.06,
            unit.designation,
            fontsize=desig_fontsize,
            color="black",
            ha="center", va="top",
            fontfamily="sans-serif",
            fontweight="bold",
            zorder=9,
            bbox=dict(facecolor="white", alpha=0.8, edgecolor="none", pad=0.3),
        )

        # Combat/movement factors (bottom of counter, inside the box)
        if unit.combat_factor > 0 or unit.movement_factor > 0:
            # Left: combat factor
            ax.text(
                cx - counter_w * 0.28,
                cy - counter_h * 0.32,
                str(unit.combat_factor),
                fontsize=factor_fontsize,
                color=text_color,
                ha="center", va="center",
                fontfamily="sans-serif",
                fontweight="bold",
                zorder=9,
            )
            # Separator dash
            ax.text(
                cx,
                cy - counter_h * 0.32,
                "-",
                fontsize=factor_fontsize * 0.8,
                color=text_color,
                ha="center", va="center",
                fontfamily="sans-serif",
                zorder=9,
            )
            # Right: movement factor
            ax.text(
                cx + counter_w * 0.28,
                cy - counter_h * 0.32,
                str(unit.movement_factor),
                fontsize=factor_fontsize,
                color=text_color,
                ha="center", va="center",
                fontfamily="sans-serif",
                fontweight="bold",
                zorder=9,
            )

    # Movement arrows
    if context.spec.movement_plans:
        for plan in context.spec.movement_plans:
            _draw_movement_arrow(ax, grid, plan, hex_lookup, r)


def _draw_movement_arrow(ax, grid, plan, hex_lookup, hex_radius):
    """Draw a movement arrow along a hex path."""
    if len(plan.hex_path) < 2:
        return

    color = "#CC0000"
    line_width = max(6.0, hex_radius * 0.15 / 1000)

    centers = []
    for hex_id in plan.hex_path:
        entry = hex_lookup.get(hex_id)
        if entry:
            _, _, cell = entry
            centers.append((cell.center_x, cell.center_y))

    if len(centers) < 2:
        return

    xs = [c[0] for c in centers]
    ys = [c[1] for c in centers]

    ax.plot(
        xs, ys,
        color=color,
        linewidth=line_width,
        alpha=0.85,
        zorder=8,
        solid_capstyle="round",
        solid_joinstyle="round",
    )

    # Arrowhead at end
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
        zorder=8,
    )
