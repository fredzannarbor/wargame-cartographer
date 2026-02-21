# Plan: Dramatically Improve Cartography & Counter Design

## Research Summary

### State of the Art — Hex Map Cartography

The gold standard for wargame hex maps comes from designers like **Mark Simonitch** (GMT Games) and **Redmond Simonsen** (SPI). Key qualities:

- **Terrain texture variety**: Multiple visual cues per terrain type — fill color + hatching + organic decorations + subtle texture gradients
- **Coastline fidelity**: Real geographic coastline geometry clipped at hex boundaries (not just colored hexes)
- **Elevation subtlety**: Hillshade as gentle atmospheric depth, not overpowering; combined with contour hints
- **Road/river hierarchy**: Major roads thick/brown, minor roads thin/dashed; rivers vary by stream order
- **City prominence scaling**: Capital cities larger than villages; ports/airfields get distinct symbols
- **Label legibility**: Anti-collision placement, halo/outline effects, font hierarchy
- **Map furniture**: Professional cartouche with title block, terrain effects chart, scale bar, compass rose, coordinate ticks

### State of the Art — Counter Design

From WargameHQ, Codex99, and NATO MIL-STD-2525/APP-6 standards:

- **Standard layout**: NATO unit symbol centered, size echelon on top, attack-defense-movement values on bottom, designation below counter
- **True NATO symbol frames**: Rectangle (friendly), diamond (hostile), with proper fill colors per affiliation
- **Affiliation color coding**: Blue = friendly, Red = hostile, Green = neutral, Yellow = unknown
- **Crisp vector rendering**: Symbols as SVG paths, not text approximations. Black on white symbol area for maximum legibility
- **Typography hierarchy**: Bold values for combat factors, smaller italic for designation, clear unit-size indicators (I, II, III, X, XX, XXX)
- **Counter chrome**: Rounded corners, subtle drop shadow or beveled edge, nationality stripe/flag
- **Information density**: Support for 2-step (Attack-Defense) or 3-step (Attack-Defense-Movement) value display
- **Status indicators**: Reduced strength (flip side), disrupted, out of supply shown via overlays

### Available Python Libraries

| Library | Purpose | Notes |
|---------|---------|-------|
| `military-symbol` | NATO APP-6(E) SVG symbols | Full SIDC support, light/medium/dark/unfilled |
| `drawsvg` | Programmatic SVG generation | Good for compositing counter elements |
| `CairoSVG` | SVG → PNG/PDF conversion | High quality rasterization |
| `svgwrite` | SVG file creation | Lightweight, pure Python |
| `matplotlib` (current) | Already in use | Good for map layers, limited for counters |

---

## Current State Assessment

The codebase exploration reveals a **solid, well-architected system** at ~70% completion:

### Strengths (keep as-is)
- Excellent modular layer architecture
- Sophisticated coastal contour rendering (real geometry clipping)
- Three distinct designer styles (Simonitch/Simonsen/Kibler)
- Good terrain decorations for forest/urban/rough
- Comprehensive cartouche with game-mechanics-integrated legend
- Deterministic pseudo-random terrain classification

### Weaknesses (to fix)

| Issue | Current | Target |
|-------|---------|--------|
| Terrain hatching | Defined in styles but **never rendered** | Apply hatches to terrain fills |
| Terrain decorations | Only 3 of 8 types decorated | All 8 types with organic decorations |
| NATO symbols | Text-based ("X", "//", "O") | True vector NATO symbols with frames |
| Unit types | 8 basic types | 20+ types including air/naval/support |
| Counter rendering | `FancyBboxPatch` with text | Professional SVG counters with proper layout |
| Hillshade azimuth | Defined in style, never applied | Pass style azimuth/altitude to computation |
| Road/river hierarchy | Single width for all | Scale by importance/stream order |
| City markers | All same size | Scale by population/importance |
| Label collision | None | Basic overlap avoidance |
| Counter information | Symbol + 2 values | Full layout: symbol, echelon, values, designation, status |

---

## Implementation Plan

### Phase 0: Foundational Readability & Sizing (Must-fix before visual enhancements)

These are the baseline requirements that determine whether the map is actually *usable* as a wargame product. All subsequent phases depend on getting these right.

#### 0.1 Hex Readability — Minimum Pixel Size Enforcement

**Problem**: Currently, hex size in pixels is purely a side-effect of `hex_size_km`, `output_width_mm`, and `dpi`. A 1km hex on a strategic-scale map may render at ~15px across — far too small for hex numbers, terrain decorations, or counter placement. There is no check or warning.

**Solution**:
- **File**: `src/wargame_cartographer/rendering/renderer.py`, `src/wargame_cartographer/config/map_spec.py`
- Add `min_hex_px` setting to `MapSpec` (default: 40). This is the minimum flat-to-flat pixel width for a hex to be considered readable.
- In `MapRenderer.render()`, compute actual px-per-hex. If below threshold:
  1. Emit a warning log
  2. Auto-scale `font_scale` downward for labels/hex numbers (so they still fit)
  3. Optionally skip decorations (trees, urban grid) that would become unreadable noise
- Add a `hex_readability_report()` method to `HexGrid` or `MapRenderer` that returns px/hex, and flags "too small" / "optimal" / "large"
- **Optimal hex sizes** (guidelines enforced as warnings, not hard limits):
  - **Minimum readable**: 40px flat-to-flat (hex numbers visible, no decorations)
  - **Good for play**: 60-80px (hex numbers, terrain texture, counter fits)
  - **Ideal**: 80-120px (full detail: decorations, labels, counters, stacking)

#### 0.2 Counter-to-Hex Proportion

**Problem**: Counter dimensions are currently `r * 1.2` wide × `r * 0.85` tall (where r = hex_radius_m). This is in *data coordinates* (meters), which is correct for placement, but there's no check that the resulting pixel size is readable. Also, counters wider than the hex flat-to-flat distance (`r * sqrt(3)`) will overlap neighboring hexes.

**Solution**:
- **File**: `src/wargame_cartographer/rendering/nato_layer.py`, `src/wargame_cartographer/config/map_spec.py`
- Add `counter_hex_ratio` to `MapSpec` (default: 0.65). This controls counter width as a fraction of hex flat-to-flat distance.
  - 0.5 = small counters, room for stacking
  - 0.65 = standard (fills most of the hex, clear separation)
  - 0.8 = large counters, fills hex (good for tactical maps)
- Compute counter size: `counter_w = hex_flat_to_flat * counter_hex_ratio`
- Enforce minimum counter pixel size (default 30px wide) — if below, show warning and auto-scale text within counter
- Counter aspect ratio: standard wargame counters are square or 6:5 — maintain this regardless of hex shape
- **Font sizing within counter**: Combat factors, designation, NATO symbol all scale proportionally to counter pixel size, with minimum thresholds (e.g., minimum 6pt for combat factors to remain legible)

#### 0.3 Counter vs. Label/Terrain Collision Avoidance

**Problem**: Counters (`zorder=8.5`) draw over hex numbers (`zorder=6`) and city labels (`zorder=6`). When a counter occupies a hex, the hex number becomes unreadable (buried under the counter). Similarly, terrain decorations (trees, urban grid at `zorder=1.0-1.45`) may visually clash with counters.

**Solution**:
- **File**: `src/wargame_cartographer/rendering/label_layer.py`, `src/wargame_cartographer/rendering/nato_layer.py`
- **Hex number displacement**: When counters are present, collect the set of occupied hex IDs. In `render_label_layer()`, for any hex with a counter:
  - Move hex number from top-center to top-left or top-right corner of hex (outside the counter footprint)
  - Reduce font size slightly for displaced numbers
  - Add a tiny white halo/background for readability against terrain
- **City label displacement**: If a counter overlaps a city label position, shift the label to a clear position (try 8 cardinal offsets from the city point)
- **Terrain decoration dimming**: When a counter occupies a hex, reduce decoration alpha (or skip decorations entirely for that hex) to avoid visual noise under/around the counter
- **Implementation approach**: Pass the set of counter-occupied hex IDs to the label and terrain layers via `RenderContext` (add `occupied_hexes: set[str]` field)

#### 0.4 Map Size Specification — Standard Sheet Sizes

**Problem**: Currently map size is controlled by `output_width_mm` (default 500) and `output_height_mm` (default 700) — arbitrary dimensions. Real wargames use standard map sheet sizes, and players expect to specify "17×22 inch map" or "22×34 inch map" or multiples thereof.

**Solution**:
- **File**: `src/wargame_cartographer/config/map_spec.py`
- Add `map_size` field to `MapSpec` as an alternative to `output_width_mm`/`output_height_mm`:
  ```python
  map_size: str | None = None  # "17x22", "22x34", "34x44", "11x17", or "NxM" (inches)
  map_sheets: int = 1  # Number of map sheets (1, 2, 4) — arranges as 1x1, 1x2, 2x2
  map_orientation: Literal["portrait", "landscape"] = "landscape"
  ```
- **Standard sizes** (inches, landscape orientation):
  | Name | Dimensions | Typical Use |
  |------|-----------|-------------|
  | `11x17` | 11×17" (279×432mm) | Small/intro game |
  | `17x22` | 17×22" (432×559mm) | Standard wargame map |
  | `22x34` | 22×34" (559×864mm) | Large wargame map |
  | `34x44` | 34×44" (864×1118mm) | Monster game sheet |

- **Multi-sheet support**: `map_sheets=2` with `17x22` produces a 22×34" equivalent (two sheets side by side). `map_sheets=4` produces 2×2 tiling.
- When `map_size` is set, override `output_width_mm` and `output_height_mm` accordingly
- **Auto-fitting**: Given map_size + bbox, compute the hex_size_km that produces a grid filling the sheet. Or given map_size + hex_size_km, compute the bbox extent. User provides 2 of the 3 constraints (map_size, bbox, hex_size_km) and the system computes the third.
- Validation: warn if hex count exceeds ~2000 (performance), warn if px/hex < 40

### Phase 1: Quick Wins — Enable Existing Features (Low effort, high impact)

#### 1.1 Enable Terrain Hatching
- **File**: `src/wargame_cartographer/rendering/terrain_layer.py`
- **Change**: Apply the already-defined `terrain_hatches` from styles to `PathPatch` objects
- Each terrain type gets its hatching pattern overlaid on the fill color
- Result: Immediate 20% visual improvement in terrain differentiation

#### 1.2 Wire Up Hillshade Azimuth/Altitude
- **Files**: `rendering/elevation_layer.py`, `geo/elevation.py`
- **Change**: Pass `style.hillshade_azimuth` and `style.hillshade_altitude` through to `compute_hillshade()`
- Currently hardcoded; styles already define the values

#### 1.3 Add Missing Terrain Decorations
- **File**: `rendering/terrain_layer.py`
- Add decorations for the 5 undecorated terrain types:
  - **Mountain**: Small peak triangles / ridgeline marks with snow caps
  - **Marsh**: Horizontal grass tufts with water ripple lines
  - **Water**: Subtle wave pattern or horizontal ripple lines
  - **Coastal**: Beach dots / wave-break marks along coast edges
  - **Desert/Clear**: (Clear stays undecorated; optionally add subtle grass tufts)

### Phase 2: Counter Design Overhaul (Medium effort, high impact)

#### 2.1 Install `military-symbol` Library
- **File**: `pyproject.toml`
- Add `military-symbol` as dependency for NATO APP-6(E) SVG generation
- This gives us proper vector NATO symbols instead of text approximations

#### 2.2 Expanded Unit Type System
- **File**: `rendering/nato_layer.py` (major rewrite)
- Expand from 8 to 20+ unit types with proper SIDC codes:

```
infantry, armor, artillery, cavalry, airborne, marine, mechanized,
headquarters, engineer, signal, medical, supply, anti-armor,
air_defense, reconnaissance, special_forces,
air_fighter, air_bomber, air_helicopter, air_transport,
naval_surface, naval_submarine, naval_carrier
```

#### 2.3 Professional Counter Rendering
- **File**: `rendering/nato_layer.py` (or new `rendering/counter_renderer.py`)
- **New counter layout** following wargame conventions:

```
          [Echelon: XX, III, etc.]
    ┌──────────────────────────┐
    │  ┌────────────────────┐  │ ← Nationality color stripe (top)
    │  │                    │  │
    │  │   NATO SYMBOL      │  │ ← True SVG NATO symbol, white bg
    │  │   (vector art)     │  │
    │  │                    │  │
    │  └────────────────────┘  │
    │                          │
    │  ATK     DEF     MOV    │ ← Bold values, proper spacing
    │   8       6       4     │
    └──────────────────────────┘
         [Unit Designation]
          "2/16 Inf"
```

- **Counter features**:
  - Proper affiliation frames: rectangle=friendly, diamond=hostile
  - Affiliation colors: blue/red/green/yellow backgrounds
  - Nationality stripe at top of counter
  - White symbol area with black NATO symbol (maximum legibility)
  - Bold, well-spaced combat values with clear left-to-right reading
  - Subtle drop shadow for "stacked" appearance on map
  - Rounded corners matching professional counter design
  - Optional reduced-strength indicator (slash or lighter color)

#### 2.4 Counter Size Scaling
- Counter size relative to hex size (configurable ratio)
- Support for stacking indicators (small offset when multiple units in hex)
- Minimum readable size enforcement

### Phase 3: Map Cartography Enhancement (Medium effort, high impact)

#### 3.1 Road/River Hierarchy
- **File**: `rendering/vector_layer.py`
- Rivers: Scale linewidth by `stream_order` attribute (if available from Natural Earth)
  - Major rivers: 2.0pt, medium: 1.2pt, minor: 0.6pt
- Roads: Differentiate by class
  - Highways: thick brown solid, secondary: medium brown, tracks: thin dashed

#### 3.2 City Prominence Scaling
- **File**: `rendering/symbol_layer.py`
- Scale marker size by population rank or feature class
- Capital cities: large filled circle + name in bold
- Towns: medium circle
- Villages: small dot
- Ports: anchor symbol, Airfields: crossed-runway symbol

#### 3.3 Label Collision Avoidance
- **File**: `rendering/label_layer.py`
- Implement basic label placement with overlap detection
- Strategy: Place labels in preferred positions (N, NE, E, SE, S, SW, W, NW)
- Fall back to next position if overlap detected
- Use `matplotlib.text.Text.get_window_extent()` for bounding box detection

#### 3.4 Elevation Contour Lines (Optional)
- **File**: `rendering/elevation_layer.py`
- Add thin contour lines at configurable intervals (e.g., every 100m or 200m)
- Light gray, very thin (0.3pt), behind terrain but above hillshade
- Toggle via `show_contours` in MapSpec

### Phase 4: Style System Enhancements (Low-medium effort)

#### 4.1 Enhanced Style Properties
- **File**: `rendering/styles.py`
- Add new style properties:
  - `counter_shadow: bool` — drop shadow on counters
  - `counter_bevel: bool` — beveled edge effect
  - `terrain_decoration_density: float` — how many trees/blotches per hex
  - `label_halo: bool` — white halo around labels for readability
  - `river_hierarchy: bool` — enable/disable river width scaling
  - `road_style: str` — "solid", "dashed", "cased" (dark outline + light fill)
  - `contour_interval_m: int` — elevation contour interval

#### 4.2 Per-Style Counter Aesthetics
- Simonitch style: Warm counter colors, subtle shadow, thin borders
- Simonsen style: Bold counter colors, strong borders, high contrast
- Kibler style: Slightly textured counter backgrounds, organic feel

### Phase 5: Map Furniture Polish (Low effort)

#### 5.1 Improved Compass Rose
- Replace text "N" with a proper compass rose graphic (drawn programmatically)
- 4 or 8 cardinal directions, decorative star shape

#### 5.2 Coordinate Grid Ticks
- Add latitude/longitude ticks around map border
- Every 0.1° or 0.5° depending on map scale
- Small tick marks with coordinate labels

#### 5.3 Improved Legend
- Only show terrain types actually present in map
- Color swatches with hatching preview
- Better spacing and typography

### Phase 6: Side Panels — OOB and Game Module Display (Medium effort, high value)

These are optional panels rendered alongside the map, following the tradition of wargame maps that include Order of Battle charts, setup instructions, and game tables printed on the mapsheet margins or separate player aid cards.

#### 6.1 Order of Battle / Setup Panel

**Purpose**: A configurable side panel showing the Order of Battle (OOB) with unit setup information — which units deploy where, on what turn, and at what strength. This is a critical reference during play.

**Solution**:
- **Files**: New `src/wargame_cartographer/rendering/oob_panel.py`, modifications to `renderer.py` and `map_spec.py`
- **MapSpec additions**:
  ```python
  show_oob_panel: bool = False
  oob_panel_position: Literal["right", "left", "bottom"] = "right"
  oob_panel_width_ratio: float = 0.25  # Panel takes 25% of total output width
  oob_data: list[OOBEntry] | None = None
  ```
- **OOBEntry model** (new Pydantic model):
  ```python
  class OOBEntry(BaseModel):
      side: str  # "blue" or "red"
      formation: str  # "V Corps", "2nd Panzer Division"
      units: list[OOBUnit]
      setup_turn: int = 1  # Turn of entry
      setup_zone: str = ""  # "Beach Red", hex range "0101-0510", etc.
      notes: str = ""

  class OOBUnit(BaseModel):
      designation: str
      unit_type: str = "infantry"
      size: str = "division"
      combat_factor: int = 0
      movement_factor: int = 0
      setup_hex: str = ""  # Specific hex or "" for formation-level setup
  ```
- **Panel rendering**:
  - Renders as a separate matplotlib axes alongside the map axes (using `GridSpec` or `fig.add_axes()`)
  - Grouped by side (Blue forces, then Red forces), then by formation
  - Each unit shows: miniature counter icon + designation + setup hex
  - Formation headers with total strength summary
  - Turn-of-entry markers for reinforcements
  - Configurable sort order: by formation, by turn of entry, by hex
- **Layout**: The map figure expands to accommodate the panel. If `map_size="17x22"` with a right panel, the map area shrinks to ~75% and the panel takes ~25%.

#### 6.2 Game Module Panels (CRT, TEC, etc.)

**Purpose**: Space for game-specific reference tables — Combat Results Table (CRT), Terrain Effects Chart (TEC), sequence of play, special rules summaries. Default display is OFF.

**Solution**:
- **Files**: New `src/wargame_cartographer/rendering/module_panel.py`, modifications to `renderer.py` and `map_spec.py`
- **MapSpec additions**:
  ```python
  show_module_panels: bool = False  # Default OFF
  module_panel_position: Literal["bottom", "right", "left"] = "bottom"
  module_panels: list[ModulePanel] | None = None
  ```
- **ModulePanel model**:
  ```python
  class ModulePanel(BaseModel):
      panel_type: Literal["crt", "tec", "sequence_of_play", "custom"] = "crt"
      title: str = ""
      custom_data: dict | None = None  # For custom panel content
  ```
- **Built-in panel types**:
  1. **CRT (Combat Results Table)**: Classic odds-ratio CRT with columns (1:2, 1:1, 2:1, 3:1, etc.) and die roll rows. Configurable results (AE, AR, DR, DE, EX, etc.). Default CRT provided; user can override via YAML.
  2. **TEC (Terrain Effects Chart)**: Auto-generated from the 8 terrain types in `TERRAIN_EFFECTS`. Shows movement cost, defense modifier, LOS blocking in a clean table. (This partially overlaps with the existing legend but provides a more complete reference.)
  3. **Sequence of Play**: Text block with numbered phases (Movement, Combat, Exploitation, etc.)
  4. **Custom**: User provides title + content rows in YAML, rendered as a formatted table or text block.
- **Panel rendering**:
  - Rendered as additional axes below or beside the map
  - Tables drawn using matplotlib table patches or manual cell layout
  - Styled consistently with the chosen `designer_style`
  - Grid lines, alternating row colors, header styling
  - Bottom panels span the full map width; side panels stack vertically

#### 6.3 Panel Layout Engine

**Purpose**: Coordinate the map area + OOB panel + module panels into a coherent page layout.

**Solution**:
- **File**: `src/wargame_cartographer/rendering/renderer.py` (modify `MapRenderer`)
- Replace single-axes rendering with a layout manager:
  1. Compute map area dimensions from `map_size` (or `output_width_mm`/`output_height_mm`)
  2. If OOB panel enabled, subtract panel width from map area
  3. If module panels enabled, subtract panel height from map area
  4. Create figure with `GridSpec` layout:
     ```
     ┌──────────────────┬──────────┐
     │                  │  OOB     │
     │    MAP AREA      │  Panel   │
     │                  │          │
     ├──────────────────┴──────────┤
     │   Module Panel (CRT, etc.)  │
     └─────────────────────────────┘
     ```
  5. Each panel gets its own axes for independent rendering
  6. All panels share the same `WargameStyle` for visual consistency

---

## Priority / Sequencing

```
Phase 0 (Foundations)    → MUST DO FIRST — readability & sizing guarantees
  0.1 Hex readability min-px enforcement
  0.2 Counter-to-hex proportion system
  0.3 Counter vs label/terrain collision avoidance
  0.4 Map size specification (17x22, 22x34, etc.)

Phase 1 (Quick Wins)     → Immediate visual improvement
  1.1 Hatching
  1.2 Hillshade wiring
  1.3 Terrain decorations

Phase 2 (Counters)       → Core feature upgrade
  2.1 military-symbol dep
  2.2 Expanded unit types
  2.3 Counter renderer
  2.4 Counter scaling (builds on 0.2)

Phase 3 (Cartography)    → Map quality uplift
  3.1 Road/river hierarchy
  3.2 City scaling
  3.3 Label collision (extends 0.3)
  3.4 Contour lines

Phase 4 (Style System)   → Polish and customization
  4.1 New style properties
  4.2 Per-style counters

Phase 5 (Furniture)      → Final polish
  5.1 Compass rose
  5.2 Coordinate ticks
  5.3 Legend improvements

Phase 6 (Side Panels)    → Optional game reference panels
  6.1 OOB / Setup panel
  6.2 Game module panels (CRT, TEC, etc.)
  6.3 Panel layout engine
```

## Files to Modify

| File | Changes |
|------|---------|
| `pyproject.toml` | Add `military-symbol` dependency |
| `src/.../config/map_spec.py` | Map size spec, counter_hex_ratio, min_hex_px, panel toggles, OOBEntry/ModulePanel models |
| `src/.../rendering/renderer.py` | Hex readability checks, GridSpec layout engine for panels, occupied_hexes in RenderContext |
| `src/.../rendering/terrain_layer.py` | Enable hatching, add 5 terrain decorations, dim decorations under counters |
| `src/.../rendering/nato_layer.py` | Complete rewrite: professional counters, proportional sizing, collision reporting |
| `src/.../rendering/elevation_layer.py` | Wire azimuth/altitude, add optional contours |
| `src/.../rendering/vector_layer.py` | Road/river hierarchy rendering |
| `src/.../rendering/symbol_layer.py` | City prominence scaling, better symbols |
| `src/.../rendering/label_layer.py` | Collision avoidance, hex number displacement when counters present |
| `src/.../rendering/styles.py` | New style properties for all enhancements |
| `src/.../rendering/cartouche_layer.py` | Compass rose, coord ticks, legend fix |
| `src/.../rendering/oob_panel.py` | **NEW** — Order of Battle side panel renderer |
| `src/.../rendering/module_panel.py` | **NEW** — CRT, TEC, and custom game module panel renderer |
| `src/.../geo/elevation.py` | Accept azimuth/altitude parameters |
| `src/.../terrain/types.py` | Possibly expand terrain type definitions |
| `src/.../hex/grid.py` | hex_readability_report() helper |

## Expected Outcome

After all phases, the maps should achieve quality comparable to:
- **GMT Games** digital VASSAL modules (Simonitch style)
- **SPI/Decision Games** classic wargame maps (Simonsen style)
- **Avalon Hill** painterly maps (Kibler style)

Counters will look like professional wargame counters with proper NATO symbology,
clear combat values, and appropriate visual weight on the map.

Maps will be produced at standard wargame sheet sizes (17×22", 22×34", etc.) with
hexes and counters guaranteed to be at readable proportions. Side panels for OOB
and game tables (CRT, TEC) can be optionally included for a complete game-ready product.
