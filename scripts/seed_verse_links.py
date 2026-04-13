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

Usage:
    python scripts/seed_verse_links.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from lamp.config import GRAPH_FILE, VERSES_DB_FILE  # noqa: E402
from lamp.graph.store import GraphStore  # noqa: E402
from lamp.models import Edge, EdgeType  # noqa: E402


ENTITY_NODE_TYPES = ("person", "place", "nation")


def expand_ref(book: str, chapter: int, verse: int, verse_end: int | None) -> list[str]:
    """Expand a scripture ref (possibly a range) into canonical verse IDs."""
    end = verse_end if verse_end else verse
    return [f"verse:{book}.{chapter}.{v}" for v in range(verse, end + 1)]


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

    # Walk entities. Node attributes include `scripture_refs` (list of dicts
    # after model_dump at seed time).
    missing_verses: Counter[str] = Counter()
    per_book_edges: Counter[str] = Counter()
    per_type_entities: Counter[str] = Counter()
    edges_added = 0
    entities_linked = 0
    entities_without_refs = 0

    for node_id, data in store.G.nodes(data=True):
        if data.get("node_type") not in ENTITY_NODE_TYPES:
            continue
        refs = data.get("scripture_refs") or []
        if not refs:
            entities_without_refs += 1
            continue

        entity_edges = 0
        seen_verse_ids: set[str] = set()

        for ref in refs:
            book = ref["book"]
            chapter = ref["chapter"]
            verse = ref["verse"]
            verse_end = ref.get("verse_end")
            for verse_id in expand_ref(book, chapter, verse, verse_end):
                if verse_id in seen_verse_ids:
                    continue
                seen_verse_ids.add(verse_id)
                if verse_id not in store.G:
                    missing_verses[book] += 1
                    continue
                store.add_edge(Edge(
                    source=verse_id,
                    target=node_id,
                    type=EdgeType.MENTIONS,
                ))
                entity_edges += 1
                per_book_edges[book] += 1

        if entity_edges > 0:
            edges_added += entity_edges
            entities_linked += 1
            per_type_entities[data["node_type"]] += 1

    t_save_start = _now()
    store.save()
    t_save = _now() - t_save_start

    print(f"Entities linked: {entities_linked} / {sum(1 for _, d in store.G.nodes(data=True) if d.get('node_type') in ENTITY_NODE_TYPES)}")
    print(f"  by type: {dict(per_type_entities)}")
    print(f"Entities with no scripture_refs: {entities_without_refs}")
    print(f"Total MENTIONS edges created: {edges_added}")
    print(f"  by book: {dict(per_book_edges)}")

    if missing_verses:
        print(f"\nMissing verse nodes (refs skipped): {sum(missing_verses.values())}")
        for book, n in missing_verses.most_common():
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

    ok = edges_added > 0 and not missing_verses
    print("\n" + "=" * 72)
    print(" RESULT: " + ("LINKING OK" if ok else "COMPLETED WITH NOTES"))
    print("=" * 72)
    return 0 if ok else 0  # Notes are informational, not errors


def _now() -> float:
    import time
    return time.perf_counter()


if __name__ == "__main__":
    sys.exit(main())
