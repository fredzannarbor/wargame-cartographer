"""Terrain layer: colored hex fills with hatching, custom terrain patterns, and coastal contours."""

from __future__ import annotations

import math
import hashlib

import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Circle, FancyBboxPatch, Polygon as MplPolygon
from matplotlib.path import Path as MplPath
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep

from wargame_cartographer.rendering.renderer import RenderContext
from wargame_cartographer.terrain.types import TerrainType


def _build_coastal_data(context: RenderContext):
    """Build projected land+lake polygons for coastal contour rendering."""
    if context.vector_data is None:
        return None, None

    bbox = context.spec.bbox
    transformer = context.grid._to_proj

    from shapely.geometry import box as shapely_box
    clip_box = shapely_box(
        bbox.min_lon - 0.5, bbox.min_lat - 0.5,
        bbox.max_lon + 0.5, bbox.max_lat + 0.5,
    )

    def _clip_and_project_gdf(gdf):
        polys = []
        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is None:
                continue
            try:
                clipped = geom.intersection(clip_box)
                if clipped.is_empty:
                    continue
                projected = _project_polygon(clipped, transformer)
                if projected is not None and projected.is_valid and not projected.is_empty:
                    polys.append(projected)
            except Exception:
                continue
        if not polys:
            return None
        try:
            return unary_union(polys)
        except Exception:
            return None

    land_proj = None
    lake_proj = None

    if hasattr(context.vector_data, 'land') and not context.vector_data.land.empty:
        land_proj = _clip_and_project_gdf(context.vector_data.land)

    if hasattr(context.vector_data, 'lakes') and not context.vector_data.lakes.empty:
        lake_proj = _clip_and_project_gdf(context.vector_data.lakes)

    return land_proj, lake_proj


def _project_polygon(geom, transformer):
    """Project a shapely polygon/multipolygon using a pyproj transformer."""
    if isinstance(geom, Polygon):
        ext_coords = [transformer.transform(x, y) for x, y in geom.exterior.coords]
        holes = []
        for interior in geom.interiors:
            hole_coords = [transformer.transform(x, y) for x, y in interior.coords]
            holes.append(hole_coords)
        return Polygon(ext_coords, holes)
    elif isinstance(geom, MultiPolygon):
        parts = []
        for poly in geom.geoms:
            p = _project_polygon(poly, transformer)
            if p is not None and p.is_valid and not p.is_empty:
                parts.append(p)
        if parts:
            return MultiPolygon(parts) if len(parts) > 1 else parts[0]
    return None


def _should_decorate(context: RenderContext, q: int, row: int) -> bool:
    """Check if a hex should get terrain decorations."""
    if context.skip_decorations:
        return False
    hex_id = context.grid.wargame_number(q, row)
    if hex_id in context.occupied_hexes:
        return False
    return True


def render_terrain_layer(ax: plt.Axes, context: RenderContext):
    """Draw terrain-colored hex fills with hatching and decorative patterns."""
    style = context.style
    grid = context.grid
    r = grid.hex_radius_m

    # Build projected land/lake geometry for coastal contours
    land_proj, lake_proj = _build_coastal_data(context)
    land_prepared = prep(land_proj) if land_proj is not None else None

    for (q, row) in grid.all_hexes():
        verts = grid.hex_vertices(q, row)
        verts_arr = np.array(verts + [verts[0]])

        codes = (
            [MplPath.MOVETO]
            + [MplPath.LINETO] * (len(verts_arr) - 2)
            + [MplPath.CLOSEPOLY]
        )
        path = MplPath(verts_arr, codes)

        terrain_info = context.hex_terrain.get((q, row), {})
        terrain = terrain_info.get("terrain", TerrainType.CLEAR)
        color = style.terrain_colors.get(terrain, "#F5EDD5")

        # Check if this is a coastal hex
        is_coastal = False
        hex_poly = None

        if land_proj is not None:
            hex_poly = Polygon(verts)
            if hex_poly.is_valid:
                try:
                    if terrain == TerrainType.WATER:
                        is_coastal = land_prepared.intersects(hex_poly) and not land_prepared.contains(hex_poly)
                    else:
                        is_coastal = not land_prepared.contains(hex_poly) and land_prepared.intersects(hex_poly)
                except Exception:
                    is_coastal = False

        if is_coastal and hex_poly is not None:
            _draw_coastal_hex(ax, context, hex_poly, verts_arr, codes, terrain, land_proj, lake_proj)
        else:
            # Standard solid fill
            patch = PathPatch(
                path,
                facecolor=color,
                edgecolor="none",
                linewidth=0,
                zorder=1,
            )
            ax.add_patch(patch)

        # Terrain hatching overlay (Phase 1.1)
        hatch = style.terrain_hatches.get(terrain)
        if hatch:
            hatch_patch = PathPatch(
                path,
                facecolor="none",
                edgecolor=style.grid_color,
                hatch=hatch,
                linewidth=0,
                alpha=0.3,
                zorder=1.05,
            )
            ax.add_patch(hatch_patch)

        cell = grid.cells[(q, row)]
        cx, cy = cell.center_x, cell.center_y

        # Custom terrain decorations (skip for water; skip if hex too small or has counter)
        if _should_decorate(context, q, row):
            if terrain == TerrainType.URBAN:
                _draw_urban_grid(ax, cx, cy, r)
            elif terrain == TerrainType.FOREST:
                _draw_forest_trees(ax, cx, cy, r, q, row)
            elif terrain == TerrainType.ROUGH:
                _draw_rough_blotches(ax, cx, cy, r, q, row)
            elif terrain == TerrainType.MOUNTAIN:
                _draw_mountain_peaks(ax, cx, cy, r, q, row)
            elif terrain == TerrainType.MARSH:
                _draw_marsh_reeds(ax, cx, cy, r, q, row)


def _draw_coastal_hex(ax, context, hex_poly, verts_arr, codes, terrain, land_proj, lake_proj):
    """Draw a hex with actual coastline contour."""
    style = context.style
    water_color = style.water_color
    land_color = style.terrain_colors.get(TerrainType.CLEAR, "#F5EDD5")

    hex_path = MplPath(verts_arr, codes)

    try:
        land_in_hex = hex_poly.intersection(land_proj)

        if lake_proj is not None:
            try:
                land_in_hex = land_in_hex.difference(lake_proj)
            except Exception:
                pass

        water_patch = PathPatch(
            hex_path,
            facecolor=water_color,
            edgecolor="none",
            linewidth=0,
            zorder=1,
        )
        ax.add_patch(water_patch)

        if not land_in_hex.is_empty:
            _draw_shapely_polygon(ax, land_in_hex, land_color, zorder=1.1)

    except Exception:
        fallback_color = style.terrain_colors.get(terrain, "#F5EDD5")
        patch = PathPatch(
            hex_path,
            facecolor=fallback_color,
            edgecolor="none",
            linewidth=0,
            zorder=1,
        )
        ax.add_patch(patch)


def _draw_shapely_polygon(ax, geom, color, zorder=1.1):
    """Render a shapely Polygon or MultiPolygon as matplotlib patches."""
    if isinstance(geom, Polygon):
        if geom.is_empty:
            return
        ext = np.array(geom.exterior.coords)
        if len(ext) < 3:
            return

        all_verts = list(ext)
        all_codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(ext) - 2) + [MplPath.CLOSEPOLY]

        for interior in geom.interiors:
            hole = np.array(interior.coords)
            if len(hole) >= 3:
                all_verts.extend(hole)
                all_codes.extend(
                    [MplPath.MOVETO] + [MplPath.LINETO] * (len(hole) - 2) + [MplPath.CLOSEPOLY]
                )

        path = MplPath(all_verts, all_codes)
        patch = PathPatch(path, facecolor=color, edgecolor="none", linewidth=0, zorder=zorder)
        ax.add_patch(patch)

    elif isinstance(geom, MultiPolygon):
        for poly in geom.geoms:
            _draw_shapely_polygon(ax, poly, color, zorder=zorder)

    elif hasattr(geom, 'geoms'):
        for part in geom.geoms:
            if isinstance(part, (Polygon, MultiPolygon)):
                _draw_shapely_polygon(ax, part, color, zorder=zorder)


def _draw_urban_grid(ax, cx, cy, r):
    """Draw a black-and-white street grid pattern inside the hex."""
    size = r * 0.55
    rect = FancyBboxPatch(
        (cx - size, cy - size), size * 2, size * 2,
        boxstyle="round,pad=0",
        facecolor="#F0F0F0",
        edgecolor="none",
        zorder=1.2,
        clip_on=True,
    )
    ax.add_patch(rect)

    spacing = r * 0.22
    line_kw = dict(color="#333333", linewidth=0.6, zorder=1.3, alpha=0.8)
    for offset in np.arange(-size, size + spacing, spacing):
        y = cy + offset
        ax.plot([cx - size, cx + size], [y, y], **line_kw)
    for offset in np.arange(-size, size + spacing, spacing):
        x = cx + offset
        ax.plot([x, x], [cy - size, cy + size], **line_kw)

    block_size = spacing * 0.35
    for xo in np.arange(-size + spacing * 0.3, size, spacing):
        for yo in np.arange(-size + spacing * 0.3, size, spacing):
            bx, by = cx + xo, cy + yo
            block = FancyBboxPatch(
                (bx - block_size, by - block_size),
                block_size * 2, block_size * 2,
                boxstyle="round,pad=0",
                facecolor="#888888",
                edgecolor="none",
                zorder=1.25,
                alpha=0.5,
            )
            ax.add_patch(block)


def _draw_forest_trees(ax, cx, cy, r, q, row):
    """Draw curly organic tree canopy blobs scattered in the hex."""
    seed = int(hashlib.md5(f"{q},{row}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)

    n_trees = 7
    spread = r * 0.50

    for i in range(n_trees):
        tx = cx + rng.uniform(-spread, spread)
        ty = cy + rng.uniform(-spread, spread)

        canopy_r = r * rng.uniform(0.10, 0.18)
        n_lobes = 8 + rng.randint(0, 5)
        angles = np.linspace(0, 2 * math.pi, n_lobes * 4, endpoint=False)
        radii = canopy_r * (1.0 + 0.25 * np.sin(angles * n_lobes) + 0.1 * rng.randn(len(angles)))
        xs = tx + radii * np.cos(angles)
        ys = ty + radii * np.sin(angles)

        ax.fill(
            xs, ys,
            color="#3D7A3D",
            zorder=1.4,
            alpha=0.65,
            edgecolor="#2D6A2D",
            linewidth=0.3,
        )

        highlight_r = canopy_r * 0.5
        hx = tx + rng.uniform(-canopy_r * 0.2, canopy_r * 0.2)
        hy = ty + canopy_r * 0.3
        h_angles = np.linspace(0, 2 * math.pi, 12)
        h_radii = highlight_r * (1.0 + 0.2 * np.sin(h_angles * 5))
        hxs = hx + h_radii * np.cos(h_angles)
        hys = hy + h_radii * np.sin(h_angles)
        ax.fill(hxs, hys, color="#5EA85E", zorder=1.45, alpha=0.4)


def _draw_rough_blotches(ax, cx, cy, r, q, row):
    """Draw irregular tan blotches for rough terrain."""
    seed = int(hashlib.md5(f"rough_{q},{row}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)

    n_blotches = 6
    spread = r * 0.5

    for i in range(n_blotches):
        bx = cx + rng.uniform(-spread, spread)
        by = cy + rng.uniform(-spread, spread)
        blob_r = r * rng.uniform(0.06, 0.14)

        angles = np.linspace(0, 2 * math.pi, 12)
        radii = blob_r * (1.0 + 0.3 * rng.randn(12))
        xs = bx + radii * np.cos(angles)
        ys = by + radii * np.sin(angles)

        ax.fill(
            xs, ys,
            color="#A0855A",
            alpha=0.6,
            zorder=1.3,
            edgecolor="#8B7040",
            linewidth=0.3,
        )


def _draw_mountain_peaks(ax, cx, cy, r, q, row):
    """Draw small triangular peak marks with snow caps for mountain terrain."""
    seed = int(hashlib.md5(f"mtn_{q},{row}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)

    n_peaks = 4
    spread = r * 0.45

    for i in range(n_peaks):
        px = cx + rng.uniform(-spread, spread)
        py = cy + rng.uniform(-spread, spread)
        peak_h = r * rng.uniform(0.15, 0.28)
        peak_w = peak_h * rng.uniform(0.8, 1.4)

        # Mountain triangle
        tri_xs = [px - peak_w / 2, px, px + peak_w / 2]
        tri_ys = [py - peak_h * 0.3, py + peak_h * 0.7, py - peak_h * 0.3]
        ax.fill(
            tri_xs, tri_ys,
            color="#6B5B4B",
            alpha=0.7,
            zorder=1.3,
            edgecolor="#4A3A2A",
            linewidth=0.4,
        )

        # Snow cap at top
        cap_h = peak_h * 0.25
        cap_w = peak_w * 0.3
        cap_xs = [px - cap_w / 2, px, px + cap_w / 2]
        cap_ys = [py + peak_h * 0.7 - cap_h, py + peak_h * 0.7, py + peak_h * 0.7 - cap_h]
        ax.fill(
            cap_xs, cap_ys,
            color="white",
            alpha=0.8,
            zorder=1.35,
            edgecolor="none",
        )

    # Ridgeline between peaks
    if n_peaks >= 2:
        ridge_y = cy + r * 0.1
        ax.plot(
            [cx - spread * 0.6, cx + spread * 0.6],
            [ridge_y, ridge_y + r * 0.05],
            color="#5A4A3A",
            linewidth=0.5,
            alpha=0.5,
            zorder=1.25,
        )


def _draw_marsh_reeds(ax, cx, cy, r, q, row):
    """Draw horizontal grass tufts with wavy water lines for marsh terrain."""
    seed = int(hashlib.md5(f"marsh_{q},{row}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)

    spread = r * 0.45

    # Wavy water lines
    n_waves = 3
    for i in range(n_waves):
        wy = cy + rng.uniform(-spread * 0.6, spread * 0.6)
        wave_xs = np.linspace(cx - spread, cx + spread, 30)
        wave_ys = wy + r * 0.03 * np.sin(wave_xs / (r * 0.12))
        ax.plot(
            wave_xs, wave_ys,
            color="#4A90D9",
            linewidth=0.5,
            alpha=0.5,
            zorder=1.25,
        )

    # Grass tufts
    n_tufts = 5
    for i in range(n_tufts):
        tx = cx + rng.uniform(-spread, spread)
        ty = cy + rng.uniform(-spread, spread)
        tuft_h = r * rng.uniform(0.08, 0.15)

        n_blades = rng.randint(3, 6)
        for b in range(n_blades):
            angle = rng.uniform(-0.4, 0.4)
            bx = tx + tuft_h * 0.3 * math.sin(angle)
            by_top = ty + tuft_h * math.cos(angle)
            ax.plot(
                [tx, bx], [ty, by_top],
                color="#4A6A3A",
                linewidth=0.6,
                alpha=0.7,
                zorder=1.3,
            )
