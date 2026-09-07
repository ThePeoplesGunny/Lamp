"""MorphGNT / SBLGNT parser tests.

Require the morphgnt source to be present at backend/data/external/morphgnt/.
Tests are skipped with a clear reason if not.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lamp.config import EXTERNAL_DIR
from lamp.ingest.morphgnt import (
    MORPHGNT_NUM_TO_OSIS,
    parse_book,
    strip_greek_diacritics,
)
from lamp.models.book_codes import Canon, osis_to_lamp


MORPHGNT_DIR = EXTERNAL_DIR / "morphgnt"


def _skip_if_no_morphgnt():
    if not MORPHGNT_DIR.exists():
        pytest.skip(
            "MorphGNT not cloned; run `git clone https://github.com/morphgnt/sblgnt` "
            "into backend/data/external/"
        )


# ── Diacritic stripping ─────────────────────────────────────────

def test_strip_diacritics_removes_accents_and_breathings():
    # Ἀβραάμ → αβρααμ  (alpha with rough-breathing+circumflex-ish, plus accents)
    assert strip_greek_diacritics("Ἀβραάμ") == "αβρααμ"


def test_strip_diacritics_handles_iota_subscript():
    # ᾗ (eta with iota subscript) → η
    assert strip_greek_diacritics("ᾗ") == "η"


def test_strip_diacritics_lowercases():
    # Βίβλος → βιβλος
    assert strip_greek_diacritics("Βίβλος") == "βιβλος"


def test_strip_diacritics_idempotent_on_plain():
    assert strip_greek_diacritics("βιβλος") == "βιβλος"


def test_strip_diacritics_preserves_punctuation():
    # Periods and commas are NOT stripped (word-boundary preservation)
    assert strip_greek_diacritics("Ἀβραάμ.") == "αβρααμ."


# ── Book code mapping ───────────────────────────────────────────

def test_nt_osis_to_lamp():
    assert osis_to_lamp("Matt") == "MAT"
    assert osis_to_lamp("John") == "JHN"
    assert osis_to_lamp("1Cor") == "1CO"
    assert osis_to_lamp("Rev") == "REV"
    assert osis_to_lamp("Phlm") == "PHM"


def test_morphgnt_num_to_osis_coverage():
    # All 27 NT books must be present
    assert len(MORPHGNT_NUM_TO_OSIS) == 27
    # Every OSIS value must round-trip through osis_to_lamp without error
    for osis in MORPHGNT_NUM_TO_OSIS.values():
        osis_to_lamp(osis)  # will raise KeyError if missing


# ── Matthew parse integration ───────────────────────────────────

@pytest.fixture(scope="module")
def matthew():
    _skip_if_no_morphgnt()
    path = MORPHGNT_DIR / "61-Mt-morphgnt.txt"
    verses, warnings = parse_book(path)
    return verses, warnings


def test_matthew_parses_without_warnings(matthew):
    _, warnings = matthew
    assert warnings == []


def test_matthew_verse_count_matches_sblgnt(matthew):
    """SBLGNT (critical text) Matthew has 1068 verses, NOT 1071.

    The 3 missing verses are the famous textual-critical omissions absent from
    earliest manuscripts:
      Matt 17:21 — "But this kind does not go out except by prayer and fasting"
      Matt 18:11 — "For the Son of Man has come to save the lost"
      Matt 23:14 — "Woe unto you, scribes and Pharisees, hypocrites! for ye devour widows' houses..."
    """
    verses, _ = matthew
    assert len(verses) == 1068


def test_matthew_omitted_verses_not_present(matthew):
    """Explicit: the three SBLGNT-omitted verses must NOT be in the output."""
    verses, _ = matthew
    ids = {v.id for v in verses}
    assert "verse:MAT.17.21" not in ids
    assert "verse:MAT.18.11" not in ids
    assert "verse:MAT.23.14" not in ids


def test_mat_1_1_structure(matthew):
    verses, _ = matthew
    v = verses[0]
    assert v.id == "verse:MAT.1.1"
    assert v.book == "MAT"
    assert v.chapter == 1
    assert v.verse == 1
    assert v.canon == Canon.NT
    assert v.language == "grc"
    # text_canonical equals text_accented for Greek
    assert v.text_canonical == v.text_accented
    # text_plain must differ from accented (diacritics stripped, lowercased)
    assert v.text_plain != v.text_accented
    # Mat 1:1 has 8 words
    assert len(v.words) == 8
    # Expected first word — Βίβλος, noun nominative singular feminine
    first = v.words[0]
    assert first.lemma == "βίβλος"
    assert first.morph_code == "GN-----NSF-"  # G-prefix, Greek Noun, nom sg fem
    assert first.text_canonical == first.text_accented


def test_mat_1_1_text_plain_is_lowercase_no_diacritics(matthew):
    verses, _ = matthew
    v = verses[0]
    # No uppercase letters
    assert v.text_plain == v.text_plain.lower()
    # No Greek combining marks in the plain layer
    import unicodedata
    decomposed = unicodedata.normalize("NFD", v.text_plain)
    assert not any(unicodedata.category(c) == "Mn" for c in decomposed)


def test_greek_word_has_no_hebrew_fields_populated(matthew):
    """Greek verses must not populate the Hebrew-specific text fields."""
    verses, _ = matthew
    v = verses[0]
    assert v.text_consonantal == ""
    assert v.text_pointed == ""
    assert v.text_cantillated == ""
    assert v.parashah_marker is None
    assert v.reversed_nun is False
    for w in v.words:
        assert w.text_consonantal == ""
        assert w.text_pointed == ""
        assert w.text_cantillated == ""
        assert w.oshb_word_id is None
        assert w.text_ketiv is None
        assert w.text_qere is None


def test_greek_source_provenance(matthew):
    verses, _ = matthew
    v = verses[0]
    assert v.source.startswith("MorphGNT-SBLGNT@")
    # Tier 2 = original-language witness, supporting the KJV 1769 base text.
    # Was 1 until the 2026-09-07 base-text decision (CLAUDE.md Locked Decision 8)
    # moved the KJV to tier 1 and the original languages beneath it.
    assert v.source_tier == 2
