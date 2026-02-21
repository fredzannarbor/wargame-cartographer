"""Data download and cache management for geographic data."""

from __future__ import annotations

import hashlib
import io
import json
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from rich.console import Console
from shapely.geometry import Point

from wargame_cartographer.config.defaults import (
    CACHE_MAX_AGE_DAYS,
    NATURAL_EARTH_LAYERS,
    OVERPASS_API_URL,
)
from wargame_cartographer.config.map_spec import BoundingBox

console = Console()

DEFAULT_CACHE_DIR = Path.home() / "wargame-cartographer" / "cache"


def _bbox_hash(bbox: BoundingBox) -> str:
    key = f"{bbox.min_lon:.4f},{bbox.min_lat:.4f},{bbox.max_lon:.4f},{bbox.max_lat:.4f}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _is_fresh(path: Path, max_age_days: int = CACHE_MAX_AGE_DAYS) -> bool:
    if not path.exists():
        return False
    age_days = (time.time() - path.stat().st_mtime) / 86400
    return age_days < max_age_days


class DataDownloader:
    """Fetch and cache geographic data."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "vector").mkdir(exist_ok=True)
        (self.cache_dir / "osm").mkdir(exist_ok=True)
        (self.cache_dir / "elevation").mkdir(exist_ok=True)

    def get_natural_earth(
        self, layer: str, bbox: BoundingBox | None = None
    ) -> gpd.GeoDataFrame:
        """Download and cache Natural Earth vector data, clipped to bbox."""
        if layer not in NATURAL_EARTH_LAYERS:
            raise ValueError(f"Unknown layer: {layer}. Available: {list(NATURAL_EARTH_LAYERS.keys())}")

        cache_path = self.cache_dir / "vector" / f"ne_10m_{layer}"

        if not cache_path.exists() or not _is_fresh(cache_path):
            url = NATURAL_EARTH_LAYERS[layer]
            console.print(f"  Downloading Natural Earth {layer}...", style="dim")
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                cache_path.mkdir(parents=True, exist_ok=True)
                zf.extractall(cache_path)

        shp_files = list(cache_path.glob("*.shp"))
        if not shp_files:
            raise FileNotFoundError(f"No .shp file found in {cache_path}")

        gdf = gpd.read_file(shp_files[0])
        if bbox is not None:
            gdf = gdf.cx[bbox.min_lon:bbox.max_lon, bbox.min_lat:bbox.max_lat]
        return gdf

    def get_cities(self, bbox: BoundingBox) -> gpd.GeoDataFrame:
        """Get cities using Natural Earth populated_places (fast, no OSM needed)."""
        cache_key = f"cities_{_bbox_hash(bbox)}"
        cache_path = self.cache_dir / "osm" / f"{cache_key}.gpkg"

        if _is_fresh(cache_path):
            return gpd.read_file(cache_path)

        console.print("  Loading cities from Natural Earth...", style="dim")
        try:
            gdf = self.get_natural_earth("populated_places", bbox)
            if not gdf.empty:
                # Keep relevant columns
                cols = ["geometry", "NAME", "POP_MAX", "FEATURECLA"]
                existing = [c for c in cols if c in gdf.columns]
                gdf = gdf[existing].copy()
                # Rename for consistency
                if "NAME" in gdf.columns:
                    gdf = gdf.rename(columns={"NAME": "name"})
                if "POP_MAX" in gdf.columns:
                    gdf = gdf.rename(columns={"POP_MAX": "population"})
                gdf.to_file(cache_path, driver="GPKG")
            return gdf
        except Exception as e:
            console.print(f"  [yellow]City data failed: {e}[/yellow]")
            return gpd.GeoDataFrame()

    def get_ports(self, bbox: BoundingBox) -> gpd.GeoDataFrame:
        """Get ports via direct Overpass API query (fast)."""
        cache_key = f"ports_{_bbox_hash(bbox)}"
        cache_path = self.cache_dir / "osm" / f"{cache_key}.gpkg"

        if _is_fresh(cache_path):
            return gpd.read_file(cache_path)

        console.print("  Fetching ports from Overpass API...", style="dim")
        try:
            query = f"""
            [out:json][timeout:30];
            (
              node["harbour"="yes"]({bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon});
              node["landuse"="port"]({bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon});
              way["landuse"="port"]({bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon});
            );
            out center;
            """
            gdf = self._overpass_to_gdf(query)
            if not gdf.empty:
                gdf.to_file(cache_path, driver="GPKG")
            return gdf
        except Exception as e:
            console.print(f"  [yellow]Port fetch failed: {e}[/yellow]")
            return gpd.GeoDataFrame()

    def _overpass_to_gdf(self, query: str) -> gpd.GeoDataFrame:
        """Execute Overpass query and return GeoDataFrame of points."""
        resp = requests.post(
            OVERPASS_API_URL,
            data={"data": query},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        records = []
        for element in data.get("elements", []):
            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")
            if lat is None or lon is None:
                continue
            tags = element.get("tags", {})
            records.append({
                "geometry": Point(lon, lat),
                "name": tags.get("name", ""),
                "type": element.get("type", ""),
            })

        if not records:
            return gpd.GeoDataFrame()

        return gpd.GeoDataFrame(records, crs="EPSG:4326")
