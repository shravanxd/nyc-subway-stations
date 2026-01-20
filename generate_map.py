import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen
import os

def generate_map():
    print("Loading data...")
    data_dir = "gtfs_supplemented"
    
    # Load Station Stats
    stats_df = pd.read_csv("station_stats.csv")
    
    # Load Entrances
    entrances_path = os.path.join(data_dir, "StationEntrances.csv")
    if os.path.exists(entrances_path):
        entrances_df = pd.read_csv(entrances_path)
    else:
        print("Warning: Station Entrances CSV not found.")
        entrances_df = pd.DataFrame()

    print("Initializing Map...")
    # Center on NYC
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=11, tiles="CartoDB dark_matter")
    Fullscreen().add_to(m)

    # --- 1. Plot Train Routes ---
    print("Processing Train Routes...")
    try:
        # Load Routes for colors
        routes_df = pd.read_csv(os.path.join(data_dir, "routes.txt"))
        # Create color map: route_id -> #Hex
        route_colors = {}
        for _, row in routes_df.iterrows():
            rid = str(row['route_id'])
            color = str(row['route_color'])
            if color == 'nan' or not color:
                color = "808080" # Default grey
            route_colors[rid] = f"#{color}"

        # Load Trips to map shape_id -> route_id
        # We only need unique shape_ids and their associated route
        trips_df = pd.read_csv(os.path.join(data_dir, "trips.txt"), usecols=['route_id', 'shape_id'])
        shape_to_route = trips_df.drop_duplicates('shape_id').set_index('shape_id')['route_id'].to_dict()
        
        # Load Shapes
        # reading this might take a moment as it is large
        print("Loading shapes.txt...")
        shapes_df = pd.read_csv(os.path.join(data_dir, "shapes.txt"))
        
        # Group points by shape_id
        # Creates a dict of shape_id -> list of [lat, lon]
        # This is faster than iterating groupby object for plotting often
        print("Building simplified shape geometries...")
        
        # Create a FeatureGroup for routes, hidden by default if user wants option to make them visible
        # "Option to make them visible" usually implies toggleable. 
        # Making it visible by default is usually better UX, but providing the control is key.
        routes_layer = folium.FeatureGroup(name="Train Routes", show=True, overlay=True).add_to(m)
        
        # Optimize: Group by shape_id and aggregate lat/lon into list
        # Using pandas groupby is efficient
        grouped_lines = shapes_df.sort_values('shape_pt_sequence').groupby('shape_id')[['shape_pt_lat', 'shape_pt_lon']].apply(lambda x: x.values.tolist()).to_dict()

        count = 0
        for shape_id, points in grouped_lines.items():
            if shape_id in shape_to_route:
                route_id = str(shape_to_route[shape_id])
                color = route_colors.get(route_id, "#808080")
                
                folium.PolyLine(
                    locations=points,
                    color=color,
                    weight=2,
                    opacity=0.8,
                    tooltip=f"Route {route_id}",
                    popup=f"Route {route_id} (Shape {shape_id})"
                ).add_to(routes_layer)
                count += 1
        print(f"Added {count} route shapes.")

    except Exception as e:
        print(f"Error processing routes: {e}")

    # --- 2. Plot Entrances ---
    if not entrances_df.empty:
        print("Adding Entrances...")
        # Entrances layer
        entrance_layer = folium.FeatureGroup(name="Entrances", show=True, overlay=True).add_to(m)
        entrance_cluster = MarkerCluster(name="Entrances Cluster").add_to(entrance_layer)
        
        for _, row in entrances_df.iterrows():
            try:
                lat = float(row['Entrance Latitude'])
                lon = float(row['Entrance Longitude'])
                name = row['Stop Name']
                ent_type = row['Entrance Type']
                
                # Icon color based on type
                color = 'green' if 'Elevator' in str(ent_type) else 'gray'
                
                # Popup
                popup_html = f"""
                <div style="font-family: sans-serif; font-size: 12px;">
                    <b>{name}</b><br>
                    Type: {ent_type}<br>
                    Entry: {row.get('Entry Allowed', 'N/A')}<br>
                    Exit: {row.get('Exit Allowed', 'N/A')}<br>
                    Lat: {lat:.5f}, Lon: {lon:.5f}
                </div>
                """
                
                # Descriptive Name for Tooltip
                tooltip_text = f"{name} Entrance ({ent_type})"
                
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=3,
                    color=color,
                    fill=True,
                    fill_opacity=0.7,
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=tooltip_text
                ).add_to(entrance_cluster)
            except Exception as e:
                continue

    # --- 3. Plot Stations ---
    print("Adding Stations...")
    # Determine min/max for scaling
    max_trains = stats_df['daily_train_count'].max()
    min_trains = stats_df['daily_train_count'].min()
    
    stations_layer = folium.FeatureGroup(name="Stations", show=True, overlay=True).add_to(m)
    
    for _, row in stats_df.iterrows():
        try:
            lat = row['stop_lat']
            lon = row['stop_lon']
            name = row['stop_name']
            
            # Popup Information
            popup_html = f"""
            <div style="font-family: sans-serif; font-size: 12px;">
                <h4 style="margin-bottom: 5px;">{row['stop_name']} ({row['parent_id']})</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td><b>Routes:</b></td><td>{row['routes_str']}</td></tr>
                    <tr><td><b>Weekday Trains:</b></td><td>{row['daily_train_count']}</td></tr>
                    <tr><td><b>Platforms:</b></td><td>{row['num_platforms']}</td></tr>
                    <tr><td><b>Entrances:</b></td><td>{row['num_entrances']}</td></tr>
                    <tr><td><b>Elevators:</b></td><td>{row['num_elevators']}</td></tr>
                    <tr><td><b>Accessible:</b></td><td>{row['accessibility']}</td></tr>
                </table>
            </div>
            """
            
            # Scale radius: 5 to 15
            if max_trains > min_trains:
                count = row['daily_train_count']
                norm = (count - min_trains) / (max_trains - min_trains)
                radius = 5 + (norm * 10)
            else:
                radius = 7
            
            # Color based on accessibility
            color = "#3388ff" # default blue
            fill_color = "#3388ff"
            if str(row['accessibility']) == 'YES':
                color = "#33ff88" # green
                fill_color = "#33ff88"
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color=color,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.8,
                weight=1,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{name} ({row['parent_id']})"
            ).add_to(stations_layer)
            
        except Exception as e:
            print(f"Skipping station {row.get('parent_id')}: {e}")
            continue

    folium.LayerControl(collapsed=False).add_to(m)
    
    output_file = "nyc_subway_map.html"
    print(f"Saving map to {output_file}...")
    m.save(output_file)
    print("Done!")

if __name__ == "__main__":
    generate_map()
