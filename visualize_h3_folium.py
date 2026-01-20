import pandas as pd
import h3
import folium
import json
from shapely.geometry import Polygon, mapping

# CONFIG
H3_RESOLUTION = 9 

def main():
    print("Loading Data...")
    df = pd.read_csv("station_stats.csv")
    
    # 1. Indexing
    print(f"Indexing H3 (Res {H3_RESOLUTION})...")
    try:
        df['h3_index'] = df.apply(lambda row: h3.latlng_to_cell(row['stop_lat'], row['stop_lon'], H3_RESOLUTION), axis=1)
    except AttributeError:
        df['h3_index'] = df.apply(lambda row: h3.geo_to_h3(row['stop_lat'], row['stop_lon'], H3_RESOLUTION), axis=1)
        
    # Aggergate counts
    hex_counts = df.groupby('h3_index').size().reset_index(name='count')
    print(f"Found {len(hex_counts)} unique hexagons.")

    # 2. Build GeoJSON for Hexagons
    # Converting H3 boundaries to GeoJSON Polygons
    features = []
    
    # 2. Build GeoJSON for Hexagons
    # Converting H3 boundaries to GeoJSON Polygons
    features = []
    
    # Generate Background Grid (Fill bounds)
    min_lat, max_lat = df['stop_lat'].min(), df['stop_lat'].max()
    min_lon, max_lon = df['stop_lon'].min(), df['stop_lon'].max()
    
    # Create a bounding box polygon (GeoJSON format: lon, lat)
    # Pad it slightly
    pad = 0.02
    # Create a bounding box polygon (GeoJSON format: lon, lat)
    # Pad it slightly
    pad = 0.02
    
    # Define polygon vertices as (lat, lon) for H3 v4 LatLngPoly
    poly_coords_latlng = [
        (min_lat-pad, min_lon-pad),
        (max_lat+pad, min_lon-pad),
        (max_lat+pad, max_lon+pad),
        (min_lat-pad, max_lon+pad),
        (min_lat-pad, min_lon-pad)
    ]
    
    # Get all hexes in this box
    try:
        # H3 v4
        geo_polygon = h3.LatLngPoly(poly_coords_latlng)
        all_hexes = h3.polygon_to_cells(geo_polygon, H3_RESOLUTION)
    except AttributeError:
        # H3 v3 fallback (unlikely given previous tests, but keeping safe)
        poly_dict = {
            'type': 'Polygon', 
            'coordinates': [[
                [min_lon-pad, min_lat-pad], 
                [min_lon-pad, max_lat+pad], 
                [max_lon+pad, max_lat+pad], 
                [max_lon+pad, min_lat-pad],
                [min_lon-pad, min_lat-pad] 
            ]]
        }
        all_hexes = h3.polyfill(poly_dict, H3_RESOLUTION)

    # Set of hexes that have stations
    station_hex_set = set(hex_counts['h3_index'].values)
    station_counts_map = hex_counts.set_index('h3_index')['count'].to_dict()

    for h in all_hexes:
        count = station_counts_map.get(h, 0)
        
        try:
            boundary = h3.cell_to_boundary(h)
        except AttributeError:
            boundary = h3.h3_to_geo_boundary(h)
            
        # Swap to (lon, lat) for GeoJSON
        geojson_coords = [[lon, lat] for lat, lon in boundary]
        geojson_coords.append(geojson_coords[0])
        
        # Style Logic
        if h in station_hex_set:
            # Active Station Hex
            style = {
                "fillColor": "#ffaa00" if count > 1 else "#3388ff",
                "color": "white",
                "weight": 1,
                "fillOpacity": 0.6
            }
            tooltip_txt = f"Hex: {h} (Stations: {count})"
        else:
            # Empty Grid Hex
            style = {
                "fillColor": "black",
                "color": "#444444",
                "weight": 0.5,
                "fillOpacity": 0.1
            }
            tooltip_txt = f"Hex: {h} (Empty)"

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [geojson_coords]
            },
            "properties": {
                "h3_index": h,
                "count": int(count),
                "style": style,
                "tooltip": tooltip_txt
            }
        }
        features.append(feature)
        
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }

    # 3. Create Folium Map
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=12, tiles="CartoDB dark_matter")
    
    # Add Hexagon Layer
    folium.GeoJson(
        geojson_data,
        name="H3 Grid",
        style_function=lambda x: x['properties']['style'],
        tooltip=folium.GeoJsonTooltip(fields=['tooltip'], aliases=['Info'])
    ).add_to(m)
    
    # Add Stations Layer
    stations = folium.FeatureGroup(name="Stations").add_to(m)
    for _, row in df.iterrows():
        color = "#33ff88" if row['accessibility'] == 'YES' else "#3388ff"
        folium.CircleMarker(
            location=[row['stop_lat'], row['stop_lon']],
            radius=4,
            color=color,
            fill=True,
            fill_opacity=0.9,
            popup=f"{row['stop_name']} ({row['h3_index']})"
        ).add_to(stations)

    folium.LayerControl().add_to(m)
    
    out_file = "nyc_subway_h3_folium_map.html"
    print(f"Saving to {out_file}...")
    m.save(out_file)
    print("Done!")

if __name__ == "__main__":
    main()
