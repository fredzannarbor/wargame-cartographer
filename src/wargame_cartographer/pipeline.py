"""Main pipeline: MapSpec → Data → Grid → Terrain → Render → Export."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from wargame_cartographer.config.map_spec import MapSpec
from wargame_cartographer.geo.elevation import ElevationProcessor
from wargame_cartographer.geo.projection import select_crs
from wargame_cartographer.geo.vector import load_vector_data
from wargame_cartographer.hex.grid import HexGrid
from wargame_cartographer.hex.sampler import HexSampler
from wargame_cartographer.rendering.renderer import MapRenderer, RenderContext
from wargame_cartographer.rendering.styles import get_style


def run_pipeline(
    spec_path: str | Path,
    status_callback: Callable[[str], None] | None = None,
) -> dict:
    """Execute the full map generation pipeline.

    Returns a dict with:
        hex_count, terrain_distribution, output_files
    """

    def status(msg: str):
        if status_callback:
            status_callback(msg)

    # 1. Load spec
    status("Loading map specification...")
    spec = MapSpec.from_yaml(spec_path)
    style = get_style(spec.designer_style, font_scale=spec.font_scale)

    # 2. Select CRS and build hex grid
    status(f"Building hex grid ({spec.hex_size_km} km hexes)...")
    crs = select_crs(spec.bbox) if spec.crs is None else None
    grid = HexGrid(bbox=spec.bbox, hex_size_km=spec.hex_size_km, crs=crs)
    status(f"Grid ready: {grid.hex_count} hexes")

    # 3. Download geographic data
    status("Downloading geographic data...")
    vector_data = None
    try:
        vector_data = load_vector_data(spec.bbox, spec)
    except Exception as e:
        status(f"Vector data partially loaded: {e}")

    # 4. Get elevation data + hillshade
    status("Processing elevation data...")
    elev_proc = ElevationProcessor()
    elevation, elev_metadata = elev_proc.get_elevation(spec.bbox)
    hillshade = elev_proc.compute_hillshade(elevation) if spec.show_elevation_shading else None

    # 5. Classify terrain per hex
    status("Classifying terrain...")
    sampler = HexSampler()
    hex_terrain = sampler.build_hex_terrain(grid, spec.bbox, vector_data)

    # Terrain distribution
    terrain_counts = {}
    for info in hex_terrain.values():
        t = info["terrain"]
        name = t.value if hasattr(t, "value") else str(t)
        terrain_counts[name] = terrain_counts.get(name, 0) + 1

    # 6. Render
    status("Rendering map layers...")
    context = RenderContext(
        spec=spec,
        grid=grid,
        hex_terrain=hex_terrain,
        style=style,
        elevation=elevation,
        hillshade=hillshade,
        elevation_metadata=elev_metadata,
        vector_data=vector_data,
    )
    renderer = MapRenderer()
    fig = renderer.render(context)

    # 7. Export
    output_dir = Path(spec.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in spec.name)[:40].lower()

    output_files = {}

    if "png" in spec.output_formats:
        status("Exporting PNG...")
        from wargame_cartographer.output.static_exporter import export_png
        png_path = export_png(fig, output_dir / f"{safe_name}_map.png", dpi=spec.dpi)
        output_files["png"] = str(png_path.resolve())

    if "pdf" in spec.output_formats:
        status("Exporting PDF...")
        from wargame_cartographer.output.static_exporter import export_pdf
        pdf_path = export_pdf(fig, output_dir / f"{safe_name}_map.pdf")
        output_files["pdf"] = str(pdf_path.resolve())

    if "html" in spec.output_formats:
        status("Exporting interactive HTML...")
        from wargame_cartographer.output.html_exporter import export_html
        html_path = export_html(grid, hex_terrain, spec, output_dir / f"{safe_name}_interactive.html")
        output_files["html"] = str(html_path.resolve())

    if "json" in spec.output_formats:
        status("Exporting game data JSON...")
        from wargame_cartographer.output.game_data_exporter import export_game_data
        json_path = export_game_data(grid, hex_terrain, spec, output_dir / f"{safe_name}_hex_terrain.json")
        output_files["json"] = str(json_path.resolve())

    plt.close(fig)

    status("Done!")

    return {
        "hex_count": grid.hex_count,
        "terrain_distribution": terrain_counts,
        "output_files": output_files,
    }
