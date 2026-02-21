"""Vector data loading: Natural Earth features + OSM POIs."""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd

from wargame_cartographer.config.map_spec import BoundingBox, MapSpec
from wargame_cartographer.geo.downloader import DataDownloader


@dataclass
class VectorData:
    """All vector geographic data for a map region."""

    coastline: gpd.GeoDataFrame
    land: gpd.GeoDataFrame
    rivers: gpd.GeoDataFrame
    lakes: gpd.GeoDataFrame
    countries: gpd.GeoDataFrame
    cities: gpd.GeoDataFrame
    ports: gpd.GeoDataFrame


def load_vector_data(bbox: BoundingBox, spec: MapSpec) -> VectorData:
    """Load all vector data needed for the map."""
    dl = DataDownloader()

    # Always load base geography
    coastline = dl.get_natural_earth("coastline", bbox)
    land = dl.get_natural_earth("land", bbox)
    rivers = dl.get_natural_earth("rivers", bbox) if spec.show_rivers else gpd.GeoDataFrame()
    lakes = dl.get_natural_earth("lakes", bbox)
    countries = dl.get_natural_earth("countries", bbox)

    cities = dl.get_cities(bbox) if spec.show_cities else gpd.GeoDataFrame()
    ports = dl.get_ports(bbox) if spec.show_ports else gpd.GeoDataFrame()

    return VectorData(
        coastline=coastline,
        land=land,
        rivers=rivers,
        lakes=lakes,
        countries=countries,
        cities=cities,
        ports=ports,
    )
