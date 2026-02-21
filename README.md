# Wargame Cartographer

Generate historically accurate, playable wargame-style hex maps for any geographic area at any scale.

## Features

- Hex grid generation with terrain classification from real geographic data
- Elevation data with hillshade rendering
- Three designer styles inspired by classic wargame publishers
- Multiple output formats: PNG, PDF, interactive HTML, game data JSON
- Natural language input — just describe the area and scale

## Claude Code Plugin

Install as a Claude Code plugin for the `/wargame-map` slash command:

```
/install-plugin fredzannarbor/wargame-cartographer
```

Then use it:

```
/wargame-map Normandy 1944 --hex-size 5
/wargame-map Eastern Front 1941 --hex-size 50 --style simonsen
/wargame-map Stalingrad tactical --hex-size 1 --style kibler
```

## Standalone Installation

```bash
git clone https://github.com/fredzannarbor/wargame-cartographer.git
cd wargame-cartographer
uv sync
```

### CLI Usage

```bash
# From a YAML spec file
uv run wargame-map generate configs/examples/normandy_hex.yaml

# Quick generate from command line
uv run wargame-map quick --name "Gettysburg" --bbox "-77.30,39.78,-77.20,39.86" --hex-size 1 --style simonitch

# List available styles
uv run wargame-map styles

# View terrain effects chart
uv run wargame-map terrain-effects
```

## Designer Styles

| Style | Inspired By | Character |
|-------|------------|-----------|
| **simonitch** | GMT Games (Normandy '44, Ukraine '43) | Warm earth tones, muted greens, thin grid |
| **simonsen** | SPI/Avalon Hill (PanzerBlitz, Squad Leader) | High contrast, bold colors, strong grid |
| **kibler** | Avalon Hill (Third Reich, Breakout: Normandy) | Painterly, saturated, organic feel |

## Output Formats

| Format | Description |
|--------|------------|
| **PNG** | High-resolution static map image (300 DPI) |
| **PDF** | Vector map for print |
| **HTML** | Interactive Folium/Leaflet map with clickable hex tooltips |
| **JSON** | Game data with hex IDs, terrain types, movement costs, elevation |

## Example Spec (YAML)

```yaml
name: "Normandy 1944"
title: "OVERLORD"
subtitle: "D-Day to the Breakout"
scenario: "June 6 - August 25, 1944"

bbox:
  min_lon: -1.80
  min_lat: 48.80
  max_lon: 0.50
  max_lat: 49.80

designer_style: simonitch
hex_size_km: 5.0
dpi: 300

show_elevation_shading: true
show_rivers: true
show_cities: true
show_hex_numbers: true
show_legend: true

output_formats: [png, html, json]
output_dir: ./output
```

## License

MIT
