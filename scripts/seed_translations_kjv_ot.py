"""Phase 2C-7 — ingest KJV 1769 OT with full Hebrew↔English versification map.

Replaces the Phase 2C-6 ingest. Uses backend/data/seed/versification_kjv_to_heb.json
which now covers all 39 OT books (no skipped_books) and all chapter-boundary shifts
verified against OSHB content.

Schema:
  - psalms_offsets: chapter → integer (offset to add to KJV verse number)
  - book_overrides: book_code → list of overrides
      {kjv_from: {chapter, verse_min, verse_max},
       heb: {chapter, verse_offset},
       extra_targets: [{chapter, verse}, ...]   # optional
      }

Merge semantics:
  - One KJV verse → multiple Heb verses (e.g. NUM 26:1 = Heb 25:19 + Heb 26:1):
    encoded via `extra_targets`. KJV text is attached to every listed Heb verse.
  - Multiple KJV verses → one Heb verse (e.g. NEH 7:67 absorbs KJV 7:67 + KJV 7:68):
    detected automatically when two KJV mappings resolve to the same target.
    KJV texts are concatenated with " | " as separator.

Usage: python scripts/seed_translations_kjv_ot.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
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

OT_ORDER = list(KJV_OT_NAME_TO_LAMP.values())

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

MERGE_SEPARATOR = " | "


def resolve_kjv_verse(
    code: str,
    kjv_chapter: int,
    kjv_verse: int,
    vm: dict,
) -> list[tuple[int, int]]:
    """Return list of (heb_chapter, heb_verse) targets for a KJV verse.

    Empty list if no target. Most KJV verses produce a single (ch, v); merge
    cases (extra_targets in versification map) produce multiple.
    """
    # Psalms — uniform per-chapter offset
    if code == "PSA":
        offset = vm["psalms_offsets"].get(str(kjv_chapter), 0)
        return [(kjv_chapter, kjv_verse + offset)]

    overrides = vm["book_overrides"].get(code, [])
    for override in overrides:
        if override.get("_note") and "kjv_from" not in override:
            continue
        f = override["kjv_from"]
        if kjv_chapter == f["chapter"] and f["verse_min"] <= kjv_verse <= f["verse_max"]:
            heb = override["heb"]
            primary = (heb["chapter"], kjv_verse + heb["verse_offset"])
            targets = [primary]
            for et in override.get("extra_targets", []):
                targets.append((et["chapter"], et["verse"]))
            return targets

    # Default: direct pass-through (KJV.ch.v → Heb.ch.v)
    return [(kjv_chapter, kjv_verse)]


def main() -> int:
    if not KJV_SOURCE.exists():
        print(f"ERROR: {KJV_SOURCE} not found.")
        return 1
    if not VERSIFICATION_MAP.exists():
        print(f"ERROR: {VERSIFICATION_MAP} not found.")
        return 1

    print("=" * 72)
    print(" Lamp — KJV 1769 OT translation ingest (Phase 2C-7, full versification)")
    print("=" * 72)

    with open(KJV_SOURCE, encoding="utf-8") as f:
        kjv = json.load(f)
    with open(VERSIFICATION_MAP, encoding="utf-8") as f:
        vm = json.load(f)

    store = GraphStore(graph_path=GRAPH_FILE, verse_db_path=VERSES_DB_FILE)
    store.load()

    # Aggregate: target_verse_id -> list of KJV texts to concatenate
    by_target: dict[str, list[str]] = defaultdict(list)
    per_book_kjv: dict[str, int] = defaultdict(int)
    per_book_attached: dict[str, int] = defaultdict(int)
    per_book_unmapped: dict[str, int] = defaultdict(int)
    unmapped_examples: list[tuple[str, str]] = []

    t_start = time.perf_counter()

    for book_idx, book_data in enumerate(kjv["books"]):
        if book_idx >= 39:  # NT handled by seed_translations_kjv_nt.py
            break
        kjv_name = book_data["name"]
        code = KJV_OT_NAME_TO_LAMP.get(kjv_name)
        if not code:
            print(f"  ! unmapped book {kjv_name!r}, skipping")
            continue

        for chapter_data in book_data["chapters"]:
            kch = chapter_data["chapter"]
            for verse_data in chapter_data["verses"]:
                kvs = verse_data["verse"]
                text = verse_data["text"]
                per_book_kjv[code] += 1

                targets = resolve_kjv_verse(code, kch, kvs, vm)
                attached_any = False
                for hch, hvs in targets:
                    target_id = f"verse:{code}.{hch}.{hvs}"
                    if target_id not in store.G:
                        if len(unmapped_examples) < 12:
                            unmapped_examples.append(
                                (f"{kjv_name} {kch}:{kvs} → {target_id}", "target verse node missing")
                            )
                        continue
                    by_target[target_id].append(text)
                    attached_any = True

                if attached_any:
                    per_book_attached[code] += 1
                else:
                    per_book_unmapped[code] += 1

    # Build TranslationText rows. Multiple KJV verses targeting the same Heb verse
    # have their texts concatenated with MERGE_SEPARATOR.
    translations: list[TranslationText] = []
    merge_count = 0
    for target_id, texts in by_target.items():
        if len(texts) > 1:
            merge_count += 1
            merged = MERGE_SEPARATOR.join(texts)
        else:
            merged = texts[0]
        translations.append(TranslationText(
            translation=TRANSLATION_ID,
            verse_id=target_id,
            text=merged,
            source=TRANSLATION_SOURCE,
            source_tier=TRANSLATION_TIER,
        ))

    inserted = store.verses.insert_translations(translations)
    t_total = time.perf_counter() - t_start

    # Report
    print(f"{'Book':<6} {'KJV verses':>11} {'Attached':>10} {'Unmapped':>10}")
    print("-" * 72)
    total_kjv = total_attached = total_unmapped = 0
    for code in OT_ORDER:
        if code not in per_book_kjv:
            continue
        kjv_n = per_book_kjv[code]
        att_n = per_book_attached[code]
        unm_n = per_book_unmapped[code]
        total_kjv += kjv_n
        total_attached += att_n
        total_unmapped += unm_n
        marker = "  ⚠" if unm_n > 0 else ""
        print(f"{code:<6} {kjv_n:>11} {att_n:>10} {unm_n:>10}{marker}")

    print("-" * 72)
    print(f"{'TOTAL':<6} {total_kjv:>11} {total_attached:>10} {total_unmapped:>10}  ({t_total:.2f}s)")
    print()
    print(f"Translation rows inserted (after merge):  {inserted}")
    print(f"Heb verses receiving multi-KJV merge:     {merge_count}")
    if merge_count:
        for tid, txts in by_target.items():
            if len(txts) > 1:
                print(f"  merged at {tid}: {len(txts)} KJV verses concatenated")

    if unmapped_examples:
        print()
        print("Unmapped cases:")
        for ref, reason in unmapped_examples:
            print(f"  {ref} — {reason}")

    # Spot-checks across all the boundary cases
    print()
    print("Spot checks:")
    spots = [
        ("verse:GEN.1.1", "Gen 1:1"),
        ("verse:GEN.32.1", "Gen 32:1 Heb (= KJV 31:55, 'Laban rose up')"),
        ("verse:EXO.7.26", "Exo 7:26 Heb (= KJV 8:1, frog warning)"),
        ("verse:LEV.5.20", "Lev 5:20 Heb (= KJV 6:1, 'LORD spake')"),
        ("verse:NUM.17.1", "Num 17:1 Heb (= KJV 16:36, 'Aaron returned')"),
        ("verse:NUM.25.19", "Num 25:19 Heb (= KJV 26:1a, 'after the plague')"),
        ("verse:NUM.30.1",  "Num 30:1 Heb (= KJV 29:40, 'Moses told Israel')"),
        ("verse:DEU.13.1",  "Deu 13:1 Heb (= KJV 12:32, 'observe to do it')"),
        ("verse:DEU.28.69", "Deu 28:69 Heb (= KJV 29:1, 'words of the covenant')"),
        ("verse:1SA.21.1",  "1Sa 21:1 Heb (= KJV 20:42b, 'arose and departed')"),
        ("verse:1KI.5.1",   "1Ki 5:1 Heb (= KJV 4:21, 'Solomon reigned')"),
        ("verse:1CH.5.27",  "1Ch 5:27 Heb (= KJV 6:1, 'sons of Levi')"),
        ("verse:NEH.3.33",  "Neh 3:33 Heb (= KJV 4:1, 'Sanballat')"),
        ("verse:JOB.40.25", "Job 40:25 Heb (= KJV 41:1, 'leviathan')"),
        ("verse:PSA.3.2",   "Ps 3:2 Heb (= KJV 3:1, 'how are they increased')"),
        ("verse:PSA.11.7",  "Ps 11:7 Heb (= KJV 11:7, no offset — was wrongly +1)"),
        ("verse:PSA.51.3",  "Ps 51:3 Heb (= KJV 51:1, 'have mercy', 2-line super)"),
        ("verse:ISA.9.1",   "Isa 9:1 Heb (= KJV 9:2, after 'land of Zebulun')"),
        ("verse:JER.8.23",  "Jer 8:23 Heb (= KJV 9:1, 'head were waters')"),
        ("verse:EZK.21.1",  "Ezk 21:1 Heb (= KJV 20:45, 'word of the LORD')"),
        ("verse:DAN.3.31",  "Dan 3:31 Heb (= KJV 4:1, 'Nebuchadnezzar to all')"),
        ("verse:HOS.2.1",   "Hos 2:1 Heb (= KJV 1:10, 'as the sand of the sea')"),
        ("verse:JOL.3.1",   "Joel 3:1 Heb (= KJV 2:28, 'pour out my Spirit')"),
        ("verse:JON.2.1",   "Jonah 2:1 Heb (= KJV 1:17, 'great fish')"),
        ("verse:ZEC.2.1",   "Zec 2:1 Heb (= KJV 1:18, 'four horns')"),
        ("verse:MAL.3.19",  "Mal 3:19 Heb (= KJV 4:1, 'day cometh')"),
    ]
    for vid, label in spots:
        v = store.verses.get_translations_for_verse(vid)
        text = v[0].text if v else "(none)"
        if len(text) > 90:
            text = text[:90] + "…"
        print(f"  {label:<55}  {text}")

    store.save()
    store.close()

    print("\n" + "=" * 72)
    print(f" RESULT: INGESTED {inserted} KJV OT verses across {sum(1 for c in per_book_kjv)} books")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
