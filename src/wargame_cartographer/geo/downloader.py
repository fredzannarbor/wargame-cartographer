"""Data download and cache management for geographic data."""

from __future__ import annotations

import hashlib
import io
import os
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import requests
from rich.console import Console

from wargame_cartographer.config.defaults import (
    CACHE_MAX_AGE_DAYS,
    NATURAL_EARTH_LAYERS,
)
from wargame_cartographer.config.map_spec import BoundingBox

console = Console()

DEFAULT_CACHE_DIR = Path.home() / "wargame-cartographer" / "cache"


def _bbox_hash(bbox: BoundingBox) -> str:
    """Content-addressed hash for a bounding box."""
    key = f"{bbox.min_lon:.4f},{bbox.min_lat:.4f},{bbox.max_lon:.4f},{bbox.max_lat:.4f}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _is_fresh(path: Path, max_age_days: int = CACHE_MAX_AGE_DAYS) -> bool:
    """Check if a cached file is still fresh."""
    if not path.exists():
        return False
    age_days = (time.time() - path.stat().st_mtime) / 86400
    return age_days < max_age_days


class DataDownloader:
    """Fetch and cache geographic data: Natural Earth vectors and OSM POIs."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "vector").mkdir(exist_ok=True)
        (self.cache_dir / "osm").mkdir(exist_ok=True)
        (self.cache_dir / "elevation").mkdir(exist_ok=True)

    def get_natural_earth(
        self, layer: str, bbox: BoundingBox | None = None
    ) -> gpd.GeoDataFrame:
        """Download and cache Natural Earth vector data, optionally clipped to bbox."""
        if layer not in NATURAL_EARTH_LAYERS:
            raise ValueError(f"Unknown layer: {layer}. Available: {list(NATURAL_EARTH_LAYERS.keys())}")

        cache_path = self.cache_dir / "vector" / f"ne_10m_{layer}"

        if not cache_path.exists() or not _is_fresh(cache_path):
            url = NATURAL_EARTH_LAYERS[layer]
            console.print(f"  Downloading Natural Earth {layer}...", style="dim")
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()

            # Extract zip to cache
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                cache_path.mkdir(parents=True, exist_ok=True)
                zf.extractall(cache_path)

        # Find shapefile in extracted directory
        shp_files = list(cache_path.glob("*.shp"))
        if not shp_files:
            raise FileNotFoundError(f"No .shp file found in {cache_path}")

        gdf = gpd.read_file(shp_files[0])

        if bbox is not None:
            gdf = gdf.cx[bbox.min_lon:bbox.max_lon, bbox.min_lat:bbox.max_lat]

        return gdf

    def get_osm_cities(self, bbox: BoundingBox) -> gpd.GeoDataFrame:
        """Fetch cities/towns from OSM via osmnx."""
        cache_key = f"cities_{_bbox_hash(bbox)}"
        cache_path = self.cache_dir / "osm" / f"{cache_key}.gpkg"

        if _is_fresh(cache_path):
            return gpd.read_file(cache_path)

        console.print("  Fetching cities from OpenStreetMap...", style="dim")
        try:
            import osmnx as ox

            tags = {"place": ["city", "town"]}
            gdf = ox.features_from_bbox(
                bbox=(bbox.max_lat, bbox.min_lat, bbox.max_lon, bbox.min_lon),
                tags=tags,
            )
            # Keep only point geometries and key columns
            if not gdf.empty:
                gdf = gdf[gdf.geometry.type == "Point"].copy()
                cols_to_keep = ["geometry", "name", "place", "population"]
                existing = [c for c in cols_to_keep if c in gdf.columns]
                gdf = gdf[existing].copy()
                gdf.to_file(cache_path, driver="GPKG")
            return gdf
        except Exception as e:
            console.print(f"  [yellow]OSM city fetch failed: {e}[/yellow]")
            return gpd.GeoDataFrame()

    def get_osm_ports(self, bbox: BoundingBox) -> gpd.GeoDataFrame:
        """Fetch ports from OSM."""
        cache_key = f"ports_{_bbox_hash(bbox)}"
        cache_path = self.cache_dir / "osm" / f"{cache_key}.gpkg"

        if _is_fresh(cache_path):
            return gpd.read_file(cache_path)

        console.print("  Fetching ports from OpenStreetMap...", style="dim")
        try:
            import osmnx as ox

            tags = {"harbour": True, "landuse": "port"}
            gdf = ox.features_from_bbox(
                bbox=(bbox.max_lat, bbox.min_lat, bbox.max_lon, bbox.min_lon),
                tags=tags,
            )
            if not gdf.empty:
                gdf.to_file(cache_path, driver="GPKG")
            return gdf
        except Exception:
            return gpd.GeoDataFrame()

    def get_osm_roads(self, bbox: BoundingBox) -> gpd.GeoDataFrame:
        """Fetch major roads from OSM."""
        cache_key = f"roads_{_bbox_hash(bbox)}"
        cache_path = self.cache_dir / "osm" / f"{cache_key}.gpkg"

        if _is_fresh(cache_path):
            return gpd.read_file(cache_path)

        console.print("  Fetching roads from OpenStreetMap...", style="dim")
        try:
            import osmnx as ox

            G = ox.graph_from_bbox(
                bbox=(bbox.max_lat, bbox.min_lat, bbox.max_lon, bbox.min_lon),
                network_type="drive",
                truncate_by_edge=True,
            )
            _, gdf_edges = ox.graph_to_gdfs(G)
            gdf_edges.to_file(cache_path, driver="GPKG")
            return gdf_edges
        except Exception:
            return gpd.GeoDataFrame()
