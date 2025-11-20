# NYC Transit Buddy

A Python library for NYC Subway routing, station search, and real-time arrival data.

## Installation

You can install this library directly from the source code using pip.

### Local Development (Recommended)
To install it in "editable" mode (changes to code reflect immediately):
```bash
pip install -e .
```

### Standard Installation
To install it like a standard package:
```bash
pip install .
```

Once installed, you can use it in any Python script on your system (provided you use the same Python environment).

## Usage

```python
from nyc_transit import GTFSLoader, TransitGraph, Router

# 1. Load Data (automatically uses local gtfs_supplemented folder)
loader = GTFSLoader()
loader.load_data()

# 2. Build Graph
graph = TransitGraph(loader)

# 3. Route
router = Router(graph)
path = router.get_shortest_path("127", "631") # Times Sq -> Grand Central
print(path)
```

## Data Setup
This library requires MTA GTFS data to function.
1. Download the static data (google_transit.zip) from [MTA Developer Resources](http://web.mta.info/developers/developer-data-terms.html).
2. Extract it into a folder named `gtfs_supplemented` in the project root.
   - Or, update `nyc_transit/config.py` to point to your data location.

## Features
- **Station Search**: Fuzzy search by name.
- **Routing**: Shortest path algorithms (Dijkstra).
- **Real-Time**: Live arrival times from MTA feeds.
- **Web UI**: Built-in route planner interface.

## Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](LICENSE)
