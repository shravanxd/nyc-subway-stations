import pandas as pd
import os
import json
from nyc_transit.config import GTFS_STATIC_DIR

def extract_stations():
    print(f"Extracting station data from {GTFS_STATIC_DIR}...")
    
    stops_path = os.path.join(GTFS_STATIC_DIR, 'stops.txt')
    if not os.path.exists(stops_path):
        print(f"Error: stops.txt not found in {GTFS_STATIC_DIR}")
        return

    stops = pd.read_csv(stops_path)
    
    # Filter for parent stations (location_type=1)
    # In some GTFS, parent stations are the main entry points.
    # We also want to capture line information if possible, but that's in stop_times/trips/routes.
    
    parent_stations = stops[stops['location_type'] == 1].copy()
    
    print(f"Found {len(parent_stations)} parent stations.")
    
    stations_data = []
    
    for _, row in parent_stations.iterrows():
        station_info = {
            'stop_id': str(row['stop_id']),
            'stop_name': row['stop_name'],
            'stop_lat': row['stop_lat'],
            'stop_lon': row['stop_lon'],
            'parent_station': row['parent_station'] if pd.notna(row['parent_station']) else None
        }
        stations_data.append(station_info)
        
    # Save to JSON
    output_file = 'stations_metadata.json'
    with open(output_file, 'w') as f:
        json.dump(stations_data, f, indent=2)
        
    print(f"Saved metadata for {len(stations_data)} stations to {output_file}")
    
    # Also print a sample
    print("\nSample Stations:")
    for s in stations_data[:5]:
        print(f"{s['stop_id']}: {s['stop_name']}")

if __name__ == "__main__":
    extract_stations()
