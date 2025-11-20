from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .data_loader import GTFSLoader
from .graph import TransitGraph
from .router import Router
from .realtime import RealTimeHandler
from .search import StationSearch
import os

app = FastAPI(title="NYC Transit API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/ui")
async def read_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

# Global instances
loader = None
graph = None
router = None
rt_handler = None
searcher = None

@app.on_event("startup")
async def startup_event():
    global loader, graph, router, rt_handler, searcher
    print("Initializing NYC Transit API...")
    loader = GTFSLoader()
    # Check if data exists, if not download (or use local)
    # In this env, we expect data to be present or config handles it
    loader.load_data()
    
    graph = TransitGraph(loader)
    router = Router(graph)
    rt_handler = RealTimeHandler()
    searcher = StationSearch(loader)
    print("Initialization complete.")

@app.get("/")
def read_root():
    return {"message": "Welcome to NYC Transit API"}

@app.get("/stations")
def search_stations(q: str = Query(..., min_length=2)):
    results = searcher.search(q)
    return {"results": results}

@app.get("/all_stations")
def get_all_stations():
    """Returns a list of all parent stations for dropdowns."""
    if not loader or loader.parent_stations is None:
        return {"stations": []}
    
    stations = []
    for _, row in loader.parent_stations.iterrows():
        stations.append({
            "id": str(row['stop_id']),
            "name": row['stop_name']
        })
    # Sort by name
    stations.sort(key=lambda x: x['name'])
    return {"stations": stations}

@app.get("/route")
def get_route(start: str, end: str):
    path = router.get_shortest_path(start, end)
    if not path:
        raise HTTPException(status_code=404, detail="No path found")
    return path

@app.get("/arrivals/{station_id}")
def get_arrivals(station_id: str):
    arrivals = rt_handler.get_arrivals(station_id)
    return {"station_id": station_id, "arrivals": arrivals}
