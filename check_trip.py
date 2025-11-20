from nyc_transit import GTFSLoader, TransitGraph, Router, RealTimeHandler
import time

def check_trip():
    print("Loading data...")
    loader = GTFSLoader()
    loader.load_data()
    graph = TransitGraph(loader)
    router = Router(graph)
    rt = RealTimeHandler()
    
    start_id = "R21" # 8 St-NYU
    end_id = "R16"   # Times Sq-42 St (N/Q/R/W platform)
    
    print(f"\nRouting from {start_id} to {end_id}...")
    path = router.get_shortest_path(start_id, end_id)
    
    if not path:
        # Try other Times Sq IDs if R16 fails (though R21->R16 should be direct)
        print("No direct path to R16, trying 127...")
        path = router.get_shortest_path(start_id, "127")
        
    if path:
        print(f"Route found! Est. time: {path['total_time_seconds'] // 60} mins")
        for step in path['steps']:
            print(f"  {step['routes']} {step['from']} -> {step['to']}")
            
        # Determine direction
        # If we are going R21 -> R16, that is generally Northbound (Uptown)
        # R21 is at 8th St, R16 is at 42nd St.
        
        print("\nChecking live arrivals at 8 St-NYU (R21)...")
        arrivals = rt.get_arrivals(start_id)
        
        print(f"Found {len(arrivals)} arrivals.")
        for a in arrivals:
            # We want Northbound (N) trains usually
            direction_str = "Uptown/Queens" if a['direction'] == 'N' else "Downtown/Brooklyn"
            print(f"  {a['route']} Train ({direction_str}) in {a['minutes_away']} mins")
            
    else:
        print("No path found.")

if __name__ == "__main__":
    check_trip()
