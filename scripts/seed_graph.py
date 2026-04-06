"""Seed the Lamp graph from Genesis genealogy data."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from lamp.config import SEED_DIR, GRAPH_FILE
from lamp.graph.store import GraphStore
from lamp.ingest.genesis_genealogy import load_seed_data


def main():
    print("Lamp — Seeding graph from Genesis genealogy data")
    print(f"  Seed file: {SEED_DIR / 'persons.json'}")
    print(f"  Graph output: {GRAPH_FILE}")
    print()

    store = GraphStore(GRAPH_FILE)
    counts = load_seed_data(SEED_DIR / "persons.json", store)
    store.save()

    stats = store.stats()
    print("Loaded:")
    print(f"  Persons:       {counts['persons']}")
    print(f"  Nations:       {counts['nations']}")
    print(f"  Relationships: {counts['relationships']}")
    print(f"  Nation links:  {counts['nation_links']}")
    print()
    print("Graph stats:")
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  Total edges: {stats['edges']}")
    print()
    print(f"Graph saved to {GRAPH_FILE}")


if __name__ == "__main__":
    main()
