import pandas as pd

class StationSearch:
    def __init__(self, loader):
        self.loader = loader
        self.stations = loader.parent_stations

    def search(self, query, limit=10):
        """
        Fuzzy search for stations by name.
        """
        if not query:
            return []
        
        query = query.lower()
        
        # Simple substring match for now. 
        # Could upgrade to Levenshtein distance later.
        matches = self.stations[self.stations['stop_name'].str.lower().str.contains(query)]
        
        results = []
        for _, row in matches.head(limit).iterrows():
            results.append({
                'id': row['stop_id'],
                'name': row['stop_name'],
                'lat': row['stop_lat'],
                'lon': row['stop_lon']
            })
            
        return results
