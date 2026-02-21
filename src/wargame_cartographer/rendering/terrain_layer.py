"""Terrain layer: colored hex fills with custom terrain patterns and coastal contours."""

from __future__ import annotations

import math
import hashlib

import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Circle, FancyBboxPatch
from matplotlib.path import Path as MplPath
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep

from wargame_cartographer.rendering.renderer import RenderContext
from wargame_cartographer.terrain.types import TerrainType


def _build_coastal_data(context: RenderContext):
    """Build projected land+lake polygons for coastal contour rendering.

    Clips global Natural Earth polygons to the map bbox BEFORE projecting,
    then projects the clipped geometry to the grid CRS.

    Returns (land_proj, lake_proj) as shapely geometries in projected CRS,
    or (None, None) if vector data is unavailable.
    """
    if context.vector_data is None:
        return None, None

    bbox = context.spec.bbox
    transformer = context.grid._to_proj

    # Build a bbox polygon in WGS84 for clipping (with small buffer)
    from shapely.geometry import box as shapely_box
    clip_box = shapely_box(
        bbox.min_lon - 0.5, bbox.min_lat - 0.5,
        bbox.max_lon + 0.5, bbox.max_lat + 0.5,
    )

    def _clip_and_project_gdf(gdf):
        """Clip GeoDataFrame to bbox in WGS84, then project to grid CRS."""
        polys = []
        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is None:
                continue
            try:
                # Clip to bbox in WGS84 first
                clipped = geom.intersection(clip_box)
                if clipped.is_empty:
                    continue
                # Now project the clipped geometry
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


def render_terrain_layer(ax: plt.Axes, context: RenderContext):
    """Draw terrain-colored hex fills with custom decorative patterns."""
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

        # Check if this is a coastal hex (water hex that intersects land,
        # or land hex that intersects water)
        is_coastal = False
        hex_poly = None

        if land_proj is not None:
            hex_poly = Polygon(verts)
            if hex_poly.is_valid:
                try:
                    if terrain == TerrainType.WATER:
                        # Water hex: check if any land intrudes
                        is_coastal = land_prepared.intersects(hex_poly) and not land_prepared.contains(hex_poly)
                    else:
                        # Land hex: check if it's partially over water
                        is_coastal = not land_prepared.contains(hex_poly) and land_prepared.intersects(hex_poly)
                except Exception:
                    is_coastal = False

        if is_coastal and hex_poly is not None:
            # Draw coastal hex with actual coastline contour
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

        cell = grid.cells[(q, row)]
        cx, cy = cell.center_x, cell.center_y

        # Custom terrain decorations (skip for water hexes)
        if terrain == TerrainType.URBAN:
            _draw_urban_grid(ax, cx, cy, r)
        elif terrain == TerrainType.FOREST:
            _draw_forest_trees(ax, cx, cy, r, q, row)
        elif terrain == TerrainType.ROUGH:
            _draw_rough_blotches(ax, cx, cy, r, q, row)


def _draw_coastal_hex(ax, context, hex_poly, verts_arr, codes, terrain, land_proj, lake_proj):
    """Draw a hex with actual coastline contour: land part in land color, water part in water color."""
    style = context.style
    water_color = style.water_color
    land_color = style.terrain_colors.get(TerrainType.CLEAR, "#F5EDD5")

    hex_path = MplPath(verts_arr, codes)

    try:
        # Compute land portion within this hex
        land_in_hex = hex_poly.intersection(land_proj)

        # Subtract lakes from land
        if lake_proj is not None:
            try:
                land_in_hex = land_in_hex.difference(lake_proj)
            except Exception:
                pass

        # First: fill entire hex with water color
        water_patch = PathPatch(
            hex_path,
            facecolor=water_color,
            edgecolor="none",
            linewidth=0,
            zorder=1,
        )
        ax.add_patch(water_patch)

        # Then: overlay land portion with land color
        if not land_in_hex.is_empty:
            _draw_shapely_polygon(ax, land_in_hex, land_color, zorder=1.1)

    except Exception:
        # Fallback: just fill with terrain color
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

        # Build path with exterior + holes
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
        # GeometryCollection — draw any polygon parts
        for part in geom.geoms:
            if isinstance(part, (Polygon, MultiPolygon)):
                _draw_shapely_polygon(ax, part, color, zorder=zorder)


def _draw_urban_grid(ax, cx, cy, r):
    """Draw a black-and-white street grid pattern inside the hex."""
    # White base
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

    # Grid lines — streets
    spacing = r * 0.22
    line_kw = dict(color="#333333", linewidth=0.6, zorder=1.3, alpha=0.8)
    # Horizontal streets
    for offset in np.arange(-size, size + spacing, spacing):
        y = cy + offset
        ax.plot([cx - size, cx + size], [y, y], **line_kw)
    # Vertical streets
    for offset in np.arange(-size, size + spacing, spacing):
        x = cx + offset
        ax.plot([x, x], [cy - size, cy + size], **line_kw)

    # City block fills (dark grey small rectangles)
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
    # Deterministic pseudo-random positions
    seed = int(hashlib.md5(f"{q},{row}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)

    n_trees = 7
    spread = r * 0.50

    for i in range(n_trees):
        # Random offset within hex, clustered near center
        tx = cx + rng.uniform(-spread, spread)
        ty = cy + rng.uniform(-spread, spread)

        # Curly canopy: overlapping irregular circles with wavy edges
        canopy_r = r * rng.uniform(0.10, 0.18)
        n_lobes = 8 + rng.randint(0, 5)
        angles = np.linspace(0, 2 * math.pi, n_lobes * 4, endpoint=False)
        # Wavy radius variation for organic look
        radii = canopy_r * (1.0 + 0.25 * np.sin(angles * n_lobes) + 0.1 * rng.randn(len(angles)))
        xs = tx + radii * np.cos(angles)
        ys = ty + radii * np.sin(angles)

        # Darker green canopy fill — softer than before
        ax.fill(
            xs, ys,
            color="#3D7A3D",
            zorder=1.4,
            alpha=0.65,
            edgecolor="#2D6A2D",
            linewidth=0.3,
        )

        # Lighter highlight lobe on top for depth
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

        # Irregular blob: circle with varying radius
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
