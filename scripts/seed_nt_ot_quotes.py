"""Phase 2D-3 — seed NT→OT QUOTES edges.

Reads backend/data/seed/nt_ot_quotes.json (curated list of ~100 well-attested
NT citations of OT) and materializes QUOTES edges (NT verse → OT verse) in
the graph. Notes on each entry are persisted to the edge's `notes` field
(captures LXX-vs-MT, typological readings, attribution puzzles).

Idempotent: MultiDiGraph edge keyed by edge-type, so re-running overwrites
(source, target, QUOTES) rather than accumulating duplicates.

Usage:
    python scripts/seed_nt_ot_quotes.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from lamp.config import GRAPH_FILE, SEED_DIR, VERSES_DB_FILE  # noqa: E402
from lamp.graph.store import GraphStore  # noqa: E402
from lamp.models import Edge, EdgeType  # noqa: E402


QUOTES_FILE = SEED_DIR / "nt_ot_quotes.json"


def verse_id(ref: dict) -> str:
    return f"verse:{ref['book']}.{ref['chapter']}.{ref['verse']}"


def main() -> int:
    if not QUOTES_FILE.exists():
        print(f"ERROR: {QUOTES_FILE} not found.")
        return 1
    if not GRAPH_FILE.exists():
        print(f"ERROR: {GRAPH_FILE} not found. Run seed_graph.py + seed_verses.py first.")
        return 1

    print("=" * 72)
    print(" Lamp — NT→OT QUOTES edge seeding (Phase 2D-3)")
    print("=" * 72)

    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    quotes = data.get("quotes", [])
    print(f"Seed entries: {len(quotes)}")

    store = GraphStore(graph_path=GRAPH_FILE, verse_db_path=VERSES_DB_FILE)
    store.load()
    pre_stats = store.stats()
    print(f"Pre-seed stats: {pre_stats}")

    # Clear pre-existing QUOTES edges so re-runs after target-edits don't leave
    # zombie edges pointing to old targets.
    to_remove = [
        (u, v, k) for u, v, k, d in store.G.edges(keys=True, data=True)
        if d.get("type") == EdgeType.QUOTES
    ]
    for u, v, k in to_remove:
        store.G.remove_edge(u, v, key=k)
    if to_remove:
        print(f"Cleared {len(to_remove)} pre-existing QUOTES edges.\n")
    else:
        print()

    edges_added = 0
    missing: list[tuple[str, str]] = []
    per_nt_book: Counter[str] = Counter()
    per_ot_book: Counter[str] = Counter()

    for q in quotes:
        nt_id = verse_id(q["nt"])
        ot_id = verse_id(q["ot"])
        if nt_id not in store.G:
            missing.append((nt_id, "NT source missing"))
            continue
        if ot_id not in store.G:
            missing.append((ot_id, "OT target missing"))
            continue
        store.add_edge(Edge(
            source=nt_id,
            target=ot_id,
            type=EdgeType.QUOTES,
            notes=q.get("notes"),
        ))
        edges_added += 1
        per_nt_book[q["nt"]["book"]] += 1
        per_ot_book[q["ot"]["book"]] += 1

    store.save()

    print(f"QUOTES edges created: {edges_added}")
    print(f"  NT source breakdown: {dict(sorted(per_nt_book.items()))}")
    print(f"  OT target breakdown: {dict(sorted(per_ot_book.items()))}")

    if missing:
        print(f"\nMissing verse nodes ({len(missing)}):")
        for vid, reason in missing[:20]:
            print(f"  {vid} — {reason}")

    post_stats = store.stats()
    print(f"\nPost-seed stats: {post_stats}")

    # Spot-check: what does Matt 1:23 quote? what quotes Isa 53:1?
    print("\nSpot check — Matt 1:23 out-edges (quotes):")
    for _, tgt, edata in store.G.out_edges("verse:MAT.1.23", data=True):
        if edata.get("type") == EdgeType.QUOTES:
            print(f"  → {tgt}: {edata.get('notes','')[:80]}")

    print("\nSpot check — Isa 53:1 in-edges (quoted by):")
    for src, _, edata in store.G.in_edges("verse:ISA.53.1", data=True):
        if edata.get("type") == EdgeType.QUOTES:
            print(f"  ← {src}: {edata.get('notes','')[:80]}")

    store.close()

    ok = edges_added > 0 and not missing
    print("\n" + "=" * 72)
    print(" RESULT: " + ("QUOTES SEEDING OK" if ok else "COMPLETED WITH NOTES"))
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
