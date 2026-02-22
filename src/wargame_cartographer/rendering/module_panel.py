"""Game module panels: CRT, TEC, sequence of play, custom tables."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from wargame_cartographer.rendering.renderer import RenderContext
from wargame_cartographer.terrain.types import TerrainType, TERRAIN_EFFECTS


def render_module_panels(ax: plt.Axes, context: RenderContext):
    """Render game module panels (CRT, TEC, etc.) on the given axes."""
    if not context.spec.module_panels:
        return

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Background
    bg = Rectangle((0.02, 0.02), 0.96, 0.96,
                    facecolor="white", edgecolor="#666666",
                    linewidth=1.0, zorder=0)
    ax.add_patch(bg)

    n_panels = len(context.spec.module_panels)
    panel_width = 0.92 / n_panels
    typo = context.style.typography

    for idx, panel in enumerate(context.spec.module_panels):
        panel_x = 0.04 + idx * panel_width

        if panel.panel_type == "crt":
            _render_crt(ax, context, panel_x, panel_width * 0.95, panel.title, typo)
        elif panel.panel_type == "tec":
            _render_tec(ax, context, panel_x, panel_width * 0.95, panel.title, typo)
        elif panel.panel_type == "sequence_of_play":
            _render_sequence(ax, context, panel_x, panel_width * 0.95, panel.title, typo)
        elif panel.panel_type == "custom" and panel.custom_data:
            _render_custom(ax, context, panel_x, panel_width * 0.95,
                          panel.title, panel.custom_data, typo)


def _render_crt(ax, context, x_start, width, title, typo):
    """Render a Combat Results Table."""
    title = title or "COMBAT RESULTS TABLE"
    ts_title = typo.panel_title
    ts_header = typo.panel_header
    ts_cell = typo.panel_cell
    ts_detail = typo.panel_detail

    ax.text(x_start + width / 2, 0.92, title,
            **ts_title.mpl_kwargs(), ha="center", va="top", zorder=1)

    odds = ["1:3", "1:2", "1:1", "2:1", "3:1", "4:1", "5:1", "6:1"]
    col_w = width / (len(odds) + 1)
    row_h = 0.06

    header_y = 0.85
    ax.text(x_start + col_w * 0.5, header_y, "Die",
            **ts_header.mpl_kwargs(), ha="center", va="center", zorder=1)

    for i, odd in enumerate(odds):
        cx = x_start + (i + 1.5) * col_w
        rect = Rectangle((cx - col_w / 2, header_y - row_h / 2), col_w, row_h,
                          facecolor="#DDDDDD", edgecolor="#999999",
                          linewidth=0.3, zorder=0.5)
        ax.add_patch(rect)
        ax.text(cx, header_y, odd,
                **ts_cell.mpl_kwargs(), fontweight="bold",
                ha="center", va="center", zorder=1)

    results = [
        ["AE", "AE", "AR", "DR", "DR", "DE", "DE", "DE"],
        ["AE", "AR", "AR", "DR", "DR", "DE", "DE", "DE"],
        ["AR", "AR", "EX", "EX", "DR", "DR", "DE", "DE"],
        ["AR", "AR", "EX", "EX", "DR", "DR", "DR", "DE"],
        ["NE", "AR", "AR", "EX", "EX", "DR", "DR", "DR"],
        ["NE", "NE", "AR", "AR", "EX", "EX", "DR", "DR"],
    ]

    result_colors = {
        "AE": "#FFCCCC",
        "AR": "#FFE0CC",
        "EX": "#FFFFCC",
        "DR": "#CCFFCC",
        "DE": "#CCCCFF",
        "NE": "#EEEEEE",
    }

    for row_idx, row_results in enumerate(results):
        y = header_y - (row_idx + 1) * row_h
        die_val = row_idx + 1

        ax.text(x_start + col_w * 0.5, y, str(die_val),
                **ts_header.mpl_kwargs(), ha="center", va="center", zorder=1)

        for col_idx, result in enumerate(row_results):
            cx = x_start + (col_idx + 1.5) * col_w
            bg_color = result_colors.get(result, "#FFFFFF")
            alt_alpha = 0.9 if row_idx % 2 == 0 else 0.7
            rect = Rectangle((cx - col_w / 2, y - row_h / 2), col_w, row_h,
                              facecolor=bg_color, edgecolor="#CCCCCC",
                              linewidth=0.3, alpha=alt_alpha, zorder=0.5)
            ax.add_patch(rect)
            ax.text(cx, y, result,
                    **ts_cell.mpl_kwargs(), ha="center", va="center", zorder=1)

    legend_y = header_y - (len(results) + 1.5) * row_h
    legend_items = [
        ("AE", "Attacker Eliminated"),
        ("AR", "Attacker Retreats"),
        ("EX", "Exchange"),
        ("DR", "Defender Retreats"),
        ("DE", "Defender Eliminated"),
        ("NE", "No Effect"),
    ]
    for i, (code, desc) in enumerate(legend_items):
        lx = x_start + (i % 3) * width * 0.33
        ly = legend_y - (i // 3) * row_h * 0.8
        color = result_colors.get(code, "#FFFFFF")
        swatch = Rectangle((lx, ly - row_h * 0.2), width * 0.03, row_h * 0.4,
                            facecolor=color, edgecolor="#999999",
                            linewidth=0.3, zorder=0.5)
        ax.add_patch(swatch)
        ax.text(lx + width * 0.04, ly, f"{code} = {desc}",
                **ts_detail.mpl_kwargs(), ha="left", va="center", zorder=1)


def _render_tec(ax, context, x_start, width, title, typo):
    """Render a Terrain Effects Chart from TERRAIN_EFFECTS."""
    title = title or "TERRAIN EFFECTS CHART"
    ts_title = typo.panel_title
    ts_header = typo.panel_header
    ts_cell = typo.panel_cell

    ax.text(x_start + width / 2, 0.92, title,
            **ts_title.mpl_kwargs(), ha="center", va="top", zorder=1)

    style = context.style
    col_headers = ["Terrain", "MP Cost", "Defense", "LOS Block"]
    col_widths = [0.30, 0.20, 0.20, 0.30]
    row_h = 0.055

    header_y = 0.85
    cx = x_start
    for header, cw in zip(col_headers, col_widths):
        cell_w = width * cw
        rect = Rectangle((cx, header_y - row_h / 2), cell_w, row_h,
                          facecolor="#DDDDDD", edgecolor="#999999",
                          linewidth=0.3, zorder=0.5)
        ax.add_patch(rect)
        ax.text(cx + cell_w / 2, header_y, header,
                **ts_header.mpl_kwargs(), ha="center", va="center", zorder=1)
        cx += cell_w

    terrains = sorted(TERRAIN_EFFECTS.keys(), key=lambda t: t.value)
    for row_idx, terrain in enumerate(terrains):
        effects = TERRAIN_EFFECTS[terrain]
        y = header_y - (row_idx + 1) * row_h
        color = style.terrain_colors.get(terrain, "#CCCCCC")

        values = [
            terrain.value.capitalize(),
            str(effects.movement_cost) if effects.movement_cost < 99 else "Impass.",
            f"{effects.defensive_modifier:+d}" if effects.defensive_modifier else "0",
            "Yes" if effects.blocks_los else "No",
        ]

        cx = x_start
        for col_idx, (val, cw) in enumerate(zip(values, col_widths)):
            cell_w = width * cw
            bg = color if col_idx == 0 else ("#F8F8F8" if row_idx % 2 == 0 else "#FFFFFF")
            rect = Rectangle((cx, y - row_h / 2), cell_w, row_h,
                              facecolor=bg, edgecolor="#CCCCCC",
                              linewidth=0.3, zorder=0.5)
            ax.add_patch(rect)
            ax.text(cx + cell_w / 2, y, val,
                    **ts_cell.mpl_kwargs(), ha="center", va="center", zorder=1)
            cx += cell_w


def _render_sequence(ax, context, x_start, width, title, typo):
    """Render a Sequence of Play panel."""
    title = title or "SEQUENCE OF PLAY"
    ts_title = typo.panel_title
    ts_num = typo.panel_phase_number
    ts_name = typo.panel_phase_name
    ts_desc = typo.panel_phase_desc

    ax.text(x_start + width / 2, 0.92, title,
            **ts_title.mpl_kwargs(), ha="center", va="top", zorder=1)

    phases = [
        ("1.", "Initial Phase", "Check supply, weather, reinforcements"),
        ("2.", "Movement Phase", "Move units up to movement allowance"),
        ("3.", "Combat Phase", "Resolve attacks (odds-ratio CRT)"),
        ("4.", "Exploitation Phase", "Mechanized/armor exploitation movement"),
        ("5.", "Clean Up Phase", "Remove markers, advance turn counter"),
    ]

    row_h = 0.06
    for i, (num, phase, desc) in enumerate(phases):
        y = 0.82 - i * row_h * 1.5

        ax.text(x_start + 0.02, y, num,
                **ts_num.mpl_kwargs(), ha="left", va="top", zorder=1)
        ax.text(x_start + 0.06, y, phase,
                **ts_name.mpl_kwargs(), ha="left", va="top", zorder=1)
        ax.text(x_start + 0.06, y - row_h * 0.5, desc,
                **ts_desc.mpl_kwargs(), ha="left", va="top", zorder=1)


def _render_custom(ax, context, x_start, width, title, data, typo):
    """Render a custom data panel from YAML-provided content."""
    title = title or "REFERENCE"
    ts_title = typo.panel_title
    ts_cell = typo.panel_header

    ax.text(x_start + width / 2, 0.92, title,
            **ts_title.mpl_kwargs(), ha="center", va="top", zorder=1)

    rows = data.get("rows", [])
    row_h = 0.04

    for i, row_data in enumerate(rows):
        y = 0.85 - i * row_h
        if isinstance(row_data, str):
            ax.text(x_start + 0.02, y, row_data,
                    **ts_cell.mpl_kwargs(fontweight="normal"),
                    ha="left", va="top", zorder=1)
        elif isinstance(row_data, dict):
            text = row_data.get("text", "")
            bold = row_data.get("bold", False)
            ax.text(x_start + 0.02, y, text,
                    **ts_cell.mpl_kwargs(fontweight="bold" if bold else "normal"),
                    ha="left", va="top", zorder=1)
