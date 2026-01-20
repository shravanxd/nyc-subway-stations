import pandas as pd
import h3
import pydeck as pdk
import os

# CONFIG
H3_RESOLUTION = 9
MAPBOX_API_KEY = "pk.eyJ1Ijoic2hyYXZhbjEyMTIiLCJhIjoiY21heDRuendzMGx6ZTJ2cTFjN3MwNGJnbyJ9.mIJu4TbgHH3N3PwKIlRBWg"

def main():
    print("Loading Data...")
    df = pd.read_csv("station_stats.csv")
    
    # Add Index
    print(f"Indexing H3 (Res {H3_RESOLUTION})...")
    try:
        df['h3_index'] = df.apply(lambda row: h3.latlng_to_cell(row['stop_lat'], row['stop_lon'], H3_RESOLUTION), axis=1)
    except AttributeError:
        df['h3_index'] = df.apply(lambda row: h3.geo_to_h3(row['stop_lat'], row['stop_lon'], H3_RESOLUTION), axis=1)
        
    # Aggregate counts per hexagon
    # We want to know how many stations are in each hex to color it
    hex_counts = df.groupby('h3_index').size().reset_index(name='count')
    
    print(f"Found {len(hex_counts)} unique hexagons.")

    # Define Layers
    
    # 1. H3 Hexagon Layer
    layer_hex = pdk.Layer(
        "H3HexagonLayer",
        hex_counts,
        pickable=True,
        stroked=True,
        filled=True,
        extruded=False, # Flat hexagons
        get_hexagon="h3_index",
        get_fill_color="[255, (1 - count / 4) * 255, 0, 100]", # Heatmap-ish color
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
    )

    # 2. Scatterplot Layer (Stations)
    # Color based on accessibility (Green=Yes, Blue=No)
    df['color'] = df['accessibility'].apply(lambda x: [0, 255, 128, 200] if x == 'YES' else [0, 128, 255, 200])
    
    layer_stations = pdk.Layer(
        "ScatterplotLayer",
        df,
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_scale=6,
        radius_min_pixels=3,
        radius_max_pixels=10,
        line_width_min_pixels=1,
        get_position=["stop_lon", "stop_lat"],
        get_radius="daily_train_count", # Size by traffic
        get_fill_color="color",
        get_line_color=[0, 0, 0],
    )

    # View State
    view_state = pdk.ViewState(
        latitude=40.7128,
        longitude=-74.0060,
        zoom=11,
        bearing=0,
        pitch=0
    )

    # Render
    r = pdk.Deck(
        layers=[layer_hex, layer_stations],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10",
        api_keys={"mapbox": MAPBOX_API_KEY},
        tooltip={"text": "Station: {stop_name}\nHex: {h3_index}"}
    )
    
    output_file = "nyc_subway_h3_map.html"
    print(f"Saving to {output_file}...")
    r.to_html(output_file)
    print("Done!")

if __name__ == "__main__":
    main()
