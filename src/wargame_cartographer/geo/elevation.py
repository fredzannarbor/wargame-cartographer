"""Elevation data loading and hillshade computation."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
from matplotlib.colors import LightSource
from rich.console import Console

from wargame_cartographer.config.map_spec import BoundingBox

console = Console()


def _bbox_hash(bbox: BoundingBox) -> str:
    key = f"{bbox.min_lon:.4f},{bbox.min_lat:.4f},{bbox.max_lon:.4f},{bbox.max_lat:.4f}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


class ElevationProcessor:
    """Load elevation rasters and compute hillshade."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or (Path.home() / "wargame-cartographer" / "cache" / "elevation")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_elevation(self, bbox: BoundingBox) -> tuple[np.ndarray, dict]:
        """Get elevation data for a bounding box.

        Returns (elevation_array, metadata_dict).
        metadata_dict contains 'transform', 'crs', 'bounds', 'resolution'.

        Uses SRTM via rasterio if available, falls back to synthetic data.
        """
        cache_key = f"dem_{_bbox_hash(bbox)}.tif"
        cache_path = self.cache_dir / cache_key

        # Try to load cached GeoTIFF
        if cache_path.exists():
            return self._load_geotiff(cache_path)

        # Try downloading SRTM via rasterio/SRTM
        try:
            return self._download_srtm(bbox, cache_path)
        except Exception as e:
            console.print(f"  [yellow]SRTM download failed ({e}), using synthetic elevation[/yellow]")
            return self._synthetic_elevation(bbox)

    def _download_srtm(self, bbox: BoundingBox, cache_path: Path) -> tuple[np.ndarray, dict]:
        """Download SRTM tiles and merge for the bbox."""
        import rasterio
        from rasterio.merge import merge
        from rasterio.warp import calculate_default_transform, reproject, Resampling

        console.print("  Downloading SRTM elevation data...", style="dim")

        # Compute which 1-degree SRTM tiles we need
        lat_min = int(math.floor(bbox.min_lat))
        lat_max = int(math.floor(bbox.max_lat))
        lon_min = int(math.floor(bbox.min_lon))
        lon_max = int(math.floor(bbox.max_lon))

        tile_paths = []
        for lat in range(lat_min, lat_max + 1):
            for lon in range(lon_min, lon_max + 1):
                tile_path = self._download_srtm_tile(lat, lon)
                if tile_path:
                    tile_paths.append(tile_path)

        if not tile_paths:
            raise RuntimeError("No SRTM tiles available for this area")

        # Merge tiles
        datasets = [rasterio.open(p) for p in tile_paths]
        try:
            merged, transform = merge(datasets, bounds=bbox.as_tuple())
            elevation = merged[0]  # First band

            metadata = {
                "transform": transform,
                "crs": "EPSG:4326",
                "bounds": bbox.as_tuple(),
                "resolution": 90,  # meters (approx for SRTM 3 arc-second)
            }

            # Cache the merged result
            with rasterio.open(
                cache_path, "w",
                driver="GTiff",
                height=elevation.shape[0],
                width=elevation.shape[1],
                count=1,
                dtype=elevation.dtype,
                crs="EPSG:4326",
                transform=transform,
            ) as dst:
                dst.write(elevation, 1)

            return elevation, metadata
        finally:
            for ds in datasets:
                ds.close()

    def _download_srtm_tile(self, lat: int, lon: int) -> Path | None:
        """Download a single SRTM 1-degree tile."""
        import requests

        ns = "N" if lat >= 0 else "S"
        ew = "E" if lon >= 0 else "W"
        tile_name = f"{ns}{abs(lat):02d}{ew}{abs(lon):03d}"
        filename = f"{tile_name}.hgt.zip"
        tile_cache = self.cache_dir / f"{tile_name}.hgt"

        if tile_cache.exists():
            return tile_cache

        # Try NASA SRTM v3
        url = f"https://elevation-tiles-prod.s3.amazonaws.com/skadi/{tile_name[:3]}/{tile_name}.hgt.gz"
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                import gzip
                with open(tile_cache, "wb") as f:
                    f.write(gzip.decompress(resp.content))
                return tile_cache
        except Exception:
            pass

        return None

    def _load_geotiff(self, path: Path) -> tuple[np.ndarray, dict]:
        """Load a cached GeoTIFF."""
        import rasterio

        with rasterio.open(path) as src:
            elevation = src.read(1)
            metadata = {
                "transform": src.transform,
                "crs": str(src.crs),
                "bounds": src.bounds,
                "resolution": src.res[0],
            }
        return elevation, metadata

    def _synthetic_elevation(self, bbox: BoundingBox) -> tuple[np.ndarray, dict]:
        """Generate synthetic elevation data as a fallback.

        Uses a simple latitude-based model: higher terrain away from coasts.
        This is a placeholder until real SRTM data is available.
        """
        # Create a 500x500 grid
        height, width = 500, 500
        lats = np.linspace(bbox.max_lat, bbox.min_lat, height)
        lons = np.linspace(bbox.min_lon, bbox.max_lon, width)

        # Simple elevation model: Perlin-like noise approximation
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        elevation = (
            200 * np.sin(lat_grid * 3.0) * np.cos(lon_grid * 3.0)
            + 100 * np.sin(lat_grid * 7.0 + lon_grid * 5.0)
            + 50 * np.cos(lat_grid * 11.0 - lon_grid * 9.0)
            + 300  # Base elevation
        )
        elevation = np.clip(elevation, 0, 3000).astype(np.float32)

        from rasterio.transform import from_bounds

        transform = from_bounds(
            bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat,
            width, height,
        )

        metadata = {
            "transform": transform,
            "crs": "EPSG:4326",
            "bounds": bbox.as_tuple(),
            "resolution": 90,
        }
        return elevation, metadata

    def compute_hillshade(
        self,
        elevation: np.ndarray,
        azimuth: float = 315.0,
        altitude: float = 45.0,
    ) -> np.ndarray:
        """Compute hillshade from elevation array.

        Returns a 0-255 array suitable for overlay rendering.
        Azimuth 315 (NW light source) is the wargame convention.
        """
        ls = LightSource(azdeg=azimuth, altdeg=altitude)
        # Normalize elevation for hillshade
        if elevation.max() > elevation.min():
            hillshade = ls.hillshade(elevation, vert_exag=2.0)
        else:
            hillshade = np.ones_like(elevation) * 0.5
        return hillshade

    def compute_slope(self, elevation: np.ndarray, cell_size_m: float = 90.0) -> np.ndarray:
        """Compute slope in degrees from elevation array."""
        dy, dx = np.gradient(elevation, cell_size_m)
        slope_rad = np.arctan(np.sqrt(dx * dx + dy * dy))
        return np.degrees(slope_rad)

    def sample_at_point(
        self, elevation: np.ndarray, metadata: dict, lon: float, lat: float
    ) -> float:
        """Sample elevation at a geographic point."""
        transform = metadata["transform"]
        # Inverse transform: geo → pixel
        col, row = ~transform * (lon, lat)
        row, col = int(round(row)), int(round(col))
        if 0 <= row < elevation.shape[0] and 0 <= col < elevation.shape[1]:
            return float(elevation[row, col])
        return 0.0
