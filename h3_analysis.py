import pandas as pd
import h3
import time
import numpy as np
from scipy.spatial import cKDTree
import random

# Configuration
H3_RESOLUTION = 9  # Approx 0.1km^2, ~300m edge length
NUM_QUERIES = 1000  # Number of random points to benchmark
K_NEIGHBORS = 1     # Find nearest 1

def load_data():
    print("Loading station data...")
    df = pd.read_csv("station_stats.csv")
    return df

def add_h3_index(df, res):
    print(f"Indexing stations with H3 resolution {res}...")
    # h3.geo_to_h3(lat, lon, res) is the old API, new is latlng_to_cell
    try:
        df['h3_index'] = df.apply(lambda row: h3.latlng_to_cell(row['stop_lat'], row['stop_lon'], res), axis=1)
    except AttributeError:
        # Fallback for older h3 versions just in case
        df['h3_index'] = df.apply(lambda row: h3.geo_to_h3(row['stop_lat'], row['stop_lon'], res), axis=1)
    return df

def build_h3_lookup(df):
    """
    Build a dict of {h3_cell: [list_of_station_indices]}
    """
    lookup = {}
    for idx, row in df.iterrows():
        h = row['h3_index']
        if h not in lookup:
            lookup[h] = []
        lookup[h].append(idx)
    return lookup

def haversine(lat1, lon1, lat2, lon2):
    # Simple distance for verification (returns km)
    R = 6371  # Earth radius in km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

def h3_search(lat, lon, lookup_table, df, k=1):
    """
    Search for k nearest stations using H3 rings.
    1. Check center cell.
    2. Expand to k=1 ring, k=2 ring, etc. until we satisfy the count or exceed a limit.
    """
    try:
        center_cell = h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
    except AttributeError:
        center_cell = h3.geo_to_h3(lat, lon, H3_RESOLUTION)
        
    candidate_indices = []
    
    # Check center and expanding rings
    # For a dense city like NYC, 3 rings (k=3) covers quite a huge area approx 1km+ radius
    for disk_size in range(0, 5): 
        try:
            # grid_disk or k_ring
            cells = h3.grid_disk(center_cell, disk_size)
        except AttributeError:
            cells = h3.k_ring(center_cell, disk_size)
            
        found_in_ring = False
        for cell in cells:
            if cell in lookup_table:
                candidate_indices.extend(lookup_table[cell])
                found_in_ring = True
        
        # Heuristic: If we found candidates in this ring (or previous), 
        # stop expanding if we have enough to be reasonably sure we found the closest.
        # Note: A simple disk check isn't strictly "nearest" if the point is at the edge 
        # and the nearest is just across the boundary of the next ring. 
        # But usually checking 1 ring buffer is safe for "nearest".
        if found_in_ring and len(candidate_indices) >= k * 3:
            break
            
    if not candidate_indices:
        return None, float('inf')

    # Now exact distance on candidates
    candidates = df.loc[candidate_indices].copy()
    candidates['dist'] = candidates.apply(lambda row: haversine(lat, lon, row['stop_lat'], row['stop_lon']), axis=1)
    nearest = candidates.nsmallest(k, 'dist')
    return nearest.index[0], nearest.iloc[0]['dist']

def baseline_search_kdtree(lat, lon, tree, df):
    # Query KDTree
    # KDTree uses Euclidean distance, which is "okay" for small areas like NYC but not strictly geodetic.
    # For strict comparison we'd use BallTree with haversine, but cKDTree is the fast standard baseline.
    dist, idx = tree.query([lat, lon], k=1)
    # The index returned is the row index in the matrix used to build the tree
    return idx, dist

def main():
    # 1. Setup Data
    df = load_data()
    df = add_h3_index(df, H3_RESOLUTION)
    h3_lookup = build_h3_lookup(df)
    
    # Setup KD-Tree
    coords = df[['stop_lat', 'stop_lon']].values
    tree = cKDTree(coords)

    # 2. Generate Random Queries in NYC Bounds
    min_lat, max_lat = df['stop_lat'].min(), df['stop_lat'].max()
    min_lon, max_lon = df['stop_lon'].min(), df['stop_lon'].max()
    
    queries = []
    for _ in range(NUM_QUERIES):
        lat = random.uniform(min_lat, max_lat)
        lon = random.uniform(min_lon, max_lon)
        queries.append((lat, lon))
        
    print(f"\n--- Benchmarking {NUM_QUERIES} queries ---")
    
    # 3. Run H3 Benchmark
    start_time = time.time()
    h3_results = []
    for lat, lon in queries:
        idx, _ = h3_search(lat, lon, h3_lookup, df)
        h3_results.append(idx)
    h3_time = time.time() - start_time
    
    # 4. Run KD-Tree Benchmark
    start_time = time.time()
    kdtree_results = []
    for lat, lon in queries:
        idx, _ = baseline_search_kdtree(lat, lon, tree, df)
        # cKDTree returns position in the array, usually same as dataframe index if 0-N
        kdtree_results.append(idx)
    kdtree_time = time.time() - start_time
    
    # 5. Results
    print(f"H3 Search Time:       {h3_time:.4f}s ({h3_time/NUM_QUERIES*1000:.4f} ms/query)")
    print(f"KD-Tree Search Time:  {kdtree_time:.4f}s ({kdtree_time/NUM_QUERIES*1000:.4f} ms/query)")
    
    # Accuracy Check (Does H3 find the same 'nearest' as the mathematical tree?)
    # Note: KDTree is doing euclidean on lat/lon, Haversine is curved. 
    # Usually they match for very near points.
    matches = 0
    for h, k in zip(h3_results, kdtree_results):
        if h == k:
            matches += 1
    
    print(f"\nMatch Rate: {matches}/{NUM_QUERIES} ({matches/NUM_QUERIES*100:.1f}%)")
    print("Note: Mismatches may occur because KDTree uses Euclidean distance on lat/lon degrees,")
    print("while our H3 post-filter uses Haversine (Great Circle) distance.")
    
    # Output to simple text report
    with open("h3_benchmark_results.txt", "w") as f:
        f.write(f"H3 Resolution: {H3_RESOLUTION}\n")
        f.write(f"H3 Time: {h3_time:.4f}s\n")
        f.write(f"KD-Tree Time: {kdtree_time:.4f}s\n")
        f.write(f"Matches: {matches}/{NUM_QUERIES}\n")

if __name__ == "__main__":
    main()
