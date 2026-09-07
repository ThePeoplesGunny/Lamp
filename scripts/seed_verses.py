"""Phase 2C-1 Step 2d — full OSHB Hebrew OT ingest.

Walks all 39 OSHB wlc/*.xml books, parses each, and populates both:
  - NetworkX graph (verse nodes with minimal metadata)
  - SQLite verse store (three-layer text + per-word morphology)

Loads the existing graph first so person/place/nation nodes are preserved;
verse nodes are added on top.

Usage:
    python scripts/seed_verses.py
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
from lamp.ingest.oshb import parse_book  # noqa: E402
from lamp.models.book_codes import LAMP_TO_OSIS, OSIS_TO_LAMP  # noqa: E402


MORPHHB_DIR = REPO_ROOT / "backend" / "data" / "external" / "morphhb" / "wlc"

# Book ingest order: Tanakh canonical order (Torah → Nevi'im → Ketuvim).
# Protestant order (Gen → Mal) also works; going Tanakh-first respects the source tradition.
TANAKH_ORDER = [
    # Torah
    "GEN", "EXO", "LEV", "NUM", "DEU",
    # Nevi'im Rishonim (Former Prophets)
    "JOS", "JDG", "1SA", "2SA", "1KI", "2KI",
    # Nevi'im Aharonim (Latter Prophets)
    "ISA", "JER", "EZK",
    # The Twelve
    "HOS", "JOL", "AMO", "OBA", "JON", "MIC",
    "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
    # Ketuvim
    "PSA", "PRO", "JOB",
    "SNG", "RUT", "LAM", "ECC", "EST",
    "DAN", "EZR", "NEH", "1CH", "2CH",
]


def main() -> int:
    if not MORPHHB_DIR.exists():
        print(f"ERROR: {MORPHHB_DIR} not found. Clone OSHB first.")
        return 1

    print("=" * 72)
    print(" Lamp — OSHB Hebrew OT ingest (Phase 2C-1 Step 2d)")
    print("=" * 72)
    print(f"Source:       {MORPHHB_DIR}")
    print(f"Graph:        {GRAPH_FILE}")
    print(f"Verse DB:     {VERSES_DB_FILE}")
    print(f"Book order:   Tanakh ({len(TANAKH_ORDER)} books)")
    print()

    store = GraphStore(graph_path=GRAPH_FILE, verse_db_path=VERSES_DB_FILE)
    store.load()

    pre_stats = store.stats()
    print(f"Pre-ingest graph: {pre_stats}\n")

    # Sanity check: every expected Lamp book must have an OSIS XML file
    missing = []
    for lamp_code in TANAKH_ORDER:
        osis = LAMP_TO_OSIS[lamp_code]
        xml_path = MORPHHB_DIR / f"{osis}.xml"
        if not xml_path.exists():
            missing.append((lamp_code, xml_path))
    if missing:
        print("ERROR: missing OSHB files:")
        for code, path in missing:
            print(f"  {code}: {path}")
        return 1

    print(f"{'Book':<6} {'Verses':>7} {'Words':>7} {'K/Q':>4} {'Par':>4} {'Note':>4} {'Warn':>4}  time")
    print("-" * 72)

    total_verses = 0
    total_words = 0
    total_kq = 0
    total_parashah = 0
    total_notes = 0
    total_warnings = 0
    per_book: dict[str, int] = {}
    t_start = time.perf_counter()

    for lamp_code in TANAKH_ORDER:
        osis = LAMP_TO_OSIS[lamp_code]
        xml_path = MORPHHB_DIR / f"{osis}.xml"

        t0 = time.perf_counter()
        verses, warnings = parse_book(xml_path)
        store.add_verses(verses)
        t1 = time.perf_counter()

        n_verses = len(verses)
        n_words = sum(len(v.words) for v in verses)
        n_kq = sum(1 for v in verses for w in v.words if w.text_ketiv is not None)
        n_par = sum(1 for v in verses if v.parashah_marker is not None)
        n_notes = sum(len(v.notes) for v in verses)

        total_verses += n_verses
        total_words += n_words
        total_kq += n_kq
        total_parashah += n_par
        total_notes += n_notes
        total_warnings += len(warnings)
        per_book[lamp_code] = n_verses

        print(
            f"{lamp_code:<6} {n_verses:>7} {n_words:>7} {n_kq:>4} {n_par:>4} "
            f"{n_notes:>4} {len(warnings):>4}  {t1-t0:.2f}s"
        )
        for w in warnings[:3]:
            print(f"       ! {w}")

    t_parse = time.perf_counter() - t_start

    print("-" * 72)
    print(f"{'TOTAL':<6} {total_verses:>7} {total_words:>7} {total_kq:>4} {total_parashah:>4} "
          f"{total_notes:>4} {total_warnings:>4}  {t_parse:.2f}s")
    print()

    # Save graph (SQLite already persisted per-batch)
    print("Saving graph...")
    t0 = time.perf_counter()
    store.save()
    t_save = time.perf_counter() - t0
    print(f"  graph saved in {t_save:.2f}s")

    # Verify SQLite counts match what we parsed. Scope the comparison to the
    # tanakh: this script ingests Hebrew OT only, while the database also holds
    # the Greek NT and the KJV-only slots. Comparing against a whole-table count
    # made this check unsatisfiable the moment Phase 2C-2 landed — 23,213 parsed
    # against 31,172 stored — so every successful run reported ISSUES DETECTED
    # and returned exit code 1.
    sqlite_verse_count = store.verses.count_verses(canon="tanakh")
    sqlite_total_count = store.verses.count_verses()
    sqlite_word_count = store.verses.count_words()
    print(f"  SQLite tanakh verses: {sqlite_verse_count}  (parsed this run: {total_verses})")
    print(f"  SQLite verses, all canons: {sqlite_total_count}")
    print(f"  SQLite words:  {sqlite_word_count}")

    post_stats = store.stats()
    print(f"\nPost-ingest graph: {post_stats}")

    # Reference totals for WLC/OSHB (Hebrew versification — may differ slightly
    # from Protestant in Psalms/Minor Prophets due to superscription numbering).
    # Published WLC reference: 23,213 verses total (plus-or-minus small tradition variance).
    print("\nReference check:")
    print(f"  Published WLC Tanakh verse total: ~23,213 (Hebrew versification)")
    print(f"  Ingested: {total_verses}")
    diff = total_verses - 23213
    if abs(diff) <= 50:
        print(f"  Delta: {diff:+d} — within expected range (versification variance)")
    else:
        print(f"  Delta: {diff:+d} — LARGER THAN EXPECTED; investigate")

    store.close()

    ok = total_warnings == 0 and sqlite_verse_count == total_verses
    print("\n" + "=" * 72)
    print(" RESULT: " + ("INGEST OK" if ok else "ISSUES DETECTED"))
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
