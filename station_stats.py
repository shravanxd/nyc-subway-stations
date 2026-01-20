import pandas as pd
import os
from nyc_transit import GTFSLoader
from nyc_transit.config import RAW_DATA_DIR

def main():
    print("Loading GTFS data...")
    loader = GTFSLoader()
    loader.load_data()
    
    # helper to get full path
    data_dir = loader.data_dir
    
    # Load calendar to confirm weekday service_id
    target_service_id = "Weekday"
    print(f"Filtering for service_id: {target_service_id}")
    
    # 1. Filter trips for the target day
    weekday_trips = loader.trips[loader.trips['service_id'] == target_service_id]
    
    if weekday_trips.empty:
        print(f"No trips found for service_id '{target_service_id}'. Unique service_ids: {loader.trips['service_id'].unique()}")
        return

    print(f"Found {len(weekday_trips)} weekday trips.")
    
    # 2. Get stop times for these trips
    print("Merging stop_times with trips...")
    weekday_stop_times = pd.merge(loader.stop_times, weekday_trips[['trip_id', 'route_id']], on='trip_id', how='inner')
    
    # 3. Work with Stops
    stops_df = loader.stops
    
    # Handle Parent vs Child
    # Based on our checks: location_type=1 is Parent.
    # Child stops have parent_station column populated.
    
    if 'parent_station' in stops_df.columns:
        # Identify Parents
        parents = stops_df[stops_df['location_type'] == 1].copy()
        
        # Calculate Platform Count (number of children per parent)
        # Children usually don't have location_type=1
        children = stops_df[stops_df['parent_station'].notna()]
        platform_counts = children.groupby('parent_station').size().reset_index(name='num_platforms')
        
        # Map stop_id in stop_times to parent_id
        stop_to_parent = stops_df.set_index('stop_id')['parent_station'].to_dict()
        
        def get_parent(sid):
            p = stop_to_parent.get(sid)
            if pd.isna(p) or not p:
                return sid 
            return p
            
        weekday_stop_times['parent_id'] = weekday_stop_times['stop_id'].apply(get_parent)
        
        # Base Station Info (Lat/Lon) from Parents
        # We'll use the parent's stop_lat/stop_lon
        station_info = parents[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']].rename(columns={'stop_id': 'parent_id'})
        
        # Merge Platform Counts
        station_info = pd.merge(station_info, platform_counts, left_on='parent_id', right_on='parent_station', how='left')
        station_info['num_platforms'] = station_info['num_platforms'].fillna(0).astype(int)
        
    else:
        print("Warning: No 'parent_station' column. Grouping by stop_id directly.")
        weekday_stop_times['parent_id'] = weekday_stop_times['stop_id']
        station_info = stops_df[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']].rename(columns={'stop_id': 'parent_id'})
        station_info['num_platforms'] = 1 # Mock if no hierarchy 

    # 4. Aggregate Stats
    print("Calculating statistics per station...")
    
    # Count total trains (trips) per station
    station_counts = weekday_stop_times.groupby('parent_id').size().reset_index(name='daily_train_count')
    
    # Count unique routes per station
    station_routes = weekday_stop_times.groupby('parent_id')['route_id'].unique().reset_index(name='routes')
    
    # Merge everything
    # station_info has [parent_id, stop_name, stop_lat, stop_lon, num_platforms]
    # stats has [daily_train_count, routes]
    
    stats = pd.merge(station_info, station_counts, on='parent_id', how='inner')
    stats = pd.merge(stats, station_routes, on='parent_id', how='inner')
    
    # Calculate number of routes
    stats['num_routes'] = stats['routes'].apply(len)
    
    # Format routes as string
    stats['routes_str'] = stats['routes'].apply(lambda x: ", ".join(sorted(map(str, x))))
    
    # Sort
    stats = stats.sort_values('daily_train_count', ascending=False)
    
    # 5. Add Entrance Data
    entrances_path = os.path.join(data_dir, "StationEntrances.csv")
    if os.path.exists(entrances_path):
        print("Loading Station Entrances data...")
        entrances = pd.read_csv(entrances_path)
        
        # Normalize GTFS Stop ID column (sometimes it has multiple IDs like "A12; D13")
        # We need to explode these to count entrances for each linked station ID
        # Note: In MTA data, Entrances are usually linked to the Complex, but here they have GTFS Stop ID.
        
        # Function to clean and split IDs
        def split_ids(x):
            if pd.isna(x):
                return []
            return [sid.strip() for sid in str(x).split(';')]

        entrances['valid_ids'] = entrances['GTFS Stop ID'].apply(split_ids)
        entrances_exploded = entrances.explode('valid_ids')
        
        # Aggregate per GTFS Stop ID
        entrance_stats = entrances_exploded.groupby('valid_ids').agg(
            num_entrances=('Entrance Type', 'count'),
            num_elevators=('Entrance Type', lambda x: (x == 'Elevator').sum()),
            accessibility=('Entrance Type', lambda x: 'YES' if (x == 'Elevator').any() else 'NO')
        ).reset_index().rename(columns={'valid_ids': 'parent_id'})
        
        # Merge with main stats
        print("Merging entrance statistics...")
        stats = pd.merge(stats, entrance_stats, on='parent_id', how='left')
        
        # Fill NaNs for stations without entrance data (e.g. out of system or missing in csv)
        stats['num_entrances'] = stats['num_entrances'].fillna(0).astype(int)
        stats['num_elevators'] = stats['num_elevators'].fillna(0).astype(int)
        stats['accessibility'] = stats['accessibility'].fillna('NO')
        
    else:
        print("Warning: StationEntrances.csv not found using default values.")
        stats['num_entrances'] = 0
        stats['num_elevators'] = 0
        stats['accessibility'] = 'NO'

    # Reorder columns
    cols = ['parent_id', 'stop_name', 'stop_lat', 'stop_lon', 'num_platforms', 'num_routes', 'routes_str', 'daily_train_count', 'num_entrances', 'num_elevators', 'accessibility']
    stats = stats[cols]
    
    output_file = "station_stats.csv"
    print(f"Saving statistics to {output_file}...")
    stats.to_csv(output_file, index=False)
    
    print("Preview of Top 5 Stations:")
    print(stats.head().to_string(index=False))

if __name__ == "__main__":
    main()
