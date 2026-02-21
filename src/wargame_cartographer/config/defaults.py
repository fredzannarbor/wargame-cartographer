"""Default configuration values."""

# Natural Earth data URLs (10m resolution)
NATURAL_EARTH_BASE = "https://naciscdn.org/naturalearth"
NATURAL_EARTH_LAYERS = {
    "coastline": f"{NATURAL_EARTH_BASE}/10m/physical/ne_10m_coastline.zip",
    "land": f"{NATURAL_EARTH_BASE}/10m/physical/ne_10m_land.zip",
    "ocean": f"{NATURAL_EARTH_BASE}/10m/physical/ne_10m_ocean.zip",
    "rivers": f"{NATURAL_EARTH_BASE}/10m/physical/ne_10m_rivers_lake_centerlines.zip",
    "lakes": f"{NATURAL_EARTH_BASE}/10m/physical/ne_10m_lakes.zip",
    "countries": f"{NATURAL_EARTH_BASE}/10m/cultural/ne_10m_admin_0_countries.zip",
    "states": f"{NATURAL_EARTH_BASE}/10m/cultural/ne_10m_admin_1_states_provinces.zip",
    "populated_places": f"{NATURAL_EARTH_BASE}/10m/cultural/ne_10m_populated_places.zip",
}

# Overpass API for targeted OSM queries
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# Cache settings
CACHE_MAX_AGE_DAYS = 30

# Default map dimensions
DEFAULT_DPI = 300
DEFAULT_OUTPUT_WIDTH_MM = 500
DEFAULT_OUTPUT_HEIGHT_MM = 700
