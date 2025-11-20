import argparse
import uvicorn
from nyc_transit import GTFSLoader, TransitGraph, Router, RealTimeHandler, StationSearch
import sys

def interactive_mode():
    print("Loading data...")
    loader = GTFSLoader()
    loader.load_data()
    graph = TransitGraph(loader)
    router = Router(graph)
    searcher = StationSearch(loader)
    rt_handler = RealTimeHandler()
    print("Ready!")

    while True:
        print("\nOptions: [1] Search Station [2] Route [3] Live Arrivals [q] Quit")
        choice = input("> ")
        
        if choice == 'q':
            break
        
        if choice == '1':
            q = input("Enter station name: ")
            results = searcher.search(q)
            for r in results:
                print(f"{r['id']}: {r['name']}")
                
        elif choice == '2':
            start = input("Start Station ID: ")
            end = input("End Station ID: ")
            path = router.get_shortest_path(start, end)
            if path:
                print(f"Total Time: {path['total_time_seconds'] // 60} mins")
                for step in path['steps']:
                    print(f"{step['routes']} {step['from']} -> {step['to']} ({step['duration']}s)")
            else:
                print("No path found.")
                
        elif choice == '3':
            sid = input("Station ID: ")
            arrivals = rt_handler.get_arrivals(sid)
            for a in arrivals:
                print(f"{a['route']} to {a['direction']} in {a['minutes_away']} mins")

def main():
    parser = argparse.ArgumentParser(description="NYC Transit Module")
    parser.add_argument("--api", action="store_true", help="Run as API server")
    args = parser.parse_args()

    if args.api:
        uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
    else:
        interactive_mode()

if __name__ == "__main__":
    main()
