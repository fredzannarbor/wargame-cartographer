"""CLI entry point for wargame-map command."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.group()
def main():
    """Wargame Cartographer — Generate playable wargame-style maps."""
    pass


@main.command()
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--verbose/--quiet", default=True)
def generate(spec_file: str, verbose: bool):
    """Generate a wargame map from a YAML spec file."""
    from wargame_cartographer.pipeline import run_pipeline

    spec_path = Path(spec_file)
    console.print(f"\n[bold]Wargame Cartographer[/bold] — {spec_path.name}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading spec...", total=None)

        def status_callback(msg: str):
            progress.update(task, description=msg)

        results = run_pipeline(spec_path, status_callback=status_callback)

    console.print(f"\n[bold green]Map generated successfully![/bold green]")
    console.print(f"  Hex count: {results['hex_count']}")
    console.print(f"  Terrain distribution:")
    for terrain, count in sorted(results.get("terrain_distribution", {}).items()):
        pct = count / results["hex_count"] * 100 if results["hex_count"] > 0 else 0
        console.print(f"    {terrain:12s} {count:4d} ({pct:.0f}%)")
    console.print()
    for fmt, path in results.get("output_files", {}).items():
        console.print(f"  {fmt:5s}: {path}")
    console.print()


@main.command()
@click.option("--name", required=True, help="Map name")
@click.option("--bbox", required=True, help="Bounding box: min_lon,min_lat,max_lon,max_lat")
@click.option("--hex-size", type=float, default=10.0, help="Hex size in km")
@click.option("--style", type=click.Choice(["simonitch", "simonsen", "kibler"]), default="simonitch")
@click.option("--output", type=click.Path(), default="./output")
@click.option("--formats", default="png,html,json", help="Comma-separated output formats")
def quick(name: str, bbox: str, hex_size: float, style: str, output: str, formats: str):
    """Quick-generate a map from command-line parameters."""
    from wargame_cartographer.config.map_spec import BoundingBox, MapSpec

    coords = [float(x.strip()) for x in bbox.split(",")]
    if len(coords) != 4:
        raise click.BadParameter("bbox must be min_lon,min_lat,max_lon,max_lat")

    spec = MapSpec(
        name=name,
        title=name.upper(),
        bbox=BoundingBox(
            min_lon=coords[0], min_lat=coords[1],
            max_lon=coords[2], max_lat=coords[3],
        ),
        hex_size_km=hex_size,
        designer_style=style,
        output_dir=Path(output),
        output_formats=[f.strip() for f in formats.split(",")],
    )

    # Write temp spec and run
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        spec.to_yaml(f.name)
        temp_path = Path(f.name)

    from wargame_cartographer.pipeline import run_pipeline

    console.print(f"\n[bold]Wargame Cartographer[/bold] — Quick Generate: {name}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating...", total=None)

        def status_callback(msg: str):
            progress.update(task, description=msg)

        results = run_pipeline(temp_path, status_callback=status_callback)

    console.print(f"\n[bold green]Map generated![/bold green]")
    console.print(f"  Hex count: {results['hex_count']}")
    for fmt, path in results.get("output_files", {}).items():
        console.print(f"  {fmt:5s}: {path}")
    console.print()

    temp_path.unlink(missing_ok=True)


@main.command()
def styles():
    """List available designer styles."""
    from wargame_cartographer.rendering.styles import STYLES

    for name, style in STYLES.items():
        console.print(f"\n[bold]{name}[/bold]")
        console.print(f"  Grid: {style.grid_color} ({style.grid_linewidth}px)")
        console.print(f"  Water: {style.water_color}")
        console.print(f"  Terrain colors:")
        for terrain, color in style.terrain_colors.items():
            console.print(f"    {terrain.value:12s} {color}")


@main.command(name="terrain-effects")
def terrain_effects():
    """List terrain types and their game effects."""
    from wargame_cartographer.terrain.types import TerrainType, TERRAIN_EFFECTS

    console.print("\n[bold]Terrain Effects Chart[/bold]\n")
    console.print(f"{'Terrain':12s} {'MP':>4s} {'Def':>5s} {'LOS':>5s}  Description")
    console.print("─" * 60)
    for tt in TerrainType:
        eff = TERRAIN_EFFECTS[tt]
        mp = str(eff.movement_cost) if eff.movement_cost < 99 else "N/A"
        console.print(
            f"{tt.value:12s} {mp:>4s} {eff.defensive_modifier:>+5d} "
            f"{'block' if eff.blocks_los else '  ok ':>5s}  {eff.description}"
        )
    console.print()


@main.command()
@click.argument("spec_file", type=click.Path(exists=True))
def validate(spec_file: str):
    """Validate a map spec YAML file."""
    from wargame_cartographer.config.map_spec import MapSpec

    try:
        spec = MapSpec.from_yaml(spec_file)
        console.print(f"[green]Valid![/green] {spec.name}")
        console.print(f"  BBox: {spec.bbox.min_lon:.2f},{spec.bbox.min_lat:.2f} → {spec.bbox.max_lon:.2f},{spec.bbox.max_lat:.2f}")
        console.print(f"  Coverage: {spec.bbox.width_km():.0f} x {spec.bbox.height_km():.0f} km")
        console.print(f"  Hex size: {spec.hex_size_km} km")
        console.print(f"  Style: {spec.designer_style}")
        console.print(f"  Output formats: {', '.join(spec.output_formats)}")
    except Exception as e:
        console.print(f"[red]Invalid:[/red] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
