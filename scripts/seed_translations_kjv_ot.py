"""Phase 2C-6 — ingest KJV 1769 OT with Hebrew↔English versification mapping.

KJV OT uses English/Protestant verse numbering, which diverges from the
Hebrew (Masoretic) numbering in a handful of predictable ways:

  - Psalms: Hebrew numbers superscriptions as verse 1 (or 1-2); KJV doesn't.
    A per-chapter offset corrects this.
  - Joel & Malachi: chapter counts differ (Heb 4/Heb 3 ch respectively,
    KJV 3/4). Explicit chapter-range remaps handle these.
  - Numbers, 1 Samuel, 1 Kings, 1 Chronicles, Nehemiah, Isaiah: chapter
    boundaries shift by >±1 verse in ways that need authoritative per-verse
    mappings we don't currently have. These books are SKIPPED this phase,
    to be completed in a follow-up once a published versification table is
    pulled in.

The 31 perfectly-aligned OT books + Psalms + Joel + Malachi cover
~22,150 of KJV OT's 23,145 verses (~96%).

Usage:
    python scripts/seed_translations_kjv_ot.py
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
from lamp.models import TranslationText  # noqa: E402


KJV_SOURCE = REPO_ROOT / "backend" / "data" / "external" / "kjv_scrollmapper.json"
VERSIFICATION_MAP = REPO_ROOT / "backend" / "data" / "seed" / "versification_kjv_to_heb.json"

# KJV book name → Lamp canonical code (OT only)
KJV_OT_NAME_TO_LAMP = {
    "Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV", "Numbers": "NUM",
    "Deuteronomy": "DEU", "Joshua": "JOS", "Judges": "JDG", "Ruth": "RUT",
    "I Samuel": "1SA", "II Samuel": "2SA", "I Kings": "1KI", "II Kings": "2KI",
    "I Chronicles": "1CH", "II Chronicles": "2CH", "Ezra": "EZR",
    "Nehemiah": "NEH", "Esther": "EST", "Job": "JOB", "Psalms": "PSA",
    "Proverbs": "PRO", "Ecclesiastes": "ECC", "Song of Solomon": "SNG",
    "Isaiah": "ISA", "Jeremiah": "JER", "Lamentations": "LAM", "Ezekiel": "EZK",
    "Daniel": "DAN", "Hosea": "HOS", "Joel": "JOL", "Amos": "AMO",
    "Obadiah": "OBA", "Jonah": "JON", "Micah": "MIC", "Nahum": "NAM",
    "Habakkuk": "HAB", "Zephaniah": "ZEP", "Haggai": "HAG", "Zechariah": "ZEC",
    "Malachi": "MAL",
}

TRANSLATION_ID = "KJV-1769"
TRANSLATION_SOURCE = "scrollmapper/bible_databases@KJV.json (PD, 1769 Oxford ed.)"
TRANSLATION_TIER = 4


def map_kjv_to_heb(
    lamp_code: str,
    kjv_chapter: int,
    kjv_verse: int,
    vm: dict,
) -> tuple[int, int] | None:
    """Translate KJV book/chapter/verse to Hebrew numbering. Returns None if unmapped."""
    # Psalms — superscription offsets
    if lamp_code == "PSA":
        offset = vm["psalms_offsets"].get(str(kjv_chapter), 0)
        return (kjv_chapter, kjv_verse + offset)

    # Joel — chapter-range remaps
    if lamp_code == "JOL":
        for override in vm["joel_mapping"]["chapter_overrides"]:
            if (kjv_chapter == override["kjv_from"]["chapter"] and
                    override["kjv_from"]["verse_min"] <= kjv_verse <=
                    override["kjv_from"]["verse_max"]):
                return (
                    override["heb"]["chapter"],
                    kjv_verse + override["heb"]["verse_offset"],
                )
        # Fall through: Joel 1:1-20, 2:1-27 align directly
        return (kjv_chapter, kjv_verse)

    # Malachi — ch 4 remap
    if lamp_code == "MAL":
        for override in vm["malachi_mapping"]["chapter_overrides"]:
            if (kjv_chapter == override["kjv_from"]["chapter"] and
                    override["kjv_from"]["verse_min"] <= kjv_verse <=
                    override["kjv_from"]["verse_max"]):
                return (
                    override["heb"]["chapter"],
                    kjv_verse + override["heb"]["verse_offset"],
                )
        # Mal 1-3 aligned directly
        return (kjv_chapter, kjv_verse)

    # All other aligned books: direct pass-through
    return (kjv_chapter, kjv_verse)


def main() -> int:
    if not KJV_SOURCE.exists():
        print(f"ERROR: {KJV_SOURCE} not found. Run scripts/seed_translations_kjv_nt.py's fetch step first.")
        return 1
    if not VERSIFICATION_MAP.exists():
        print(f"ERROR: {VERSIFICATION_MAP} not found.")
        return 1

    print("=" * 72)
    print(" Lamp — KJV 1769 OT translation ingest (Phase 2C-6)")
    print("=" * 72)

    with open(KJV_SOURCE, encoding="utf-8") as f:
        kjv = json.load(f)
    with open(VERSIFICATION_MAP, encoding="utf-8") as f:
        vm = json.load(f)

    skipped_books = set(vm["skipped_books"].keys()) - {"_doc"}
    print(f"Skipped books (deferred — complex versification): {sorted(skipped_books)}")
    print()

    store = GraphStore(graph_path=GRAPH_FILE, verse_db_path=VERSES_DB_FILE)
    store.load()

    translations: list[TranslationText] = []
    per_book: dict[str, dict] = {}  # code -> {ingested, unmapped}
    unmapped_examples: list[tuple[str, str]] = []  # (kjv_ref, reason)

    t_start = time.perf_counter()

    for book_idx, book_data in enumerate(kjv["books"]):
        if book_idx >= 39:  # NT — handled by seed_translations_kjv_nt.py
            break
        kjv_name = book_data["name"]
        lamp_code = KJV_OT_NAME_TO_LAMP.get(kjv_name)
        if not lamp_code:
            print(f"  ! unmapped book {kjv_name!r}, skipping")
            continue
        if lamp_code in skipped_books:
            per_book[lamp_code] = {"ingested": 0, "skipped_book": True, "kjv_verse_count":
                sum(len(ch["verses"]) for ch in book_data["chapters"])}
            continue

        ingested = 0
        unmapped = 0

        for chapter_data in book_data["chapters"]:
            kjv_chapter = chapter_data["chapter"]
            for verse_data in chapter_data["verses"]:
                kjv_verse = verse_data["verse"]
                text = verse_data["text"]

                mapping = map_kjv_to_heb(lamp_code, kjv_chapter, kjv_verse, vm)
                if mapping is None:
                    unmapped += 1
                    if len(unmapped_examples) < 5:
                        unmapped_examples.append(
                            (f"{kjv_name} {kjv_chapter}:{kjv_verse}", "mapping returned None")
                        )
                    continue

                heb_chapter, heb_verse = mapping
                verse_id = f"verse:{lamp_code}.{heb_chapter}.{heb_verse}"

                if verse_id not in store.G:
                    unmapped += 1
                    if len(unmapped_examples) < 5:
                        unmapped_examples.append(
                            (f"{kjv_name} {kjv_chapter}:{kjv_verse} → {verse_id}",
                             "target verse node missing"),
                        )
                    continue

                translations.append(TranslationText(
                    translation=TRANSLATION_ID,
                    verse_id=verse_id,
                    text=text,
                    source=TRANSLATION_SOURCE,
                    source_tier=TRANSLATION_TIER,
                ))
                ingested += 1

        per_book[lamp_code] = {"ingested": ingested, "unmapped": unmapped}

    # Batch insert
    inserted = store.verses.insert_translations(translations)
    t_total = time.perf_counter() - t_start

    # Report
    print(f"{'Book':<6} {'Ingested':>10} {'Unmapped':>10}")
    print("-" * 72)
    total_ingested = 0
    total_unmapped = 0
    skipped_verse_count = 0
    for code in sorted(per_book.keys(), key=lambda c: _canonical_index(c)):
        info = per_book[code]
        if info.get("skipped_book"):
            print(f"{code:<6} {'—':>10} {'—':>10}  [SKIPPED — see versification map]")
            skipped_verse_count += info.get("kjv_verse_count", 0)
        else:
            ing = info["ingested"]
            unm = info["unmapped"]
            total_ingested += ing
            total_unmapped += unm
            marker = "  ⚠" if unm > 0 else ""
            print(f"{code:<6} {ing:>10} {unm:>10}{marker}")

    print("-" * 72)
    print(f"{'TOTAL':<6} {total_ingested:>10} {total_unmapped:>10}  ({t_total:.2f}s)")
    print()
    print(f"Translation rows inserted:      {inserted}")
    print(f"Verses in skipped books (KJV):  {skipped_verse_count}  (not ingested this phase)")

    if unmapped_examples:
        print()
        print("Sample unmapped cases:")
        for ref, reason in unmapped_examples:
            print(f"  {ref} — {reason}")

    # Spot checks
    print()
    print("Spot checks:")
    v = store.verses.get_translations_for_verse("verse:GEN.1.1")
    print(f"  Gen 1:1 KJV: {v[0].text if v else '(none)'}")
    v = store.verses.get_translations_for_verse("verse:PSA.3.2")
    print(f"  Ps 3:2 (Heb; KJV Ps 3:1): {v[0].text if v else '(none)'}")
    v = store.verses.get_translations_for_verse("verse:JOL.3.1")
    print(f"  Joel 3:1 (Heb; KJV Joel 2:28): {v[0].text if v else '(none)'}")
    v = store.verses.get_translations_for_verse("verse:MAL.3.19")
    print(f"  Mal 3:19 (Heb; KJV Mal 4:1): {v[0].text if v else '(none)'}")

    store.save()
    store.close()

    print("\n" + "=" * 72)
    print(f" RESULT: INGESTED {inserted} KJV OT verses across "
          f"{sum(1 for i in per_book.values() if not i.get('skipped_book'))} books")
    print("=" * 72)
    return 0


def _canonical_index(code: str) -> int:
    """Sort helper — canonical OT order."""
    order = [
        "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
        "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
        "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO",
        "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
    ]
    try:
        return order.index(code)
    except ValueError:
        return 999


if __name__ == "__main__":
    sys.exit(main())
