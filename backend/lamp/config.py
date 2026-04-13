from pathlib import Path

# Project root paths
BACKEND_DIR = Path(__file__).parent.parent
DATA_DIR = BACKEND_DIR / "data"
SEED_DIR = DATA_DIR / "seed"
GRAPHS_DIR = DATA_DIR / "graphs"
EXTERNAL_DIR = DATA_DIR / "external"
VERSES_DIR = DATA_DIR / "verses"

# Graph persistence
GRAPH_FILE = GRAPHS_DIR / "lamp.json"

# Verse text + translations SQLite store (keyed by verse ID, parallels graph)
VERSES_DB_FILE = VERSES_DIR / "verses.db"

# API
API_PREFIX = "/api/v1"
