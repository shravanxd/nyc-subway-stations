import networkx as nx

class Router:
    def __init__(self, graph_wrapper):
        self.graph_wrapper = graph_wrapper
        self.graph = graph_wrapper.graph

    def get_shortest_path(self, start_stop_id, end_stop_id):
        """
        Finds the shortest path between two stops.
        Returns a list of steps.
        """
        try:
            path = nx.shortest_path(self.graph, source=start_stop_id, target=end_stop_id, weight='weight')
            
            # Reconstruct journey details
            journey = []
            total_time = 0
            
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                edge_data = self.graph[u][v]
                weight = edge_data['weight']
                total_time += weight
                
                step = {
                    'from': self.graph_wrapper.loader.get_station_name(u),
                    'from_id': u,
                    'to': self.graph_wrapper.loader.get_station_name(v),
                    'to_id': v,
                    'duration': weight,
                    'type': edge_data.get('type', 'unknown'),
                    'routes': list(edge_data.get('routes', []))
                }
                journey.append(step)
                
            return {
                'total_time_seconds': total_time,
                'steps': journey
            }
            
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None

