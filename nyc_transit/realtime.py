import requests
from google.transit import gtfs_realtime_pb2
from .config import GTFS_REALTIME_URLS
import time

class RealTimeHandler:
    def __init__(self):
        # Cache feeds briefly to avoid spamming MTA API
        self.feed_cache = {}
        self.cache_ttl = 30 # seconds

    def get_feed(self, feed_id):
        """Fetches and parses a GTFS-RT feed."""
        url = GTFS_REALTIME_URLS.get(feed_id)
        if not url:
            print(f"Feed ID {feed_id} not found.")
            return None

        # Check cache
        if feed_id in self.feed_cache:
            timestamp, feed = self.feed_cache[feed_id]
            if time.time() - timestamp < self.cache_ttl:
                return feed
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            self.feed_cache[feed_id] = (time.time(), feed)
            return feed
        except Exception as e:
            print(f"Error fetching feed {feed_id}: {e}")
            return None

    def get_arrivals(self, station_id):
        """
        Get live arrivals for a specific station ID.
        Returns a list of dictionaries: {'route': 'A', 'time': timestamp, 'direction': 'N'}
        """
        # We need to check all feeds because we don't strictly know which feed a station is on 
        # without a mapping. For MVP, we'll check a few common ones or all.
        # Optimization: Map lines to feeds.
        
        arrivals = []
        
        # Iterate over all configured feeds
        for feed_key in GTFS_REALTIME_URLS.keys():
            feed = self.get_feed(feed_key)
            if not feed: continue
            
            for entity in feed.entity:
                if entity.HasField('trip_update'):
                    for stop_time_update in entity.trip_update.stop_time_update:
                        if stop_time_update.stop_id.startswith(station_id):
                            # Found a match!
                            route_id = entity.trip_update.trip.route_id
                            arrival_time = stop_time_update.arrival.time
                            
                            # Determine direction from stop_id (usually ends in N or S)
                            direction = stop_time_update.stop_id[-1] if stop_time_update.stop_id[-1] in ['N', 'S'] else '?'
                            
                            # Only future arrivals
                            if arrival_time > time.time():
                                arrivals.append({
                                    'route': route_id,
                                    'time': arrival_time,
                                    'minutes_away': int((arrival_time - time.time()) / 60),
                                    'direction': direction,
                                    'stop_id': stop_time_update.stop_id
                                })
                                
        # Sort by time
        arrivals.sort(key=lambda x: x['time'])
        return arrivals

