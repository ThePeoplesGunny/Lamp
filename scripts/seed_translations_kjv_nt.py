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
from lamp.models import Canon, TranslationText, VerseRef  # noqa: E402


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
TRANSLATION_TIER = 1  # THE BASE TEXT. Tier 1 is the canonical layer. CLAUDE.md's table
                      # named the KJV 1769 at tier 2 while this project treated the
                      # original languages as canonical. The 2026-09-07 base-text
                      # decision inverted that: the KJV 1769 IS the text this project
                      # is about, so it holds tier 1 and OSHB/MorphGNT moved to tier 2
                      # as supporting witnesses. (Before that it was briefly tier 2,
                      # and before THAT tier 4 — "speculative inference" — which was
                      # simply a misreading of the scale as a generic ranking.)


def _kjv_only_ref(verse_id: str, book: str, chapter: int, verse: int) -> VerseRef:
    """Identity for a verse present in the KJV but absent from the SBLGNT.

    This used to build a whole fake Greek verse — empty text layers, no words,
    the KJV file as its `source` — because `translations` hung off `verses` and
    the KJV text had to have a parent row. After the 2026-09-07 identity/witness
    split it does not: the verse gets an identity and a base text, and simply has
    no original-language witness, which is the truth about it.
    """
    return VerseRef(
        id=verse_id,
        book=book,
        chapter=chapter,
        verse=verse,
        canon=Canon.NT,
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
    kjv_addresses: dict[str, tuple[str, int, int]] = {}

    # Slots this script created on an earlier run. They are REFRESHED, not skipped:
    # a slot written by a previous run keeps whatever metadata that run stamped on
    # it, so a change to TRANSLATION_TIER or to the note text never reaches the rows
    # already on disk. That is exactly what happened — correcting the tier from 4 to
    # 2 left 32 verse rows stale at 4, because the guard below was create-only.
    # Matching on TRANSLATION_SOURCE keeps this precise: only rows this script wrote
    # are rewritten, never a verse holding real Hebrew or Greek text.
    existing_slot_ids = store.verses.verse_ids_without_witness()
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
        book_new_slots: list[VerseRef] = []

        for chapter_data in book_data["chapters"]:
            chapter = chapter_data["chapter"]
            for verse_data in chapter_data["verses"]:
                verse_num = verse_data["verse"]
                text = verse_data["text"]
                verse_id = f"verse:{lamp_code}.{chapter}.{verse_num}"

                if verse_id not in store.G or verse_id in existing_slot_ids:
                    book_new_slots.append(_kjv_only_ref(
                        verse_id=verse_id,
                        book=lamp_code,
                        chapter=chapter,
                        verse=verse_num,
                    ))
                    if verse_id not in existing_slot_ids:
                        created_verse_nodes.append((verse_id, f"{kjv_name} {chapter}:{verse_num}"))

                # KJV and SBLGNT share NT versification, so the base-text address
                # is the verse's own. Written explicitly rather than left NULL so
                # no query needs a fallback for the NT half of the corpus.
                kjv_addresses[verse_id] = (lamp_code, chapter, verse_num)

                translations.append(TranslationText(
                    translation=TRANSLATION_ID,
                    verse_id=verse_id,
                    text=text,
                    source=TRANSLATION_SOURCE,
                    source_tier=TRANSLATION_TIER,
                ))
                book_verse_count += 1

        if book_new_slots:
            store.add_verse_refs(book_new_slots)
        per_book_counts[lamp_code] = book_verse_count

        t1 = time.perf_counter()
        print(f"{lamp_code:<6} {book_verse_count:>7} {len(book_new_slots):>10}  {t1-t0:.2f}s")

    store.verses.clear_kjv_addresses("nt")
    addressed = store.verses.set_kjv_addresses(kjv_addresses)
    print(f"KJV addresses written for {addressed} NT verse(s)")

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
