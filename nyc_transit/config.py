import os

# MTA Data URLs
# MTA Data URLs
GTFS_STATIC_URL = "http://web.mta.info/developers/data/nyct/subway/google_transit.zip"

# Updated Public Realtime Feeds (No API Key Required)
GTFS_REALTIME_URLS = {
    'ACE': "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    'BDFM': "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    'G': "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
    'JZ': "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    'NQRW': "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    'L': "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
    '1234567': "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    'SIR': "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si"
}

# Local Data Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Use the provided local GTFS directory
GTFS_STATIC_DIR = os.path.join(BASE_DIR, "gtfs_supplemented")

# Keep these for compatibility if needed, or redirect them
DATA_DIR = BASE_DIR
RAW_DATA_DIR = GTFS_STATIC_DIR
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "processed_data")

# Ensure processed directory exists
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
