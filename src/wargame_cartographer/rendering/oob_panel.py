"""Order of Battle side panel renderer."""

from __future__ import annotations

import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

from wargame_cartographer.rendering.renderer import RenderContext

SIDE_COLORS = {
    "blue": ("#3366CC", "Blue Forces"),
    "red": ("#CC3333", "Red Forces"),
    "green": ("#338833", "Neutral Forces"),
}


def render_oob_panel(ax: plt.Axes, context: RenderContext):
    """Render the Order of Battle panel on the given axes."""
    if not context.spec.oob_data:
        return

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Detect orientation: wide panel = bottom (horizontal), tall panel = side (vertical)
    bbox = ax.get_position()
    aspect = bbox.width / bbox.height if bbox.height > 0 else 1.0

    if aspect > 1.5:
        _render_horizontal(ax, context)
    else:
        _render_vertical(ax, context)


def _render_horizontal(ax: plt.Axes, context: RenderContext):
    """Render a wide horizontal bottom panel with side-by-side forces + commentary."""
    oob_data = context.spec.oob_data
    oob_commentary = getattr(context.spec, "oob_commentary", None)
    typo = context.style.typography

    # Panel background
    bg = Rectangle((0.01, 0.02), 0.98, 0.96,
                    facecolor="white", edgecolor="#666666",
                    linewidth=1.0, zorder=0)
    ax.add_patch(bg)

    # Title bar across top
    title_bar = Rectangle((0.01, 0.88), 0.98, 0.10,
                           facecolor="#2C3E50", edgecolor="none",
                           alpha=0.9, zorder=0.5)
    ax.add_patch(title_bar)

    ax.text(0.5, 0.93, "ORDER OF BATTLE",
            **typo.oob_title.mpl_kwargs(),
            ha="center", va="center", zorder=1)

    # Group entries by side
    sides: dict[str, list] = {}
    for entry in oob_data:
        sides.setdefault(entry.side, []).append(entry)

    blue_entries = sides.get("blue", [])
    red_entries = sides.get("red", [])
    other_entries = {k: v for k, v in sides.items() if k not in ("blue", "red")}

    # Layout columns
    has_commentary = bool(oob_commentary)
    if has_commentary:
        col_left = (0.02, 0.35)
        col_right = (0.36, 0.67)
        col_comment = (0.68, 0.98)
    else:
        col_left = (0.02, 0.49)
        col_right = (0.51, 0.98)
        col_comment = None

    if blue_entries:
        _draw_force_column(ax, blue_entries, "blue", col_left[0], col_left[1], 0.86, typo)

    if red_entries:
        _draw_force_column(ax, red_entries, "red", col_right[0], col_right[1], 0.86, typo)

    for side_key, entries in other_entries.items():
        _draw_force_column(ax, entries, side_key, col_right[0], col_right[1], 0.50, typo)

    if has_commentary and col_comment:
        _draw_commentary_column(ax, oob_commentary, col_comment[0], col_comment[1], typo)


def _draw_force_column(ax, entries, side_key, x_left, x_right, top_y, typo):
    """Draw a force column with header bar and unit listings."""
    color, label = SIDE_COLORS.get(side_key, ("#666666", side_key.capitalize()))
    col_w = x_right - x_left

    ts_side = typo.oob_side_header
    ts_formation = typo.oob_formation
    ts_unit = typo.oob_unit
    ts_notes = typo.oob_notes

    # Side header bar
    header_h = 0.05
    header_bg = Rectangle((x_left, top_y - header_h), col_w, header_h,
                            facecolor=color, alpha=0.15, edgecolor="none", zorder=0.5)
    ax.add_patch(header_bg)

    ax.text(x_left + 0.01, top_y - header_h * 0.5, label.upper(),
            fontsize=ts_side.fontsize, fontweight=ts_side.fontweight,
            fontfamily=ts_side.fontfamily, color=color,
            ha="left", va="center", zorder=1)

    cursor_y = top_y - header_h - 0.02
    line_h = 0.04
    unit_line_h = 0.035

    for entry in entries:
        if cursor_y < 0.06:
            break

        formation_text = entry.formation
        if entry.setup_turn > 1:
            formation_text += f"  (Turn {entry.setup_turn})"
        if entry.setup_zone:
            formation_text += f"  [{entry.setup_zone}]"

        ax.text(x_left + 0.01, cursor_y, formation_text,
                **ts_formation.mpl_kwargs(),
                ha="left", va="top", zorder=1)
        cursor_y -= line_h

        for unit in entry.units:
            if cursor_y < 0.06:
                break

            icon_x = x_left + 0.01
            icon_y = cursor_y - unit_line_h * 0.6
            icon_w, icon_h = 0.015, 0.02
            icon = Rectangle((icon_x, icon_y), icon_w, icon_h,
                              facecolor=color, edgecolor="black",
                              linewidth=0.4, zorder=1)
            ax.add_patch(icon)

            parts = [unit.designation]
            size_type = f"{unit.size} {unit.unit_type}".strip()
            if size_type:
                parts[0] += f" ({size_type})"
            if unit.combat_factor or unit.movement_factor:
                parts[0] += f" [{unit.combat_factor}-{unit.movement_factor}]"
            if getattr(unit, "strength", ""):
                parts[0] += f" — {unit.strength}"
            if unit.setup_hex:
                parts[0] += f"  @ {unit.setup_hex}"

            ax.text(x_left + 0.03, cursor_y, parts[0],
                    **ts_unit.mpl_kwargs(),
                    ha="left", va="top", zorder=1)
            cursor_y -= unit_line_h

        if entry.notes:
            ax.text(x_left + 0.02, cursor_y, entry.notes,
                    **ts_notes.mpl_kwargs(),
                    ha="left", va="top", zorder=1)
            cursor_y -= unit_line_h

        cursor_y -= 0.01


def _draw_commentary_column(ax, commentary, x_left, x_right, typo):
    """Draw the commentary column with wrapped paragraphs."""
    col_w = x_right - x_left
    ts_header = typo.oob_commentary_header
    ts_text = typo.oob_commentary_text

    header_h = 0.05
    top_y = 0.86
    header_bg = Rectangle((x_left, top_y - header_h), col_w, header_h,
                            facecolor="#555555", alpha=0.1, edgecolor="none", zorder=0.5)
    ax.add_patch(header_bg)

    ax.text(x_left + col_w * 0.5, top_y - header_h * 0.5, "COMMENTARY",
            **ts_header.mpl_kwargs(),
            ha="center", va="center", zorder=1)

    cursor_y = top_y - header_h - 0.02
    line_h = 0.03
    chars_per_line = max(30, int(col_w * 200))

    for paragraph in commentary:
        if cursor_y < 0.06:
            break
        wrapped = textwrap.wrap(paragraph, width=chars_per_line)
        for line in wrapped:
            if cursor_y < 0.06:
                break
            ax.text(x_left + 0.01, cursor_y, line,
                    **ts_text.mpl_kwargs(),
                    ha="left", va="top", zorder=1)
            cursor_y -= line_h
        cursor_y -= 0.01


def _render_vertical(ax: plt.Axes, context: RenderContext):
    """Render a tall vertical side panel (original stacked layout)."""
    oob_data = context.spec.oob_data
    typo = context.style.typography

    bg = Rectangle((0.02, 0.02), 0.96, 0.96,
                    facecolor="white", edgecolor="#666666",
                    linewidth=1.0, zorder=0)
    ax.add_patch(bg)

    ax.text(0.5, 0.96, "ORDER OF BATTLE",
            **typo.oob_v_title.mpl_kwargs(),
            ha="center", va="top", zorder=1)

    sides: dict[str, list] = {}
    for entry in oob_data:
        sides.setdefault(entry.side, []).append(entry)

    cursor_y = 0.90
    line_h = 0.025

    for side_key, entries in sides.items():
        color, label = SIDE_COLORS.get(side_key, ("#666666", side_key.capitalize()))

        header_bg = Rectangle((0.04, cursor_y - line_h * 0.8), 0.92, line_h * 1.2,
                               facecolor=color, alpha=0.15, edgecolor="none", zorder=0.5)
        ax.add_patch(header_bg)

        ax.text(0.06, cursor_y, label.upper(),
                fontsize=typo.oob_v_side_header.fontsize,
                fontweight=typo.oob_v_side_header.fontweight,
                fontfamily=typo.oob_v_side_header.fontfamily,
                color=color,
                ha="left", va="top", zorder=1)
        cursor_y -= line_h * 1.5

        for entry in entries:
            formation_text = entry.formation
            if entry.setup_turn > 1:
                formation_text += f"  (Turn {entry.setup_turn})"
            if entry.setup_zone:
                formation_text += f"  [{entry.setup_zone}]"

            ax.text(0.08, cursor_y, formation_text,
                    **typo.oob_v_formation.mpl_kwargs(),
                    ha="left", va="top", zorder=1)
            cursor_y -= line_h

            for unit in entry.units:
                icon_x, icon_y = 0.10, cursor_y - line_h * 0.3
                icon_w, icon_h = 0.025, 0.015
                icon = Rectangle((icon_x, icon_y), icon_w, icon_h,
                                  facecolor=color, edgecolor="black",
                                  linewidth=0.5, zorder=1)
                ax.add_patch(icon)

                unit_text = f"{unit.designation}"
                if unit.combat_factor or unit.movement_factor:
                    unit_text += f"  ({unit.combat_factor}-{unit.movement_factor})"
                if getattr(unit, "strength", ""):
                    unit_text += f" — {unit.strength}"
                if unit.setup_hex:
                    unit_text += f"  Hex {unit.setup_hex}"

                ax.text(0.14, cursor_y, unit_text,
                        **typo.oob_v_unit.mpl_kwargs(),
                        ha="left", va="top", zorder=1)
                cursor_y -= line_h

            if entry.notes:
                ax.text(0.10, cursor_y, entry.notes,
                        **typo.oob_v_notes.mpl_kwargs(),
                        ha="left", va="top", zorder=1)
                cursor_y -= line_h

            cursor_y -= line_h * 0.3

        cursor_y -= line_h * 0.5

    oob_commentary = getattr(context.spec, "oob_commentary", None)
    if oob_commentary:
        cursor_y -= line_h * 0.5
        ax.plot([0.04, 0.96], [cursor_y, cursor_y],
                color="#AAAAAA", linewidth=0.5, zorder=1)
        cursor_y -= line_h

        ax.text(0.5, cursor_y, "COMMENTARY",
                **typo.oob_v_commentary_header.mpl_kwargs(),
                ha="center", va="top", zorder=1)
        cursor_y -= line_h * 1.2

        for paragraph in oob_commentary:
            words = paragraph.split()
            line = ""
            for word in words:
                test = f"{line} {word}".strip()
                if len(test) > 55 and line:
                    ax.text(0.06, cursor_y, line,
                            **typo.oob_v_commentary_text.mpl_kwargs(),
                            ha="left", va="top", zorder=1)
                    cursor_y -= line_h * 0.8
                    line = word
                else:
                    line = test
            if line:
                ax.text(0.06, cursor_y, line,
                        **typo.oob_v_commentary_text.mpl_kwargs(),
                        ha="left", va="top", zorder=1)
                cursor_y -= line_h * 0.8
            cursor_y -= line_h * 0.3
