"""Order of Battle side panel renderer."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

from wargame_cartographer.rendering.renderer import RenderContext

SIDE_COLORS = {
    "blue": ("#3366CC", "Allied Forces"),
    "red": ("#CC3333", "Axis Forces"),
    "green": ("#338833", "Neutral Forces"),
}


def render_oob_panel(ax: plt.Axes, context: RenderContext):
    """Render the Order of Battle panel on the given axes."""
    if not context.spec.oob_data:
        return

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    style = context.style
    oob_data = context.spec.oob_data

    # Panel background
    bg = Rectangle((0.02, 0.02), 0.96, 0.96,
                    facecolor="white", edgecolor="#666666",
                    linewidth=1.0, zorder=0)
    ax.add_patch(bg)

    # Title
    ax.text(0.5, 0.96, "ORDER OF BATTLE",
            fontsize=12, fontweight="bold", ha="center", va="top",
            fontfamily="sans-serif", zorder=1)

    # Group entries by side
    sides: dict[str, list] = {}
    for entry in oob_data:
        sides.setdefault(entry.side, []).append(entry)

    cursor_y = 0.90
    line_h = 0.025

    for side_key, entries in sides.items():
        color, label = SIDE_COLORS.get(side_key, ("#666666", side_key.capitalize()))

        # Side header
        header_bg = Rectangle((0.04, cursor_y - line_h * 0.8), 0.92, line_h * 1.2,
                               facecolor=color, alpha=0.15, edgecolor="none", zorder=0.5)
        ax.add_patch(header_bg)

        ax.text(0.06, cursor_y, label.upper(),
                fontsize=10, fontweight="bold", color=color,
                ha="left", va="top", fontfamily="sans-serif", zorder=1)
        cursor_y -= line_h * 1.5

        for entry in entries:
            # Formation header
            formation_text = entry.formation
            if entry.setup_turn > 1:
                formation_text += f"  (Turn {entry.setup_turn})"
            if entry.setup_zone:
                formation_text += f"  [{entry.setup_zone}]"

            ax.text(0.08, cursor_y, formation_text,
                    fontsize=8, fontweight="bold", color="#333333",
                    ha="left", va="top", fontfamily="sans-serif", zorder=1)
            cursor_y -= line_h

            # Units in this formation
            for unit in entry.units:
                # Mini counter icon
                icon_x, icon_y = 0.10, cursor_y - line_h * 0.3
                icon_w, icon_h = 0.025, 0.015
                icon = Rectangle((icon_x, icon_y), icon_w, icon_h,
                                  facecolor=color, edgecolor="black",
                                  linewidth=0.5, zorder=1)
                ax.add_patch(icon)

                # Unit info line
                unit_text = f"{unit.designation}"
                if unit.combat_factor or unit.movement_factor:
                    unit_text += f"  ({unit.combat_factor}-{unit.movement_factor})"
                if unit.setup_hex:
                    unit_text += f"  Hex {unit.setup_hex}"

                ax.text(0.14, cursor_y, unit_text,
                        fontsize=7, color="#444444",
                        ha="left", va="top", fontfamily="sans-serif", zorder=1)
                cursor_y -= line_h

            # Notes
            if entry.notes:
                ax.text(0.10, cursor_y, entry.notes,
                        fontsize=6, fontstyle="italic", color="#666666",
                        ha="left", va="top", fontfamily="sans-serif", zorder=1)
                cursor_y -= line_h

            cursor_y -= line_h * 0.3  # spacing between formations

        cursor_y -= line_h * 0.5  # spacing between sides
