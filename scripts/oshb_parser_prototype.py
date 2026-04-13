"""OSHB parser prototype — Phase 2C-1 Step 2b.

Parses Genesis from OSHB, prints sample output, reports counts/warnings.
Used for Gunny's review before full 39-book ingest.

Usage:
    python scripts/oshb_parser_prototype.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Windows console defaults to cp1252; Hebrew needs UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Make `lamp` package importable when run from the repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from lamp.ingest.oshb import parse_book  # noqa: E402


MORPHHB = REPO_ROOT / "backend" / "data" / "external" / "morphhb" / "wlc"


def _fmt_word(w) -> str:
    parts = [f"  [{w.position}]"]
    parts.append(f"cantillated={w.text_cantillated!r}")
    parts.append(f"pointed={w.text_pointed!r}")
    parts.append(f"consonantal={w.text_consonantal!r}")
    parts.append(f"lemma={w.lemma!r}")
    parts.append(f"strongs={w.strongs!r}")
    parts.append(f"morph={w.morph_code!r}")
    parts.append(f"oshb_id={w.oshb_word_id!r}")
    if w.text_ketiv or w.text_qere:
        parts.append(f"ketiv={w.text_ketiv!r} qere={w.text_qere!r}")
    return "\n    ".join(parts)


def main() -> int:
    gen_path = MORPHHB / "Gen.xml"
    if not gen_path.exists():
        print(f"ERROR: {gen_path} not found. Did OSHB clone succeed?")
        return 1

    print(f"Parsing {gen_path}...")
    verses, warnings = parse_book(gen_path)
    print(f"  Verses parsed: {len(verses)}")

    total_words = sum(len(v.words) for v in verses)
    ketiv_qere_words = sum(
        1 for v in verses for w in v.words if w.text_ketiv is not None
    )
    parashah_count = sum(1 for v in verses if v.parashah_marker is not None)
    pe_count = sum(1 for v in verses if v.parashah_marker == "pe")
    samekh_count = sum(1 for v in verses if v.parashah_marker == "samekh")
    note_count = sum(len(v.notes) for v in verses)
    source = verses[0].source if verses else "n/a"

    print(f"  Source: {source}")
    print(f"  Total words: {total_words}")
    print(f"  Ketiv/Qere variants: {ketiv_qere_words}")
    print(f"  Parashah markers: {parashah_count} (pe={pe_count}, samekh={samekh_count})")
    print(f"  Masoretic notes: {note_count}")
    print(f"  Warnings: {len(warnings)}")
    for w in warnings[:10]:
        print(f"    ! {w}")
    if len(warnings) > 10:
        print(f"    ... and {len(warnings) - 10} more")

    # Expected: 1,533 verses in Genesis per standard MT reckoning
    print(f"\nExpected (MT standard): 1533 verses in Genesis")
    print(f"Actual: {len(verses)} — "
          f"{'OK' if len(verses) == 1533 else 'MISMATCH — investigate'}")

    print("\n" + "=" * 70)
    print("SAMPLE: Genesis 1:1")
    print("=" * 70)
    v = verses[0]
    print(f"id:              {v.id}")
    print(f"book:            {v.book}")
    print(f"chapter:         {v.chapter}")
    print(f"verse:           {v.verse}")
    print(f"canon:           {v.canon}")
    print(f"language:        {v.language}")
    print(f"source:          {v.source}  (tier {v.source_tier})")
    print(f"parashah_marker: {v.parashah_marker}")
    print(f"notes:           {v.notes}")
    print(f"text_cantillated: {v.text_cantillated!r}")
    print(f"text_pointed:     {v.text_pointed!r}")
    print(f"text_consonantal: {v.text_consonantal!r}")
    print(f"words ({len(v.words)}):")
    for w in v.words:
        print(_fmt_word(w))

    # Show a verse with a parashah marker (first one found)
    parashah_verse = next((v for v in verses if v.parashah_marker), None)
    if parashah_verse:
        print("\n" + "=" * 70)
        print(f"SAMPLE (with parashah marker): {parashah_verse.id}")
        print("=" * 70)
        print(f"parashah_marker: {parashah_verse.parashah_marker}")
        print(f"text_cantillated: {parashah_verse.text_cantillated!r}")

    # Show a verse with ketiv/qere (first one found)
    kq_verse = next(
        (v for v in verses if any(w.text_ketiv is not None for w in v.words)),
        None,
    )
    if kq_verse:
        print("\n" + "=" * 70)
        print(f"SAMPLE (with ketiv/qere): {kq_verse.id}")
        print("=" * 70)
        print(f"text_cantillated: {kq_verse.text_cantillated!r}")
        print(f"notes: {kq_verse.notes}")
        for w in kq_verse.words:
            if w.text_ketiv is not None:
                print(f"  [{w.position}] ketiv={w.text_ketiv!r}  qere={w.text_qere!r}  "
                      f"lemma={w.lemma!r} morph={w.morph_code!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
