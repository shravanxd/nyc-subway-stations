import networkx as nx
import pandas as pd
from datetime import datetime, timedelta

class TransitGraph:
    def __init__(self, loader):
        self.loader = loader
        self.graph = nx.DiGraph()
        self.build_graph()

    def build_graph(self):
        """Builds the transit graph from loaded GTFS data."""
        print("Building transit graph...")
        
        # Add nodes (stops)
        # We use stop_id as the node identifier.
        # We might want to use parent_station for a simplified graph, 
        # but for accurate routing (including specific platforms), we use all stops.
        for _, stop in self.loader.stops.iterrows():
            self.graph.add_node(
                stop['stop_id'], 
                name=stop['stop_name'], 
                lat=stop['stop_lat'], 
                lon=stop['stop_lon'],
                parent=stop['parent_station'] if pd.notna(stop['parent_station']) else None
            )

        # Add edges from stop_times (Trip segments)
        # This is the heavy part. We need to connect consecutive stops in trips.
        # To speed this up, we can group by trip_id and sort by stop_sequence.
        
        # Optimization: We don't need EVERY trip. Many trips have identical patterns.
        # But for a full schedule-aware router, we do. 
        # For a simplified "average time" router, we can average the times.
        # Let's do a simplified version first: Average travel time between adjacent stops.
        
        print("Processing stop_times for edges...")
        stop_times = self.loader.stop_times.sort_values(['trip_id', 'stop_sequence'])
        
        # Create a shifted dataframe to get previous stop info
        stop_times['next_stop_id'] = stop_times.groupby('trip_id')['stop_id'].shift(-1)
        stop_times['next_arrival_time'] = stop_times.groupby('trip_id')['arrival_time'].shift(-1)
        
        # Filter out the last stop of each trip
        edges_df = stop_times.dropna(subset=['next_stop_id'])
        
        # Calculate travel time (simplified, assuming valid H:M:S)
        # Note: GTFS times can go past 24:00:00 (e.g., 25:30:00).
        def parse_time(t_str):
            h, m, s = map(int, t_str.split(':'))
            return h * 3600 + m * 60 + s

        # We can't easily vectorize the time diff because of the 24h wrap, but let's try a rough approx
        # For now, let's just take unique edges and assign a default weight if we want to be fast,
        # or do it properly. Let's do it properly but aggregated.
        
        # Group by (stop_id, next_stop_id) to find average travel time
        # This avoids adding millions of edges for every single trip.
        
        # First, we need to compute duration for each segment.
        # This is slow in pure Python loop. Let's try to do it with pandas if possible, 
        # but the time parsing is tricky.
        
        # Let's iterate over unique route segments instead.
        # A "route segment" is defined by a unique sequence of stops.
        
        # Actually, for a MVP, let's just iterate and add edges. 
        # If an edge exists, we update the weight (average).
        
        edge_weights = {} # (u, v) -> [times]
        
        # Taking a sample or just processing all might be slow.
        # Let's try processing a subset or using a faster method.
        # We will use the 'trips' to get the route_id for the edge.
        
        # Let's merge trips to get route_id
        edges_df = edges_df.merge(self.loader.trips[['trip_id', 'route_id']], on='trip_id')
        
        # We only care about unique (stop_id, next_stop_id, route_id) tuples for the graph structure
        # But we need average time.
        
        # Let's just take the first occurrence for now to speed up build time for this demo.
        # In a real app, we'd pre-calculate this.
        unique_segments = edges_df.drop_duplicates(subset=['stop_id', 'next_stop_id', 'route_id'])
        
        count = 0
        for _, row in unique_segments.iterrows():
            u = row['stop_id']
            v = row['next_stop_id']
            route_id = row['route_id']
            
            # Rough estimate of travel time: difference in arrival times
            # This is tricky without parsing all times. 
            # Let's assume 2 minutes (120s) for intra-station, unless we parse.
            t1 = parse_time(row['departure_time'])
            t2 = parse_time(row['next_arrival_time'])
            duration = t2 - t1
            
            if duration < 0: duration += 24*3600 # Handle day wrap
            
            # Add edge
            # We might have multiple edges between nodes (different lines).
            # NetworkX MultiDiGraph could work, or just store list of lines in edge data.
            if self.graph.has_edge(u, v):
                self.graph[u][v]['routes'].add(route_id)
                # Update average time? For now keep the first one found or min?
                # Let's keep min time (fastest line).
                self.graph[u][v]['weight'] = min(self.graph[u][v]['weight'], duration)
            else:
                self.graph.add_edge(u, v, weight=duration, routes={route_id}, type='transit')
            
            count += 1
            
        print(f"Added {count} transit edges.")

        # Add transfers
        # 1. Explicit transfers from transfers.txt
        if self.loader.transfers is not None:
            print("Processing transfers...")
            for _, row in self.loader.transfers.iterrows():
                u = row['from_stop_id']
                v = row['to_stop_id']
                t_type = row['transfer_type']
                min_time = row['min_transfer_time']
                
                weight = float(min_time) if pd.notna(min_time) else 180 # Default 3 mins
                
                if t_type == 2: # Requires min time
                    self.graph.add_edge(u, v, weight=weight, type='transfer')
                elif t_type == 0: # Recommended transfer point
                    self.graph.add_edge(u, v, weight=weight, type='transfer')
                    
        # 2. Implicit transfers (Parent Station <-> Child Stop)
        # This allows routing from "Times Sq" (Parent) to specific platform "127N" (Child)
        print("Adding parent-child connections...")
        for _, stop in self.loader.stops.iterrows():
            if pd.notna(stop['parent_station']):
                parent = stop['parent_station']
                child = stop['stop_id']
                # Parent -> Child (0 cost, or small cost to represent walking to platform)
                self.graph.add_edge(parent, child, weight=30, type='parent_child')
                # Child -> Parent
                self.graph.add_edge(child, parent, weight=30, type='child_parent')

        print(f"Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

