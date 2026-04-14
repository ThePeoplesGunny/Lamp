"""Phase 2C-2 Step 4 — full MorphGNT / SBLGNT Greek NT ingest.

Walks all 27 MorphGNT book files and populates both:
  - NetworkX graph (verse nodes with minimal metadata)
  - SQLite verse store (accented + plain Greek text + per-word morphology)

Loads the existing graph first so entity and Hebrew-verse nodes are preserved;
Greek verse nodes are added alongside.

Note: SBLGNT is a modern critical text, so it legitimately OMITS verses that
TR/KJV include (e.g. Matt 17:21, 18:11, 23:14). The total verse count here
will be lower than the KJV NT total of 7,957 — this is correct, not data loss.
Byzantine/TR ingest (if later added) will surface those verses under the same
verse IDs and make the textual divergence analyzable.

Usage:
    python scripts/seed_verses_nt.py
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
from lamp.ingest.morphgnt import MORPHGNT_NUM_TO_OSIS, parse_book  # noqa: E402
from lamp.models.book_codes import osis_to_lamp  # noqa: E402


MORPHGNT_DIR = REPO_ROOT / "backend" / "data" / "external" / "morphgnt"

# MorphGNT filename convention: {sort_prefix}-{short_code}-morphgnt.txt
# Sort prefixes 61-87 for the 27 NT books in canonical Protestant order.
MORPHGNT_FILENAMES = {
    "01": "61-Mt-morphgnt.txt",  "02": "62-Mk-morphgnt.txt",
    "03": "63-Lk-morphgnt.txt",  "04": "64-Jn-morphgnt.txt",
    "05": "65-Ac-morphgnt.txt",  "06": "66-Ro-morphgnt.txt",
    "07": "67-1Co-morphgnt.txt", "08": "68-2Co-morphgnt.txt",
    "09": "69-Ga-morphgnt.txt",  "10": "70-Eph-morphgnt.txt",
    "11": "71-Php-morphgnt.txt", "12": "72-Col-morphgnt.txt",
    "13": "73-1Th-morphgnt.txt", "14": "74-2Th-morphgnt.txt",
    "15": "75-1Ti-morphgnt.txt", "16": "76-2Ti-morphgnt.txt",
    "17": "77-Tit-morphgnt.txt", "18": "78-Phm-morphgnt.txt",
    "19": "79-Heb-morphgnt.txt", "20": "80-Jas-morphgnt.txt",
    "21": "81-1Pe-morphgnt.txt", "22": "82-2Pe-morphgnt.txt",
    "23": "83-1Jn-morphgnt.txt", "24": "84-2Jn-morphgnt.txt",
    "25": "85-3Jn-morphgnt.txt", "26": "86-Jud-morphgnt.txt",
    "27": "87-Re-morphgnt.txt",
}


def main() -> int:
    if not MORPHGNT_DIR.exists():
        print(f"ERROR: {MORPHGNT_DIR} not found. Clone MorphGNT first.")
        return 1

    print("=" * 72)
    print(" Lamp — MorphGNT / SBLGNT Greek NT ingest (Phase 2C-2 Step 4)")
    print("=" * 72)
    print(f"Source:       {MORPHGNT_DIR}")
    print(f"Graph:        {GRAPH_FILE}")
    print(f"Verse DB:     {VERSES_DB_FILE}")
    print(f"Book order:   NT canonical (27 books, Matt → Rev)")
    print()

    store = GraphStore(graph_path=GRAPH_FILE, verse_db_path=VERSES_DB_FILE)
    store.load()

    pre_stats = store.stats()
    print(f"Pre-ingest graph: {pre_stats}\n")

    # Sanity — every expected file is present
    missing = [
        (num, MORPHGNT_DIR / fn)
        for num, fn in MORPHGNT_FILENAMES.items()
        if not (MORPHGNT_DIR / fn).exists()
    ]
    if missing:
        print("ERROR: missing MorphGNT files:")
        for num, path in missing:
            print(f"  {num}: {path}")
        return 1

    print(f"{'Book':<6} {'Verses':>7} {'Words':>7} {'Warn':>4}  time")
    print("-" * 72)

    total_verses = 0
    total_words = 0
    total_warnings = 0
    per_book: dict[str, int] = {}
    t_start = time.perf_counter()

    # Walk in canonical NT order (Matt → Rev, numbers 01-27)
    for num in sorted(MORPHGNT_FILENAMES.keys()):
        osis = MORPHGNT_NUM_TO_OSIS[num]
        lamp_code = osis_to_lamp(osis)
        filename = MORPHGNT_FILENAMES[num]
        path = MORPHGNT_DIR / filename

        t0 = time.perf_counter()
        verses, warnings = parse_book(path)
        store.add_verses(verses)
        t1 = time.perf_counter()

        n_verses = len(verses)
        n_words = sum(len(v.words) for v in verses)
        total_verses += n_verses
        total_words += n_words
        total_warnings += len(warnings)
        per_book[lamp_code] = n_verses

        print(f"{lamp_code:<6} {n_verses:>7} {n_words:>7} {len(warnings):>4}  {t1-t0:.2f}s")
        for w in warnings[:3]:
            print(f"       ! {w}")

    t_parse = time.perf_counter() - t_start

    print("-" * 72)
    print(f"{'TOTAL':<6} {total_verses:>7} {total_words:>7} {total_warnings:>4}  {t_parse:.2f}s")
    print()

    print("Saving graph...")
    t0 = time.perf_counter()
    store.save()
    t_save = time.perf_counter() - t0
    print(f"  graph saved in {t_save:.2f}s")

    post_stats = store.stats()
    print(f"\nPost-ingest graph: {post_stats}")

    # SBLGNT reference counts — the 27 NT books per SBLGNT critical edition.
    # These differ from KJV/TR (which are higher) because SBLGNT omits verses
    # absent from earliest manuscripts (Matt 17:21, 18:11, 23:14, Mark 7:16,
    # 9:44, 9:46, 11:26, 15:28, Luke 17:36, 23:17, John 5:4, Acts 8:37, 15:34,
    # 24:7, 28:29, Rom 16:24 etc.).
    print("\nReference note:")
    print(f"  Ingested SBLGNT verse total: {total_verses}")
    print(f"  KJV/TR NT verse total: 7,957 (higher due to Byzantine-only verses)")
    print(f"  Difference is textual-critical, not data loss.")

    # Spot check
    print("\nSpot check — verse:JHN.3.16:")
    v = store.get_verse("verse:JHN.3.16")
    if v is None:
        print("  ! Not found")
    else:
        print(f"  canonical: {v.text_canonical[:120]}...")
        print(f"  words: {len(v.words)}")

    store.close()

    ok = total_warnings == 0
    print("\n" + "=" * 72)
    print(" RESULT: " + ("INGEST OK" if ok else "ISSUES DETECTED"))
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
