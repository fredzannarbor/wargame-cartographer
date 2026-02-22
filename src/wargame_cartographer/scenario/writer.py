"""Convert a ScenarioAnalysis into a MapSpec YAML and rationale document."""

from __future__ import annotations

from pathlib import Path

from wargame_cartographer.config.map_spec import BoundingBox, MapSpec, OOBEntry, OOBUnit
from wargame_cartographer.scenario.models import ScenarioAnalysis


def analysis_to_map_spec(analysis: ScenarioAnalysis) -> MapSpec:
    """Convert a ScenarioAnalysis to a complete, valid MapSpec."""
    margin_factor = 1.0 + analysis.margin_percent / 100.0
    effective_width = analysis.area_width_km * margin_factor
    effective_height = analysis.area_height_km * margin_factor

    bbox = BoundingBox.from_center(
        lat=analysis.center_lat,
        lon=analysis.center_lon,
        width_km=effective_width,
        height_km=effective_height,
    )

    subtitle_parts = []
    if analysis.date_range:
        subtitle_parts.append(analysis.date_range)
    if analysis.theater:
        subtitle_parts.append(analysis.theater)

    # Build OOB entries from forces, grouped by side
    oob_entries: list[OOBEntry] = []
    oob_commentary: list[str] = []

    if analysis.forces:
        sides: dict[str, list] = {}
        for f in analysis.forces:
            sides.setdefault(f.side, []).append(f)

        # Use "Blue"/"Red" as default formation labels — only use historical
        # names when they are well-known and unambiguous (e.g. Union/Confederate)
        default_labels = {"blue": "Blue", "red": "Red"}
        for side_key, forces in sides.items():
            units = [
                OOBUnit(
                    designation=f.designation,
                    unit_type=f.unit_type,
                    size=f.size,
                    strength=f.strength,
                    setup_hex=f.approximate_location,
                )
                for f in forces
            ]
            oob_entries.append(OOBEntry(
                side=side_key,
                formation=default_labels.get(side_key, side_key.capitalize()),
                units=units,
            ))

    # Build commentary from objectives
    if analysis.blue_objectives:
        oob_commentary.append(
            f"{analysis.blue_side_name} Objectives: " + "; ".join(analysis.blue_objectives)
        )
    if analysis.red_objectives:
        oob_commentary.append(
            f"{analysis.red_side_name} Objectives: " + "; ".join(analysis.red_objectives)
        )
    if analysis.bbox_rationale:
        oob_commentary.append(analysis.bbox_rationale)

    has_oob = bool(oob_entries)

    return MapSpec(
        name=analysis.scenario_name,
        title=analysis.scenario_name.upper(),
        subtitle=" — ".join(subtitle_parts) if subtitle_parts else "",
        scenario=f"{analysis.blue_side_name} vs {analysis.red_side_name}",
        bbox=bbox,
        designer_style=analysis.designer_style_recommendation,
        hex_size_km=analysis.recommended_hex_size_km,
        dpi=150,
        show_elevation_shading=True,
        show_rivers=analysis.show_rivers,
        show_roads=analysis.show_roads,
        show_railways=analysis.show_railways,
        show_cities=True,
        show_ports=analysis.show_ports,
        show_airfields=analysis.show_airfields,
        show_hex_numbers=True,
        show_legend=True,
        show_scale_bar=True,
        show_compass=True,
        show_oob_panel=has_oob,
        oob_panel_position="bottom",
        oob_panel_width_ratio=0.30,
        oob_data=oob_entries if oob_entries else None,
        oob_commentary=oob_commentary if oob_commentary else None,
        output_formats=["png", "html", "json"],
    )


def write_rationale(analysis: ScenarioAnalysis, path: Path) -> None:
    """Write a human-readable rationale document for the scenario analysis."""
    lines: list[str] = []

    lines.append(f"# {analysis.scenario_name} — Scenario Analysis")
    lines.append("")

    # Metadata
    lines.append("## Scenario")
    lines.append("")
    if analysis.date_range:
        lines.append(f"- **Date range:** {analysis.date_range}")
    if analysis.theater:
        lines.append(f"- **Theater:** {analysis.theater}")
    lines.append(
        f"- **Belligerents:** {analysis.blue_side_name} vs {analysis.red_side_name}"
    )
    lines.append("")

    # Objectives
    if analysis.blue_objectives or analysis.red_objectives:
        lines.append("## Objectives")
        lines.append("")
        if analysis.blue_objectives:
            lines.append(f"### {analysis.blue_side_name}")
            lines.append("")
            for obj in analysis.blue_objectives:
                lines.append(f"- {obj}")
            lines.append("")
        if analysis.red_objectives:
            lines.append(f"### {analysis.red_side_name}")
            lines.append("")
            for obj in analysis.red_objectives:
                lines.append(f"- {obj}")
            lines.append("")

    # Bounding box rationale
    lines.append("## Bounding Box Rationale")
    lines.append("")
    lines.append(
        f"- **Center:** {analysis.center_lat:.4f}N, {analysis.center_lon:.4f}E"
    )
    lines.append(
        f"- **Area:** {analysis.area_width_km:.0f} x {analysis.area_height_km:.0f} km"
    )
    lines.append(f"- **Margin:** {analysis.margin_percent:.0f}%")
    lines.append("")
    if analysis.bbox_rationale:
        lines.append(analysis.bbox_rationale)
        lines.append("")

    # Scale
    lines.append("## Scale Selection")
    lines.append("")
    lines.append(f"- **Scale:** {analysis.recommended_scale}")
    lines.append(f"- **Hex size:** {analysis.recommended_hex_size_km} km")
    lines.append("")
    if analysis.scale_rationale:
        lines.append(analysis.scale_rationale)
        lines.append("")

    # Key terrain
    if analysis.key_terrain:
        lines.append("## Key Terrain")
        lines.append("")
        lines.append(
            "| Name | Category | Lat | Lon | Significance |"
        )
        lines.append(
            "|------|----------|-----|-----|--------------|"
        )
        for pt in analysis.key_terrain:
            lines.append(
                f"| {pt.name} | {pt.category} | {pt.lat:.4f} | {pt.lon:.4f} | {pt.significance} |"
            )
        lines.append("")

    # Order of Battle
    if analysis.forces:
        lines.append("## Order of Battle")
        lines.append("")

        blue_forces = [f for f in analysis.forces if f.side == "blue"]
        red_forces = [f for f in analysis.forces if f.side == "red"]

        for side_name, forces in [
            (analysis.blue_side_name, blue_forces),
            (analysis.red_side_name, red_forces),
        ]:
            if forces:
                lines.append(f"### {side_name}")
                lines.append("")
                for f in forces:
                    off_map = " *(off-map)*" if f.is_off_map else ""
                    loc = f" — {f.approximate_location}" if f.approximate_location else ""
                    lines.append(
                        f"- **{f.designation}** ({f.size} {f.unit_type}){loc}{off_map}"
                    )
                lines.append("")

    # Style
    lines.append("## Style Recommendation")
    lines.append("")
    lines.append(f"- **Style:** {analysis.designer_style_recommendation}")
    lines.append("")
    if analysis.style_rationale:
        lines.append(analysis.style_rationale)
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
