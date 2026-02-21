"""CRS auto-selection and coordinate transformation."""

from __future__ import annotations

import math

import pyproj

from wargame_cartographer.config.map_spec import BoundingBox


def select_crs(bbox: BoundingBox) -> pyproj.CRS:
    """Auto-select the best projected CRS for a bounding box.

    - <200km extent: UTM zone (best for tactical maps)
    - <2000km extent: Lambert Conformal Conic (regional/operational)
    - Larger: Azimuthal Equidistant (strategic/continental)
    """
    max_extent = max(bbox.width_km(), bbox.height_km())
    center_lat, center_lon = bbox.center()

    if max_extent < 200:
        return _utm_crs(center_lat, center_lon)
    elif max_extent < 2000:
        return _lambert_conformal_conic(center_lat, center_lon, bbox)
    else:
        return _azimuthal_equidistant(center_lat, center_lon)


def _utm_crs(lat: float, lon: float) -> pyproj.CRS:
    """Get UTM zone CRS for a point."""
    zone = int((lon + 180) / 6) + 1
    hemisphere = "north" if lat >= 0 else "south"
    epsg = 32600 + zone if hemisphere == "north" else 32700 + zone
    return pyproj.CRS.from_epsg(epsg)


def _lambert_conformal_conic(
    center_lat: float, center_lon: float, bbox: BoundingBox
) -> pyproj.CRS:
    """Lambert Conformal Conic centered on the bbox."""
    sp1 = bbox.min_lat + (bbox.max_lat - bbox.min_lat) / 6.0
    sp2 = bbox.max_lat - (bbox.max_lat - bbox.min_lat) / 6.0
    proj_string = (
        f"+proj=lcc +lat_1={sp1:.2f} +lat_2={sp2:.2f} "
        f"+lat_0={center_lat:.2f} +lon_0={center_lon:.2f} "
        f"+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    return pyproj.CRS.from_proj4(proj_string)


def _azimuthal_equidistant(center_lat: float, center_lon: float) -> pyproj.CRS:
    """Azimuthal Equidistant centered on a point."""
    proj_string = (
        f"+proj=aeqd +lat_0={center_lat:.2f} +lon_0={center_lon:.2f} "
        f"+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    return pyproj.CRS.from_proj4(proj_string)


def make_transformer(
    src_crs: pyproj.CRS | str, dst_crs: pyproj.CRS | str
) -> pyproj.Transformer:
    """Create a coordinate transformer."""
    if isinstance(src_crs, str):
        src_crs = pyproj.CRS(src_crs)
    if isinstance(dst_crs, str):
        dst_crs = pyproj.CRS(dst_crs)
    return pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True)
