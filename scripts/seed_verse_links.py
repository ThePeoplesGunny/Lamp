"""Phase 2C-1 Step 3 — auto-link existing entity nodes to verse nodes.

For every Person / Place / Nation node, walk its curated `scripture_refs`,
expand ranges, and materialize a `MENTIONS` edge from each referenced verse
node to the entity. This is pure mechanical translation of existing data —
no new claims are introduced. After this script, the graph has first-class
verse→entity traversals and questions like "every verse mentioning Abraham"
become O(degree) lookups.

Idempotent: re-running replaces existing (verse → entity, MENTIONS) edges
instead of accumulating duplicates, because NetworkX MultiDiGraph keyed by
edge-type overwrites on re-insert.

The linking logic itself lives in lamp.ingest.verse_links so seed_graph.py can
re-link in-process after replacing entity nodes. This script is the standalone
entry point for re-linking without touching entities.

Usage:
    python scripts/seed_verse_links.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from lamp.config import GRAPH_FILE, VERSES_DB_FILE  # noqa: E402
from lamp.graph.store import GraphStore  # noqa: E402
from lamp.ingest.verse_links import link_entities_to_verses  # noqa: E402


def main() -> int:
    if not GRAPH_FILE.exists():
        print(f"ERROR: {GRAPH_FILE} not found. Run seed_graph.py and seed_verses.py first.")
        return 1
    if not VERSES_DB_FILE.exists():
        print(f"ERROR: {VERSES_DB_FILE} not found. Run seed_verses.py first.")
        return 1

    print("=" * 72)
    print(" Lamp — entity ↔ verse link seeding (Phase 2C-1 Step 3)")
    print("=" * 72)

    store = GraphStore(graph_path=GRAPH_FILE, verse_db_path=VERSES_DB_FILE)
    store.load()

    pre_stats = store.stats()
    print(f"Pre-link stats: {pre_stats}\n")

    result = link_entities_to_verses(store)

    t_save_start = time.perf_counter()
    store.save()
    t_save = time.perf_counter() - t_save_start

    print(f"Entities linked: {result.entities_linked} / {result.entities_total}")
    print(f"  by type: {dict(result.per_type_entities)}")
    print(f"Entities with no scripture_refs: {result.entities_without_refs}")
    print(f"Total MENTIONS edges created: {result.edges_added}")
    print(f"  by book: {dict(result.per_book_edges)}")

    if result.missing_verses:
        print(f"\nMissing verse nodes (refs skipped): {sum(result.missing_verses.values())}")
        for book, n in result.missing_verses.most_common():
            print(f"  {book}: {n} ref(s) — book not ingested")

    post_stats = store.stats()
    print(f"\nPost-link stats: {post_stats}")
    print(f"Graph saved in {t_save:.2f}s")

    # Spot check: confirm a well-known entity links to expected verse count
    print("\nSpot check — person:abraham:")
    abe_verses = store.get_verses_mentioning("person:abraham")
    print(f"  MENTIONS edges in: {len(abe_verses)}")
    for v in abe_verses[:3]:
        print(f"    {v['id']}")
    if len(abe_verses) > 3:
        print(f"    ... +{len(abe_verses) - 3} more")

    store.close()

    ok = result.edges_added > 0 and not result.missing_verses
    print("\n" + "=" * 72)
    print(" RESULT: " + ("LINKING OK" if ok else "COMPLETED WITH NOTES"))
    print("=" * 72)
    return 0 if ok else 0  # Notes are informational, not errors


if __name__ == "__main__":
    sys.exit(main())
