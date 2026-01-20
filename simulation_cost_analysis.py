import pandas as pd
import h3
import time
import numpy as np
from scipy.spatial import cKDTree
import random

# CONSTANTS
H3_RES = 9
K_STATIONS = 4 # Find nearest 4
SIM_USERS = 5

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

class SearchStats:
    def __init__(self, name):
        self.name = name
        self.latency_ms = 0
        self.distance_calcs = 0
        self.db_lookups = 0  # Simulating index/bucket fetches
        self.accuracy_rank = [] # List of station IDs found

def run_simulation():
    # 1. Load Data
    print("Loading Data...")
    df = pd.read_csv("station_stats.csv")
    
    # Setup H3 Index
    # Index mapping: H3_Cell -> [List of Station Indices]
    # This simulates a Key-Value Store (Redis/DynamoDB)
    h3_index = {}
    
    def get_h3(lat, lon):
        try: return h3.latlng_to_cell(lat, lon, H3_RES)
        except: return h3.geo_to_h3(lat, lon, H3_RES)

    df['h3'] = df.apply(lambda x: get_h3(x['stop_lat'], x['stop_lon']), axis=1)
    
    for idx, row in df.iterrows():
        cell = row['h3']
        if cell not in h3_index: h3_index[cell] = []
        h3_index[cell].append(idx)
        
    # Setup KD-Tree
    tree_coords = df[['stop_lat', 'stop_lon']].values
    tree = cKDTree(tree_coords)
    
    # Define Bounds for NYC (approx)
    lat_min, lat_max = 40.57, 40.91
    lon_min, lon_max = -74.04, -73.75
    
    print(f"\n--- Simulating {SIM_USERS} Users seeking nearest {K_STATIONS} Stations ---")
    
    results = []

    for user_id in range(1, SIM_USERS + 1):
        # Generate Random Location 
        u_lat = random.uniform(lat_min, lat_max)
        u_lon = random.uniform(lon_min, lon_max)
        print(f"\nUser {user_id} @ [{u_lat:.5f}, {u_lon:.5f}]")
        
        # --- Method 1: Brute Force (Baseline) ---
        stats_bf = SearchStats("Brute Force")
        t0 = time.perf_counter()
        
        # Calculate dist to ALL stations
        # "DB Lookup": 1 (Fetch all stations table)
        stats_bf.db_lookups = 1 
        distances = []
        for idx, row in df.iterrows():
            d = haversine(u_lat, u_lon, row['stop_lat'], row['stop_lon'])
            distances.append((d, row['stop_name']))
            stats_bf.distance_calcs += 1
            
        distances.sort(key=lambda x: x[0])
        found_bf = distances[:K_STATIONS]
        stats_bf.latency_ms = (time.perf_counter() - t0) * 1000
        
        print(f"  [Brute Force] Calcs: {stats_bf.distance_calcs}, Latency: {stats_bf.latency_ms:.3f}ms")

        # --- Method 2: KD-Tree ---
        stats_kd = SearchStats("KD-Tree")
        t0 = time.perf_counter()
        
        # Tree Query
        # "DB Lookup": 0 (Tree is typically in-memory) or 1 (Load Tree)
        # We assume in-memory structure
        dists, indices = tree.query([u_lat, u_lon], k=K_STATIONS)
        found_kd = []
        for i in indices:
            found_kd.append(df.iloc[i]['stop_name'])
            
        stats_kd.distance_calcs = int(np.log2(len(df))) # Theoretical checks approx
        stats_kd.latency_ms = (time.perf_counter() - t0) * 1000
        print(f"  [KD-Tree]     Calcs: ~{stats_kd.distance_calcs} (Tree Nodes), Latency: {stats_kd.latency_ms:.3f}ms")

        # --- Method 3: H3 Intelligent Search ---
        stats_h3 = SearchStats("H3 Index")
        t0 = time.perf_counter()
        
        center_cell = get_h3(u_lat, u_lon)
        candidates = []
        rings_checked = 0
        
        # Expand rings until we have at least 4x required candidates (heuristic for accuracy)
        # or enough to feel safe. 
        # For K=4, let's try to get at least 10 candidates before fine-sorting
        
        current_ring = 0
        while len(candidates) < K_STATIONS * 3 and current_ring < 10:
            stats_h3.db_lookups += 1 # 1 Lookup per ring batch usually, or per cell
            
            try: cells = h3.grid_disk(center_cell, current_ring)
            except: cells = h3.k_ring(center_cell, current_ring)
            
            # Identify new cells in this ring
            for c in cells:
                if c in h3_index:
                    for station_idx in h3_index[c]:
                        if station_idx not in candidates:
                            candidates.append(station_idx)
            
            # Optimization: If we found *some* stations in ring 0, we might still check ring 1
            # to be safe, but we stop expanding early.
            if len(candidates) > K_STATIONS * 2:
                break
            current_ring += 1
            
        # Fine Sort candidates
        candidate_dists = []
        for idx in candidates:
            row = df.iloc[idx]
            d = haversine(u_lat, u_lon, row['stop_lat'], row['stop_lon'])
            candidate_dists.append((d, row['stop_name']))
            stats_h3.distance_calcs += 1
            
        candidate_dists.sort(key=lambda x: x[0])
        found_h3 = candidate_dists[:K_STATIONS]
        stats_h3.latency_ms = (time.perf_counter() - t0) * 1000
        
        print(f"  [H3 Index]    Calcs: {stats_h3.distance_calcs} (Refined), Lookups: {stats_h3.db_lookups} (Rings), Latency: {stats_h3.latency_ms:.3f}ms")
        
        # Verification
        top_bf = [x[1] for x in found_bf]
        top_h3 = [x[1] for x in found_h3]
        match_type = "Exact"
        if top_bf != top_h3:
            overlap = len(set(top_bf).intersection(top_h3))
            match_type = f"{overlap}/{K_STATIONS} Overlap"
            print(f"  -> H3 Result: {match_type}")
        else:
            print("  -> H3 Result: MATCHES EXACTLY")

        # Collect Data
        results.append({
            "User": user_id,
            "Lat": u_lat,
            "Lon": u_lon,
            "BF_Latency_ms": stats_bf.latency_ms,
            "BF_Calcs": stats_bf.distance_calcs,
            "KD_Latency_ms": stats_kd.latency_ms,
            "KD_Calcs": stats_kd.distance_calcs,
            "H3_Latency_ms": stats_h3.latency_ms,
            "H3_Calcs": stats_h3.distance_calcs,
            "H3_Lookups": stats_h3.db_lookups,
            "H3_Match": match_type
        })

    print("\n\n--- COST & SCALE ANALYSIS ---")
    print("Assuming Cloud Infrastructure (e.g., AWS/GCP):")
    print("1. Brute Force:")
    print("   - Compute: High (Linear Scan). Fails at scale (1M users x 1000 stations).")
    print("   - API/DB: 1 'Full Table Scan' per query. Very expensive IO.")
    print("\n2. KD-Tree:")
    print("   - Compute: Low. Very fast.")
    print("   - Infra: Stateful. Requires maintaining the Tree structure in memory.")
    print("   - Scale: Hard to shard. You need the whole tree or complex spatial sharding.")
    print("\n3. H3 Index:")
    print("   - Compute: Low (Dict lookup + small sort).")
    print("   - Infra: Stateless/Serverless friendly. H3 mapping can be stored in Redis/DynamoDB.")
    print("   - Scale: Infinitely horizontally scalable. Shard Redis by H3 Prefix.")

    # Save Results to CSV
    results_df = pd.DataFrame(results)
    output_csv = "simulation_results.csv"
    print(f"\nSaving results to {output_csv}...")
    results_df.to_csv(output_csv, index=False)
    print("Done!")

if __name__ == "__main__":
    run_simulation()
