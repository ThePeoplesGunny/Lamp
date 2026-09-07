"""Seed the Lamp graph from curated entity seed data.

ADDITIVE. This script replaces the entity layer (person / place / nation) and
leaves everything else in the graph alone.

Why it is written this way
--------------------------
It used to build a brand-new empty graph and save it over lamp.json. Because it
never called store.load(), that overwrite erased all 31,172 verse nodes and all
144 verse→verse QUOTES edges from the graph JSON. Recovering them meant
re-running seed_verses.py — and that, in turn, destroyed all 31,104 KJV
translation rows, because insert_verses used "INSERT OR REPLACE", which SQLite
performs as DELETE-then-INSERT, firing ON DELETE CASCADE on the translations
table. So one entity-seed change cost a full six-script rebuild.

Both halves are now fixed. insert_verses upserts instead of replacing (see
lamp/verse_store.py), and this script loads the existing graph first.

What a run changes:
  - person / place / nation nodes ....... replaced from the seed files
  - entity→entity edges ................. replaced (they are re-created by the seed loader)
  - verse→entity MENTIONS edges ......... dropped with the old entity nodes, then
                                          rebuilt in-process by link_entities_to_verses
  - verse nodes ......................... untouched
  - verse→verse QUOTES edges ............ untouched
  - verses.db (text + translations) ..... never opened; see the note below

The GraphStore is constructed WITHOUT verse_db_path on purpose. That gives it an
in-memory SQLite store, so this script cannot write to the real verses.db even
by accident. It only ever needs graph structure.

Usage:
    python scripts/seed_graph.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from lamp.config import SEED_DIR, GRAPH_FILE  # noqa: E402
from lamp.graph.store import GraphStore  # noqa: E402
from lamp.ingest.genesis_genealogy import load_seed_data  # noqa: E402
from lamp.ingest.verse_links import ENTITY_NODE_TYPES, link_entities_to_verses  # noqa: E402


def main() -> int:
    print("Lamp — Seeding entity layer from curated seed data")
    print(f"  Seed dir:     {SEED_DIR}")
    print(f"  Graph file:   {GRAPH_FILE}")
    print()

    # No verse_db_path: in-memory verse store, so verses.db is never opened.
    store = GraphStore(GRAPH_FILE)
    store.load()

    before = store.stats()
    existed = GRAPH_FILE.exists()
    if existed:
        print("Existing graph loaded:")
        print(f"  Verses:   {before['verses']}")
        print(f"  Entities: {before['persons'] + before['places'] + before['nations']}")
        print(f"  Edges:    {before['edges']}")
    else:
        print("No existing graph — building from scratch.")
    print()

    # Replace only the entity layer. Removing a node also removes every edge
    # incident to it, which is why MENTIONS edges are rebuilt further down.
    stale = [
        n for n, d in store.G.nodes(data=True)
        if d.get("node_type") in ENTITY_NODE_TYPES
    ]
    store.G.remove_nodes_from(stale)
    print(f"Removed {len(stale)} existing entity node(s) and their edges.")

    counts = load_seed_data(SEED_DIR / "persons.json", store)
    print("Seeded:")
    print(f"  Persons:       {counts['persons']}")
    print(f"  Nations:       {counts['nations']}")
    print(f"  Places:        {counts.get('places', 0)}")
    print(f"  Relationships: {counts['relationships']}")
    print(f"  Nation links:  {counts['nation_links']}")
    print(f"  Place links:   {counts.get('place_links', 0)}")
    print()

    # Rebuild verse→entity MENTIONS in the same run. Doing this here rather than
    # telling the operator to run seed_verse_links.py afterwards is the point:
    # a reminder in a print statement is not a guarantee.
    after_seed = store.stats()
    if after_seed["verses"] == 0:
        print("No verse nodes in graph — skipping MENTIONS relink.")
        print("  Run seed_verses.py / seed_verses_nt.py, then seed_verse_links.py.")
    else:
        link = link_entities_to_verses(store)
        print("Relinked entity ↔ verse MENTIONS:")
        print(f"  Entities linked: {link.entities_linked} / {link.entities_total}")
        print(f"  MENTIONS edges:  {link.edges_added}")
        if link.missing_verses:
            total_missing = sum(link.missing_verses.values())
            print(f"  Refs skipped (verse node absent): {total_missing}")
            for book, n in link.missing_verses.most_common(10):
                print(f"    {book}: {n}")
    print()

    after = store.stats()
    print("Graph stats:")
    print(f"  Persons:     {after['persons']}")
    print(f"  Places:      {after['places']}")
    print(f"  Nations:     {after['nations']}")
    print(f"  Verses:      {after['verses']}")
    print(f"  Total nodes: {after['total_nodes']}")
    print(f"  Total edges: {after['edges']}")
    print()

    # Gate, checked BEFORE the write. Verse nodes must survive an entity reseed.
    # If they did not, refusing to save is what protects lamp.json — reporting it
    # after store.save() would only describe a file that is already damaged.
    if existed and after["verses"] != before["verses"]:
        print(
            f"ERROR: verse node count changed {before['verses']} -> {after['verses']}. "
            "The entity reseed must leave verse nodes untouched."
        )
        print("REFUSING TO SAVE. Graph on disk is unchanged.")
        store.close()
        return 1

    store.save()
    store.close()

    print(f"Graph saved to {GRAPH_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
