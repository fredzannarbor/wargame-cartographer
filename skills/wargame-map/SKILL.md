---
description: Generate Wargame-Style Maps
allowed-tools: Bash(*), Read, Write, Glob
argument-hint: [area or scenario] [--hex-size N] [--style simonitch|simonsen|kibler]
---

# /wargame-map - Generate Wargame-Style Maps

Generate historically accurate, playable wargame-style hex maps for any geographic area at any scale. Produces static PNG/PDF, interactive HTML, and game data JSON.

## Usage

```
/wargame-map <area or scenario description> [options]
/wargame-map --spec <yaml_file>
```

## Examples

- `/wargame-map Normandy 1944 --hex-size 5`
- `/wargame-map Eastern Front 1941 --hex-size 50 --style simonsen`
- `/wargame-map Stalingrad tactical --hex-size 1 --style kibler`
- `/wargame-map Persian Gulf --hex-size 25`
- `/wargame-map --spec configs/examples/normandy_hex.yaml`

## Prerequisites

This skill requires the `wargame-cartographer` Python package. On first use, clone and install:

```bash
git clone https://github.com/fredzannarbor/wargame-cartographer.git ~/wargame-cartographer
cd ~/wargame-cartographer
uv sync
```

## Implementation

When invoked, follow these steps:

### 1. Locate Installation

Find the wargame-cartographer installation:

```bash
# Check common locations
ls ~/wargame-cartographer/pyproject.toml 2>/dev/null || \
ls ./pyproject.toml 2>/dev/null
```

If not found, tell the user to install it first.

### 2. Ensure Dependencies

```bash
cd ~/wargame-cartographer
uv sync
```

### 3. Parse Input

If `--spec` is provided, use that YAML file directly:

```bash
cd ~/wargame-cartographer
uv run wargame-map generate <spec_file>
```

If natural language, construct a MapSpec YAML:

1. **Geocode the area**: Use the description to determine a bounding box. For well-known scenarios:
   - "Normandy 1944" → bbox: -1.80,48.80,0.50,49.80
   - "Eastern Front" → bbox: 20.0,45.0,42.0,60.0
   - "Stalingrad" → bbox: 43.8,48.4,44.8,49.0
   - "North Africa" → bbox: -5.0,28.0,25.0,38.0
   - "Pacific Theater" → bbox: 90.0,-10.0,180.0,50.0
   - "Gettysburg" → bbox: -77.30,39.78,-77.20,39.86
   - "Bulge" → bbox: 5.5,49.5,6.8,50.5
   - For other areas, use OSM Nominatim or estimate from geography knowledge

2. **Infer scale** from keywords:
   - "tactical" or hex-size < 5 → 1-5 km hexes
   - "operational" or default → 5-25 km hexes
   - "strategic" or hex-size > 25 → 25-100 km hexes

3. **Write YAML spec** to `/tmp/wargame_spec_{name}.yaml`:

```yaml
name: "Map Name"
title: "MAP TITLE"
subtitle: "Optional subtitle"
scenario: "Historical context"

bbox:
  min_lon: <float>
  min_lat: <float>
  max_lon: <float>
  max_lat: <float>

map_style: hex
designer_style: simonitch  # or simonsen, kibler
hex_size_km: 10.0

output_width_mm: 580
output_height_mm: 420
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

output_formats:
  - png
  - html
  - json

output_dir: ./output
```

4. **Run generator**:

```bash
cd ~/wargame-cartographer
uv run wargame-map generate /tmp/wargame_spec_{name}.yaml
```

### 4. Report Results

Tell the user:
- Map name, hex count, hex size, coverage area
- Terrain distribution summary
- Absolute paths to all output files (PNG, HTML, JSON)
- Any warnings (e.g., data unavailable, using synthetic elevation)

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--hex-size <km>` | 10 | Hex size in km |
| `--style <name>` | simonitch | Visual style |
| `--formats <list>` | png,html,json | Comma-separated output formats |
| `--output <dir>` | ./output | Output directory |
| `--spec <file>` | — | Use existing YAML spec file |
| `--dpi <int>` | 300 | Output resolution |
| `--title <text>` | (inferred) | Map title |

## Available Styles

| Style | Inspired By | Character |
|-------|------------|-----------|
| simonitch | GMT Games (Normandy '44, Ukraine '43) | Warm earth tones, muted greens, thin grid |
| simonsen | SPI/Avalon Hill (PanzerBlitz, Squad Leader) | High contrast, bold colors, strong grid |
| kibler | Avalon Hill (Third Reich, Breakout: Normandy) | Painterly, saturated, organic feel |

## Output Formats

| Format | Description |
|--------|------------|
| PNG | High-resolution static map image (300 DPI) |
| PDF | Vector map for print |
| HTML | Interactive Folium/Leaflet map with clickable hex tooltips |
| JSON | Game data: all hex IDs, terrain types, movement costs, elevation |

## Notes

- First run downloads elevation + vector data (~50-200MB), cached for 30 days
- Large maps (1000+ hexes) take 1-3 minutes to render at 300 DPI
- The JSON file is mechanically complete for wargame use
- Interactive HTML lets you click hexes to see terrain, MP cost, elevation
