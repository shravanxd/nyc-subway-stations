import h3

print(f"H3 Version: {h3.__version__}")

# Define a small polygon (Triangle)
# H3 native usually wants (lat, lon)
latgs = [
    (40.7, -74.0),
    (40.8, -74.0),
    (40.8, -73.9),
    (40.7, -74.0)
]

print("\n--- Test 1: h3.polygon_to_cells(dict) ---")
try:
    poly_dict = {
        'type': 'Polygon',
        'coordinates': [[
            [-74.0, 40.7], [-74.0, 40.8], [-73.9, 40.8], [-74.0, 40.7] # lon, lat
        ]]
    }
    res = h3.polygon_to_cells(poly_dict, 9)
    print(f"Success! {len(res)} hexes found.")
except Exception as e:
    print(f"Failed: {e}")

print("\n--- Test 2: h3.polygon_to_cells(h3.LatLngPoly()) ---")
try:
    # Note: LatLngPoly usually takes (lat, lon)
    poly_obj = h3.LatLngPoly(latgs)
    res = h3.polygon_to_cells(poly_obj, 9)
    print(f"Success! {len(res)} hexes found.")
except Exception as e:
    print(f"Failed: {e}")
