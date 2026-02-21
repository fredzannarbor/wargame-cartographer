# Wargame Cartographer

Generate historically accurate, playable wargame-style hex maps from real geographic data.

## Quick Start

```bash
uv sync
uv run wargame-map generate configs/examples/normandy_hex.yaml
uv run wargame-map quick --name "Gettysburg" --bbox "-77.30,39.78,-77.20,39.86" --hex-size 1
```

## Architecture

```
src/wargame_cartographer/
├── cli.py              # Click CLI: generate, quick, styles, validate, terrain-effects
├── pipeline.py         # Orchestrates: spec → data → grid → classify → render → export
├── config/
│   ├── map_spec.py     # Pydantic MapSpec + BoundingBox models
│   └── defaults.py     # Default values
├── geo/
│   ├── elevation.py    # SRTM tile download + hillshade (30-day cache)
│   ├── vector.py       # Natural Earth coastlines/rivers/cities + OSM Overpass
│   ├── downloader.py   # HTTP with caching to ~/.wargame-cartographer/cache/
│   └── projection.py   # UTM auto-projection from bbox center
├── hex/
│   ├── grid.py         # Flat-top hex grid generation in projected CRS
│   ├── sampler.py      # Sample elevation/land-use per hex → terrain type
│   └── geojson.py      # GeoJSON export of hex grid
├── terrain/
│   ├── types.py        # 8 terrain types with movement costs + defense modifiers
│   ├── classifier.py   # Elevation + land-use → terrain classification
│   └── palette.py      # Per-style color palettes
├── rendering/
│   ├── renderer.py     # Layer compositor (matplotlib)
│   ├── terrain_layer.py    # Hex fill colors + patterns (forest hatching, etc.)
│   ├── grid_layer.py       # Hex outlines + numbering
│   ├── elevation_layer.py  # Hillshade overlay
│   ├── vector_layer.py     # Coastlines, rivers, roads
│   ├── label_layer.py      # City/town labels
│   ├── nato_layer.py       # NATO unit symbols (counters)
│   ├── symbol_layer.py     # Map symbols
│   ├── cartouche_layer.py  # Title block / cartouche
│   └── styles.py           # 3 designer style definitions
└── output/
    ├── static_exporter.py    # PNG + PDF (matplotlib savefig)
    ├── html_exporter.py      # Interactive Folium/Leaflet map
    └── game_data_exporter.py # JSON with hex IDs, terrain, movement costs
```

## Workflow

1. **Write a YAML spec** (or use `quick` command with CLI flags)
2. **Run `generate`** — pipeline downloads geo data, builds hex grid, classifies terrain, renders layers, exports
3. **Output** goes to `./output/` — PNG, PDF, HTML, JSON as configured

## YAML Spec Format

```yaml
name: "Map Name"
title: "TITLE IN CAPS"
subtitle: "Optional subtitle"
scenario: "Historical context"

bbox:
  min_lon: -1.80
  min_lat: 48.80
  max_lon: 0.50
  max_lat: 49.80

designer_style: simonitch   # simonitch | simonsen | kibler
hex_size_km: 5.0
dpi: 300

show_elevation_shading: true
show_rivers: true
show_roads: false
show_railways: false
show_cities: true
show_ports: true
show_airfields: false
show_hex_numbers: true
show_legend: true
show_scale_bar: true
show_compass: true

output_formats: [png, html, json]
output_dir: ./output
```

## Designer Styles

- **simonitch** — GMT Games feel. Warm earth tones, muted greens, thin grid lines.
- **simonsen** — SPI/Avalon Hill feel. High contrast, bold colors, strong grid.
- **kibler** — Avalon Hill painterly feel. Saturated colors, organic textures.

## Terrain Types (8)

| Type | MP Cost | Defense | LOS Block |
|------|---------|---------|-----------|
| Clear | 1 | 0 | No |
| Forest | 2 | +1 | Yes |
| Rough | 2 | +1 | No |
| Mountain | 3 | +2 | Yes |
| Marsh | 3 | 0 | No |
| Urban | 1 | +2 | Yes |
| Water | Impassable | — | No |
| Coastal | 1 | 0 | No |

## External Data Sources

All auto-downloaded and cached at `~/.wargame-cartographer/cache/` (30-day TTL):

- **SRTM elevation** — ~90m resolution DEM tiles via rasterio/GDAL
- **Natural Earth 10m** — Coastlines, rivers, populated places (shapefile bundles)
- **OSM Overpass API** — Roads, railways, airfields, ports for the bbox

All degrade gracefully if unavailable (synthetic elevation, no coastlines, etc.).

## Well-Known Bounding Boxes

For natural-language requests, use these:

| Scenario | bbox (min_lon, min_lat, max_lon, max_lat) |
|----------|-------------------------------------------|
| Normandy 1944 | -1.80, 48.80, 0.50, 49.80 |
| Eastern Front | 20.0, 45.0, 42.0, 60.0 |
| Stalingrad | 43.8, 48.4, 44.8, 49.0 |
| Gettysburg | -77.30, 39.78, -77.20, 39.86 |
| Battle of the Bulge | 5.5, 49.5, 6.8, 50.5 |
| North Africa | -5.0, 28.0, 25.0, 38.0 |
| Pacific Theater | 90.0, -10.0, 180.0, 50.0 |

For other areas, estimate from geography or use OSM Nominatim.

## Scale Guidelines

- **Tactical** (1-5 km hexes): Individual battles, city fights
- **Operational** (5-25 km hexes): Campaigns, theater sectors
- **Strategic** (25-100+ km hexes): Entire fronts, continental scale

## Performance Notes

- First run for an area downloads ~50-200MB of geo data
- Large maps (1000+ hexes) take 1-3 minutes at 300 DPI
- Subsequent runs use cached data (fast)
- Max ~20 SRTM tiles per request

## Development

- Python 3.12+, managed with `uv`
- All source in `src/wargame_cartographer/`
- Example configs in `configs/examples/`
- No tests yet — validate with `uv run wargame-map validate <spec.yaml>`
