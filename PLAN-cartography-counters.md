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

---

## Priority / Sequencing

```
Phase 1 (Quick Wins)     → Do first, immediate visual improvement
  1.1 Hatching
  1.2 Hillshade wiring
  1.3 Terrain decorations

Phase 2 (Counters)       → Core feature upgrade
  2.1 military-symbol dep
  2.2 Expanded unit types
  2.3 Counter renderer
  2.4 Counter scaling

Phase 3 (Cartography)    → Map quality uplift
  3.1 Road/river hierarchy
  3.2 City scaling
  3.3 Label collision
  3.4 Contour lines

Phase 4 (Style System)   → Polish and customization
  4.1 New style properties
  4.2 Per-style counters

Phase 5 (Furniture)      → Final polish
  5.1 Compass rose
  5.2 Coordinate ticks
  5.3 Legend improvements
```

## Files to Modify

| File | Changes |
|------|---------|
| `pyproject.toml` | Add `military-symbol` dependency |
| `src/.../rendering/terrain_layer.py` | Enable hatching, add 5 terrain decorations |
| `src/.../rendering/nato_layer.py` | Complete rewrite for professional counters |
| `src/.../rendering/elevation_layer.py` | Wire azimuth/altitude, add optional contours |
| `src/.../rendering/vector_layer.py` | Road/river hierarchy rendering |
| `src/.../rendering/symbol_layer.py` | City prominence scaling, better symbols |
| `src/.../rendering/label_layer.py` | Collision avoidance |
| `src/.../rendering/styles.py` | New style properties for all enhancements |
| `src/.../rendering/cartouche_layer.py` | Compass rose, coord ticks, legend fix |
| `src/.../config/map_spec.py` | New spec fields (show_contours, etc.) |
| `src/.../geo/elevation.py` | Accept azimuth/altitude parameters |
| `src/.../terrain/types.py` | Possibly expand terrain type definitions |

## Expected Outcome

After all phases, the maps should achieve quality comparable to:
- **GMT Games** digital VASSAL modules (Simonitch style)
- **SPI/Decision Games** classic wargame maps (Simonsen style)
- **Avalon Hill** painterly maps (Kibler style)

Counters will look like professional wargame counters with proper NATO symbology,
clear combat values, and appropriate visual weight on the map.
