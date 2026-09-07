"""OSHB parser tests.

Require the morphhb/wlc source to be present at backend/data/external/morphhb/.
Tests are skipped with a clear reason if not.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lamp.config import EXTERNAL_DIR
from lamp.ingest.oshb import (
    extract_strongs,
    parse_book,
    strip_cantillation,
    strip_niqqud,
    to_consonantal,
)
from lamp.models.book_codes import Canon, osis_to_lamp


MORPHHB_WLC = EXTERNAL_DIR / "morphhb" / "wlc"

_requires_oshb = pytest.mark.skipif(
    not MORPHHB_WLC.exists(),
    reason="OSHB not cloned; run `git clone https://github.com/openscriptures/morphhb` into backend/data/external/",
)


def _skip_if_no_oshb():
    if not MORPHHB_WLC.exists():
        pytest.skip("OSHB not cloned; see README")


# ── Unicode strip primitives ────────────────────────────────────

def test_strip_cantillation_removes_teamim():
    # בָּרָ֣א has cantillation mark (U+05A3 munach); stripping leaves pointed form
    cantillated = "בָּרָ֣א"
    assert strip_cantillation(cantillated) == "בָּרָא"


def test_strip_niqqud_removes_vowel_points():
    # After cantillation stripped: בָּרָא still has qamatz; removing niqqud leaves consonants
    pointed = "בָּרָא"
    assert strip_niqqud(pointed) == "ברא"


def test_to_consonantal_strips_both_layers():
    cantillated = "בְּרֵאשִׁ֖ית"
    assert to_consonantal(cantillated) == "בראשית"


def test_strip_is_idempotent_on_already_stripped():
    assert strip_cantillation("בראשית") == "בראשית"
    assert strip_niqqud("בראשית") == "בראשית"


# ── Strong's extraction ─────────────────────────────────────────

def test_extract_strongs_simple():
    assert extract_strongs("1254") == "1254"


def test_extract_strongs_with_suffix():
    # "1254 a" — first numeric run is the Strong's number
    assert extract_strongs("1254 a") == "1254"


def test_extract_strongs_with_segmentation():
    # "c/m/6529" — prefix segments, final is the root Strong's
    assert extract_strongs("c/m/6529") == "6529"


def test_extract_strongs_none_for_none():
    assert extract_strongs(None) is None
    assert extract_strongs("") is None


# ── Book code mapping ───────────────────────────────────────────

def test_osis_to_lamp_basic():
    assert osis_to_lamp("Gen") == "GEN"
    assert osis_to_lamp("Exod") == "EXO"
    assert osis_to_lamp("Ps") == "PSA"
    assert osis_to_lamp("1Sam") == "1SA"
    assert osis_to_lamp("Nah") == "NAM"


def test_osis_to_lamp_unknown_raises():
    with pytest.raises(KeyError):
        osis_to_lamp("NotABook")


# ── Genesis parse integration ───────────────────────────────────

@pytest.fixture(scope="module")
def genesis():
    _skip_if_no_oshb()
    verses, warnings = parse_book(MORPHHB_WLC / "Gen.xml")
    return verses, warnings


@_requires_oshb
def test_genesis_verse_count(genesis):
    verses, _ = genesis
    # Published MT reference for Genesis
    assert len(verses) == 1533


@_requires_oshb
def test_genesis_parses_without_warnings(genesis):
    _, warnings = genesis
    assert warnings == []


@_requires_oshb
def test_gen_1_1_three_layers(genesis):
    """Verify the three text layers differ correctly by structural content.

    Asserted structurally (not by literal string match) because Unicode combining-mark
    order can vary between sources without changing the rendered text.
    """
    verses, _ = genesis
    v = verses[0]
    assert v.id == "verse:GEN.1.1"
    assert v.book == "GEN"
    assert v.chapter == 1
    assert v.verse == 1
    assert v.canon == Canon.TANAKH
    assert v.language == "hbo"

    # Consonantal: no niqqud, no te'amim (only base Hebrew letters + punctuation)
    niqqud_range = range(0x05B0, 0x05BD)  # + U+05C1, U+05C2, U+05C7
    cantillation_range = range(0x0591, 0x05B0)
    assert not any(ord(ch) in niqqud_range for ch in v.text_consonantal)
    assert not any(ord(ch) in cantillation_range for ch in v.text_consonantal)

    # Pointed: has niqqud, no te'amim
    assert any(ord(ch) in niqqud_range for ch in v.text_pointed)
    assert not any(ord(ch) in cantillation_range for ch in v.text_pointed)

    # Cantillated: has both layers
    assert any(ord(ch) in niqqud_range for ch in v.text_cantillated)
    assert any(ord(ch) in cantillation_range for ch in v.text_cantillated)

    # Length ordering: consonantal < pointed < cantillated (strict)
    assert len(v.text_consonantal) < len(v.text_pointed) < len(v.text_cantillated)


@_requires_oshb
def test_gen_1_1_word_count_and_morphology(genesis):
    verses, _ = genesis
    v = verses[0]
    # Gen 1:1 has 7 words in the Masoretic text
    assert len(v.words) == 7
    bara = v.words[1]  # "בָּרָא" — created
    assert bara.strongs == "1254"
    assert bara.morph_code == "HVqp3ms"
    assert bara.text_consonantal == "ברא"
    assert bara.oshb_word_id is not None


@_requires_oshb
def test_ketiv_qere_pairing(genesis):
    """Gen 8:17 has a ketiv/qere: ketiv='הוצא' (unpointed), qere='הַיְצֵ֣א' (pointed)."""
    verses, _ = genesis
    target = next(v for v in verses if v.id == "verse:GEN.8.17")
    kq_words = [w for w in target.words if w.text_ketiv and w.text_qere]
    assert len(kq_words) == 1
    w = kq_words[0]
    assert w.text_ketiv == "הוצא"
    assert "היצא" in to_consonantal(w.text_qere)


@_requires_oshb
def test_parashah_marker_captured(genesis):
    """Gen 1:5 ends a parashah (end of creation day 1 — open paragraph 'pe')."""
    verses, _ = genesis
    v15 = next(v for v in verses if v.id == "verse:GEN.1.5")
    assert v15.parashah_marker == "pe"


@_requires_oshb
def test_source_provenance_captured(genesis):
    verses, _ = genesis
    v = verses[0]
    assert v.source.startswith("OSHB-WLC@")
    # Tier 2 = original-language witness, supporting the KJV 1769 base text.
    # Was 1 until the 2026-09-07 base-text decision (CLAUDE.md Locked Decision 8)
    # moved the KJV to tier 1 and the original languages beneath it.
    assert v.source_tier == 2
