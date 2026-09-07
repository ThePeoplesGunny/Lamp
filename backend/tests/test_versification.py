"""KJV → Hebrew versification mapping.

Guards the resolver in scripts/seed_translations_kjv_ot.py against the map, and
pins the cases where a uniform per-chapter offset is not enough.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "seed_translations_kjv_ot.py"
MAP_FILE = Path(__file__).parent.parent / "data" / "seed" / "versification_kjv_to_heb.json"


@pytest.fixture(scope="module")
def resolve():
    spec = importlib.util.spec_from_file_location("_kjv_ot_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resolve_kjv_verse


@pytest.fixture(scope="module")
def vm():
    return json.loads(MAP_FILE.read_text(encoding="utf-8"))


def test_psalm_13_superscription_shifts_the_whole_psalm(resolve, vm):
    """Psalm 13 was attached one verse early for the life of the corpus.

    OSHB numbers the superscription (לַמְנַצֵּחַ מִזְמוֹר לְדָוִד) as 13:1, so
    KJV 13:1-4 belong at Hebrew 13:2-5. Hebrew 13:6 then carries BOTH KJV 13:5
    and 13:6. Both chapters have six verses, which is why the Phase 2C-7
    recomputation "mechanically from OSHB↔KJV chapter-size deltas" read the
    offset as 0: the delta measures the wrong quantity when a verse is added at
    the top and two merge at the bottom. The result was that the superscription
    itself received the text of KJV 13:1.
    """
    assert resolve("PSA", 13, 1, vm) == [(13, 2)]
    assert resolve("PSA", 13, 2, vm) == [(13, 3)]
    assert resolve("PSA", 13, 3, vm) == [(13, 4)]
    assert resolve("PSA", 13, 4, vm) == [(13, 5)]
    # The reverse merge: two KJV verses onto one Hebrew verse.
    assert resolve("PSA", 13, 5, vm) == [(13, 6)]
    assert resolve("PSA", 13, 6, vm) == [(13, 6)]

    # Nothing may target the superscription.
    targets = {resolve("PSA", 13, v, vm)[0] for v in range(1, 7)}
    assert (13, 1) not in targets


def test_psalms_offsets_still_apply_where_there_is_no_override(resolve, vm):
    """The override lookup runs first now; the offset table must still work."""
    assert resolve("PSA", 3, 1, vm) == [(3, 2)]      # +1, one-line superscription
    assert resolve("PSA", 51, 1, vm) == [(51, 3)]    # +2, two-line superscription
    assert resolve("PSA", 1, 1, vm) == [(1, 1)]      # no superscription verse


def test_genesis_chapter_boundary(resolve, vm):
    """KJV Gen 31:55 is Hebrew Gen 32:1, and the rest of the chapter shifts +1."""
    assert resolve("GEN", 31, 55, vm) == [(32, 1)]
    assert resolve("GEN", 32, 1, vm) == [(32, 2)]


def test_every_override_range_is_well_formed(vm):
    """verse_min <= verse_max, and no two ranges in a book overlap.

    An overlap would make the resolver's first-match-wins order significant in a
    way nothing states, so a later edit could silently change existing mappings.
    """
    for book, entries in vm["book_overrides"].items():
        if book.startswith("_"):
            continue  # "_doc" is a prose note, not a book code
        seen: list[tuple[int, int, int]] = []
        for e in entries:
            f = e["kjv_from"]
            assert f["verse_min"] <= f["verse_max"], f"{book}: inverted range {f}"
            for ch, lo, hi in seen:
                if ch == f["chapter"]:
                    assert f["verse_max"] < lo or f["verse_min"] > hi, (
                        f"{book} chapter {ch}: ranges overlap"
                    )
            seen.append((f["chapter"], f["verse_min"], f["verse_max"]))
