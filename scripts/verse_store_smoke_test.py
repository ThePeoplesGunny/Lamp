"""Smoke test — verify Phase 2C-1 Step 2c wiring end-to-end.

Parses Genesis via OSHB ingest, pushes verses into GraphStore (in-memory + in-memory SQLite),
round-trips one verse back, and cross-checks integrity vs. the original parse output.

Usage:
    python scripts/verse_store_smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from lamp.graph.store import GraphStore  # noqa: E402
from lamp.ingest.oshb import parse_book  # noqa: E402
from lamp.models import Edge, EdgeType, Person  # noqa: E402


MORPHHB_GEN = REPO_ROOT / "backend" / "data" / "external" / "morphhb" / "wlc" / "Gen.xml"


def main() -> int:
    print("=" * 70)
    print("Phase 2C-1 Step 2c — verse_store smoke test")
    print("=" * 70)

    # 1. In-memory GraphStore + VerseStore
    store = GraphStore(graph_path=None, verse_db_path=None)
    store.load()
    print(f"\n[1] GraphStore initialized (in-memory graph + in-memory SQLite)")

    # 2. Parse Genesis
    print(f"\n[2] Parsing {MORPHHB_GEN.name}...")
    verses, warnings = parse_book(MORPHHB_GEN)
    print(f"    {len(verses)} verses parsed, {len(warnings)} warnings")
    if warnings:
        for w in warnings[:5]:
            print(f"      ! {w}")

    # 3. Push into GraphStore (graph nodes + SQLite)
    print(f"\n[3] Adding to GraphStore...")
    count = store.add_verses(verses)
    print(f"    {count} verses stored")
    print(f"    SQLite verses: {store.verses.count_verses()}")
    print(f"    SQLite words:  {store.verses.count_words()}")

    # 4. Round-trip one verse
    print(f"\n[4] Round-trip check — verse:GEN.1.1")
    original = verses[0]
    fetched = store.get_verse("verse:GEN.1.1")
    assert fetched is not None, "get_verse returned None"
    checks = [
        ("id", original.id == fetched.id),
        ("book", original.book == fetched.book),
        ("chapter", original.chapter == fetched.chapter),
        ("verse", original.verse == fetched.verse),
        ("canon", original.canon == fetched.canon),
        ("text_cantillated", original.text_cantillated == fetched.text_cantillated),
        ("text_pointed", original.text_pointed == fetched.text_pointed),
        ("text_consonantal", original.text_consonantal == fetched.text_consonantal),
        ("word count", len(original.words) == len(fetched.words)),
        ("word 1 lemma", original.words[0].lemma == fetched.words[0].lemma),
        ("word 1 morph", original.words[0].morph_code == fetched.words[0].morph_code),
        ("word 1 strongs", original.words[0].strongs == fetched.words[0].strongs),
        ("word 1 oshb_id", original.words[0].oshb_word_id == fetched.words[0].oshb_word_id),
    ]
    all_ok = True
    for name, ok in checks:
        status = "✓" if ok else "✗ MISMATCH"
        print(f"    {status} {name}")
        if not ok:
            all_ok = False

    # 5. Round-trip a ketiv/qere verse
    print(f"\n[5] Round-trip check — ketiv/qere preservation (GEN.8.17)")
    kq_fetched = store.get_verse("verse:GEN.8.17")
    assert kq_fetched is not None
    kq_words = [w for w in kq_fetched.words if w.text_ketiv is not None]
    if kq_words:
        for w in kq_words:
            print(f"    ketiv={w.text_ketiv!r} qere={w.text_qere!r} at position {w.position}")
    else:
        print("    ✗ No ketiv/qere words found — data lost in round-trip!")
        all_ok = False

    # 6. Parashah marker round-trip
    print(f"\n[6] Parashah marker round-trip — GEN.1.5")
    p_fetched = store.get_verse("verse:GEN.1.5")
    assert p_fetched is not None
    print(f"    parashah_marker = {p_fetched.parashah_marker!r} (expected 'pe')")
    if p_fetched.parashah_marker != "pe":
        all_ok = False

    # 7. MENTIONS edge traversal
    print(f"\n[7] MENTIONS edge traversal — add test person + edge, query both directions")
    test_person = Person(
        id="person:_smoke_adam",
        name_english="Smoke Adam",
        sex="male",
    )
    store.add_person(test_person)
    store.add_edge(Edge(
        source="verse:GEN.1.1",
        target="person:_smoke_adam",
        type=EdgeType.MENTIONS,
    ))
    fwd = store.get_mentions("verse:GEN.1.1")
    rev = store.get_verses_mentioning("person:_smoke_adam")
    print(f"    outgoing mentions from GEN.1.1:  {[n['id'] for n in fwd]}")
    print(f"    incoming mentions for Smoke Adam: {[v['id'] for v in rev]}")
    edge_ok = (
        len(fwd) == 1 and fwd[0]["id"] == "person:_smoke_adam"
        and len(rev) == 1 and rev[0]["id"] == "verse:GEN.1.1"
    )
    if not edge_ok:
        all_ok = False
        print("    ✗ edge traversal FAILED")
    else:
        print("    ✓ edges traverse correctly in both directions")

    # 8. Stats
    print(f"\n[8] GraphStore.stats():")
    for k, v in store.stats().items():
        print(f"    {k}: {v}")

    store.close()

    print("\n" + "=" * 70)
    print("RESULT: " + ("ALL CHECKS PASSED" if all_ok else "FAILURES DETECTED"))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
