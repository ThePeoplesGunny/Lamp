"""Phase 2C-5 Step 1 — ingest KJV 1769 New Testament as a translation layer.

Source: scrollmapper/bible_databases KJV.json (public domain, 1769 Oxford edition).
Scope: NT only this phase. OT deferred to Phase 2C-6 pending Hebrew↔English
versification mapping (Psalms superscriptions, minor-prophet chapter breaks, etc.).

For each KJV NT verse:
  - If the matching verse node exists in the graph (e.g. verse:JHN.3.16),
    attach a TranslationText row keyed by (KJV-1769, verse_id).
  - If the verse node does NOT exist (~30 verses — Matt 17:21, 18:11, 23:14,
    Mark 7:16, etc., absent from SBLGNT critical text), CREATE a minimal
    Greek-language verse node with empty text_accented/text_plain so the
    verse slot exists. This is exegetically correct: KJV has these verses
    from the Byzantine tradition, and the empty Greek flags "no SBLGNT text
    for this verse — see translations for the reading." Byzantine/TR ingest
    later can populate the Greek text.

Usage:
    python scripts/seed_translations_kjv_nt.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from lamp.config import GRAPH_FILE, VERSES_DB_FILE  # noqa: E402
from lamp.graph.store import GraphStore  # noqa: E402
from lamp.models import Canon, TranslationText, Verse  # noqa: E402


KJV_SOURCE = REPO_ROOT / "backend" / "data" / "external" / "kjv_scrollmapper.json"

# KJV scrollmapper uses Roman-numeral prefixes and older book names.
# Map KJV's names to canonical Lamp 3-letter codes for the 27 NT books.
KJV_NT_NAME_TO_LAMP = {
    "Matthew": "MAT",
    "Mark": "MRK",
    "Luke": "LUK",
    "John": "JHN",
    "Acts": "ACT",
    "Romans": "ROM",
    "I Corinthians": "1CO",
    "II Corinthians": "2CO",
    "Galatians": "GAL",
    "Ephesians": "EPH",
    "Philippians": "PHP",
    "Colossians": "COL",
    "I Thessalonians": "1TH",
    "II Thessalonians": "2TH",
    "I Timothy": "1TI",
    "II Timothy": "2TI",
    "Titus": "TIT",
    "Philemon": "PHM",
    "Hebrews": "HEB",
    "James": "JAS",
    "I Peter": "1PE",
    "II Peter": "2PE",
    "I John": "1JN",
    "II John": "2JN",
    "III John": "3JN",
    "Jude": "JUD",
    "Revelation of John": "REV",
}

TRANSLATION_ID = "KJV-1769"
TRANSLATION_SOURCE = "scrollmapper/bible_databases@KJV.json (PD, 1769 Oxford ed.)"
TRANSLATION_TIER = 2  # Historic translation (public domain). CLAUDE.md's tier table
                      # defines tier 2 as exactly this and names the KJV 1769. This was
                      # 4 with the comment "lower than primary-source tier 1" — but the
                      # scale is not a generic ranking: tier 4 means "Speculative
                      # inference", which "cannot be presented as fact". That tagged all
                      # 31,104 KJV rows as speculation and printed "tier 4" on every
                      # verse page.


def _minimal_greek_verse(verse_id: str, book: str, chapter: int, verse: int, source: str) -> Verse:
    """Create a placeholder Greek verse node for KJV-only verses (e.g. Matt 17:21).

    Greek text layers remain empty — Byzantine/TR ingest later will fill them.
    """
    from lamp.models.verse import VerseWord  # local import to avoid top-level cycle cost
    _ = VerseWord  # unused directly; Verse.words is just []
    return Verse(
        id=verse_id,
        book=book,
        chapter=chapter,
        verse=verse,
        canon=Canon.NT,
        language="grc",
        text_canonical="",     # no Greek source for this slot yet
        text_accented="",
        text_plain="",
        words=[],
        source=source,
        source_tier=TRANSLATION_TIER,
        notes=[
            "Verse absent from SBLGNT critical text; present in KJV/Byzantine. "
            "Greek text will be populated when Byzantine/TR source is ingested."
        ],
    )


def main() -> int:
    if not KJV_SOURCE.exists():
        print(f"ERROR: {KJV_SOURCE} not found.")
        print("Download with:")
        print("  curl -sL -o backend/data/external/kjv_scrollmapper.json "
              "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/KJV.json")
        return 1

    print("=" * 72)
    print(" Lamp — KJV 1769 NT translation ingest (Phase 2C-5 Step 1)")
    print("=" * 72)
    print(f"Source: {KJV_SOURCE}")
    print(f"Translation id: {TRANSLATION_ID}")
    print()

    with open(KJV_SOURCE, encoding="utf-8") as f:
        kjv = json.load(f)

    store = GraphStore(graph_path=GRAPH_FILE, verse_db_path=VERSES_DB_FILE)
    store.load()
    pre_stats = store.stats()
    print(f"Pre-ingest: {pre_stats['verses']} verses, {pre_stats['edges']} edges")
    print()

    t_start = time.perf_counter()
    per_book_counts: dict[str, int] = {}
    created_verse_nodes: list[tuple[str, str]] = []  # (verse_id, book+c:v human ref)
    translations: list[TranslationText] = []

    # Slots this script created on an earlier run. They are REFRESHED, not skipped:
    # a slot written by a previous run keeps whatever metadata that run stamped on
    # it, so a change to TRANSLATION_TIER or to the note text never reaches the rows
    # already on disk. That is exactly what happened — correcting the tier from 4 to
    # 2 left 32 verse rows stale at 4, because the guard below was create-only.
    # Matching on TRANSLATION_SOURCE keeps this precise: only rows this script wrote
    # are rewritten, never a verse holding real Hebrew or Greek text.
    existing_slot_ids = store.verses.verse_ids_by_source(TRANSLATION_SOURCE)
    print(f"Existing KJV-only slots to refresh: {len(existing_slot_ids)}")
    print()

    print(f"{'Book':<6} {'Verses':>7} {'New slots':>10}  time")
    print("-" * 72)

    for book_idx, book_data in enumerate(kjv["books"]):
        if book_idx < 39:  # OT — skip this phase
            continue
        kjv_name = book_data["name"]
        if kjv_name not in KJV_NT_NAME_TO_LAMP:
            print(f"  ! unrecognized book {kjv_name!r}, skipping")
            continue
        lamp_code = KJV_NT_NAME_TO_LAMP[kjv_name]

        t0 = time.perf_counter()
        book_verse_count = 0
        book_new_slots: list[Verse] = []

        for chapter_data in book_data["chapters"]:
            chapter = chapter_data["chapter"]
            for verse_data in chapter_data["verses"]:
                verse_num = verse_data["verse"]
                text = verse_data["text"]
                verse_id = f"verse:{lamp_code}.{chapter}.{verse_num}"

                if verse_id not in store.G or verse_id in existing_slot_ids:
                    book_new_slots.append(_minimal_greek_verse(
                        verse_id=verse_id,
                        book=lamp_code,
                        chapter=chapter,
                        verse=verse_num,
                        source=TRANSLATION_SOURCE,
                    ))
                    if verse_id not in existing_slot_ids:
                        created_verse_nodes.append((verse_id, f"{kjv_name} {chapter}:{verse_num}"))

                translations.append(TranslationText(
                    translation=TRANSLATION_ID,
                    verse_id=verse_id,
                    text=text,
                    source=TRANSLATION_SOURCE,
                    source_tier=TRANSLATION_TIER,
                ))
                book_verse_count += 1

        if book_new_slots:
            store.add_verses(book_new_slots)
        per_book_counts[lamp_code] = book_verse_count

        t1 = time.perf_counter()
        print(f"{lamp_code:<6} {book_verse_count:>7} {len(book_new_slots):>10}  {t1-t0:.2f}s")

    inserted = store.verses.insert_translations(translations)
    t_total = time.perf_counter() - t_start

    print("-" * 72)
    total_verses = sum(per_book_counts.values())
    total_new = len(created_verse_nodes)
    print(f"{'TOTAL':<6} {total_verses:>7} {total_new:>10}  {t_total:.2f}s")
    print()
    print(f"Translation rows inserted: {inserted}")

    if created_verse_nodes:
        print(f"\nVerse slots created for SBLGNT-absent KJV verses ({len(created_verse_nodes)}):")
        for _, ref in created_verse_nodes:
            print(f"  {ref}")

    print("\nSaving graph...")
    t0 = time.perf_counter()
    store.save()
    print(f"  saved in {time.perf_counter()-t0:.2f}s")

    post_stats = store.stats()
    print(f"\nPost-ingest: {post_stats['verses']} verses, {post_stats['edges']} edges")
    print(f"  Δ verses: +{post_stats['verses'] - pre_stats['verses']}")

    # Spot check
    v = store.get_verse("verse:JHN.3.16")
    tr = store.verses.get_translations_for_verse("verse:JHN.3.16")
    print(f"\nSpot check — John 3:16 has {len(tr)} translation(s):")
    for t in tr:
        print(f"  [{t.translation}] {t.text[:90]}{'...' if len(t.text) > 90 else ''}")

    store.close()

    print("\n" + "=" * 72)
    print(f" RESULT: INGESTED {inserted} KJV NT verses across {len(per_book_counts)} books")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
