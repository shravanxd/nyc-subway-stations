import os
import requests
import zipfile
import pandas as pd
import io
from .config import GTFS_STATIC_URL, RAW_DATA_DIR

class GTFSLoader:
    def __init__(self, data_dir=RAW_DATA_DIR):
        self.data_dir = data_dir
        self.stops = None
        self.routes = None
        self.trips = None
        self.stop_times = None
        self.transfers = None

    def download_static_data(self):
        """Downloads and extracts the latest GTFS static data."""
        print(f"Downloading GTFS data from {GTFS_STATIC_URL}...")
        response = requests.get(GTFS_STATIC_URL)
        response.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(self.data_dir)
        print("Download and extraction complete.")

    def load_data(self):
        """Loads GTFS data into Pandas DataFrames."""
        print("Loading GTFS data into memory...")
        
        # Load stops
        self.stops = pd.read_csv(os.path.join(self.data_dir, 'stops.txt'))
        
        # Load routes
        self.routes = pd.read_csv(os.path.join(self.data_dir, 'routes.txt'))
        
        # Load trips (this can be large)
        self.trips = pd.read_csv(os.path.join(self.data_dir, 'trips.txt'))
        
        # Load stop_times (this is VERY large, might need optimization for prod)
        # For now, we'll load it all. In a real app, we might filter by active trips.
        self.stop_times = pd.read_csv(os.path.join(self.data_dir, 'stop_times.txt'))
        
        # Load transfers
        if os.path.exists(os.path.join(self.data_dir, 'transfers.txt')):
            self.transfers = pd.read_csv(os.path.join(self.data_dir, 'transfers.txt'))
        
        print("Data loaded.")
        self._preprocess_stops()

    def _preprocess_stops(self):
        """
        Enhances stops data.
        MTA GTFS has parent stations (e.g., '101') and child stops (e.g., '101N', '101S').
        We mainly care about parent stations for the graph nodes, but need children for specific routing.
        """
        # Ensure stop_id is string
        self.stops['stop_id'] = self.stops['stop_id'].astype(str)
        
        # Filter for parent stations (usually location_type=1) or just stops that are parents
        # In MTA data, parent stations have location_type=1
        self.parent_stations = self.stops[self.stops['location_type'] == 1].copy()
        
        print(f"Loaded {len(self.parent_stations)} parent stations.")

    def get_station_name(self, stop_id):
        """Returns the name of a station given its ID."""
        # Handle both parent and child IDs
        if not self.stops is None:
            station = self.stops[self.stops['stop_id'] == stop_id]
            if not station.empty:
                return station.iloc[0]['stop_name']
        return "Unknown Station"

if __name__ == "__main__":
    loader = GTFSLoader()
    loader.download_static_data()
    loader.load_data()
