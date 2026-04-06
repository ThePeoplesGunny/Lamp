from pathlib import Path

# Project root paths
BACKEND_DIR = Path(__file__).parent.parent
DATA_DIR = BACKEND_DIR / "data"
SEED_DIR = DATA_DIR / "seed"
GRAPHS_DIR = DATA_DIR / "graphs"
EXTERNAL_DIR = DATA_DIR / "external"

# Graph persistence
GRAPH_FILE = GRAPHS_DIR / "lamp.json"

# API
API_PREFIX = "/api/v1"
