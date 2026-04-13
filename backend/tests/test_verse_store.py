"""VerseStore (SQLite) round-trip and query tests.

All tests use in-memory SQLite (db_path=None) — no filesystem dependency.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lamp.models import Canon, TranslationText, Verse, VerseWord
from lamp.verse_store import VerseStore


def _make_verse(
    verse_id: str = "verse:GEN.1.1",
    book: str = "GEN",
    chapter: int = 1,
    verse: int = 1,
    words: list[VerseWord] | None = None,
    **overrides,
) -> Verse:
    if words is None:
        words = [
            VerseWord(
                position=1,
                text_consonantal="בראשית",
                text_pointed="בְּרֵאשִׁית",
                text_cantillated="בְּרֵאשִׁ֖ית",
                lemma="b/7225",
                strongs="7225",
                morph_code="HR/Ncfsa",
                oshb_word_id="01xeN",
            ),
        ]
    fields = {
        "id": verse_id,
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "canon": Canon.TANAKH,
        "language": "hbo",
        "text_consonantal": "בראשית",
        "text_pointed": "בְּרֵאשִׁית",
        "text_cantillated": "בְּרֵאשִׁ֖ית",
        "words": words,
        "source": "OSHB-WLC@test",
        "source_tier": 1,
    }
    fields.update(overrides)
    return Verse(**fields)


@pytest.fixture
def store():
    s = VerseStore(db_path=None)
    s.connect()
    yield s
    s.close()


def test_requires_connect():
    s = VerseStore(db_path=None)
    with pytest.raises(RuntimeError, match="not connected"):
        s.get_verse("verse:GEN.1.1")


def test_round_trip_single_verse(store):
    original = _make_verse()
    store.insert_verses([original])
    fetched = store.get_verse("verse:GEN.1.1")
    assert fetched is not None
    assert fetched.id == original.id
    assert fetched.text_cantillated == original.text_cantillated
    assert fetched.text_pointed == original.text_pointed
    assert fetched.text_consonantal == original.text_consonantal
    assert fetched.canon == Canon.TANAKH
    assert len(fetched.words) == 1
    assert fetched.words[0].strongs == "7225"
    assert fetched.words[0].morph_code == "HR/Ncfsa"


def test_round_trip_preserves_reversed_nun(store):
    v = _make_verse(verse_id="verse:NUM.10.36", book="NUM", chapter=10, verse=36, reversed_nun=True)
    store.insert_verses([v])
    fetched = store.get_verse("verse:NUM.10.36")
    assert fetched is not None
    assert fetched.reversed_nun is True


def test_round_trip_preserves_parashah_marker(store):
    v = _make_verse(verse_id="verse:GEN.1.5", verse=5, parashah_marker="pe")
    store.insert_verses([v])
    fetched = store.get_verse("verse:GEN.1.5")
    assert fetched.parashah_marker == "pe"


def test_round_trip_preserves_notes(store):
    v = _make_verse(notes=["First note", "Second note"])
    store.insert_verses([v])
    fetched = store.get_verse("verse:GEN.1.1")
    assert fetched.notes == ["First note", "Second note"]


def test_round_trip_preserves_ketiv_qere(store):
    word = VerseWord(
        position=1,
        text_consonantal="",
        text_pointed="",
        text_cantillated="",
        text_ketiv="",
        text_qere="בְּנֵי",
    )
    v = _make_verse(verse_id="verse:JDG.20.13", book="JDG", chapter=20, verse=13, words=[word])
    store.insert_verses([v])
    fetched = store.get_verse("verse:JDG.20.13")
    assert fetched.words[0].text_ketiv == ""
    assert fetched.words[0].text_qere == "בְּנֵי"


def test_get_verse_missing_returns_none(store):
    assert store.get_verse("verse:GEN.999.999") is None


def test_batch_insert_and_fetch(store):
    verses = [
        _make_verse(verse_id=f"verse:GEN.1.{i}", verse=i) for i in range(1, 6)
    ]
    store.insert_verses(verses)
    fetched = store.get_verses([f"verse:GEN.1.{i}" for i in range(1, 6)])
    assert len(fetched) == 5


def test_insert_or_replace_semantics(store):
    v1 = _make_verse(text_cantillated="original")
    store.insert_verses([v1])
    v2 = _make_verse(text_cantillated="updated")
    store.insert_verses([v2])
    fetched = store.get_verse("verse:GEN.1.1")
    assert fetched.text_cantillated == "updated"
    # Word replacement: old words purged on re-insert
    assert store.count_words() == 1


def test_stats(store):
    store.insert_verses([
        _make_verse(verse_id="verse:GEN.1.1", book="GEN", chapter=1, verse=1),
        _make_verse(verse_id="verse:GEN.1.2", book="GEN", chapter=1, verse=2),
        _make_verse(verse_id="verse:EXO.1.1", book="EXO", chapter=1, verse=1),
    ])
    assert store.count_verses() == 3
    assert store.count_by_book() == {"EXO": 1, "GEN": 2}


def test_translation_insert_and_fetch(store):
    store.insert_verses([_make_verse()])
    store.insert_translations([
        TranslationText(
            translation="KJV-1769",
            verse_id="verse:GEN.1.1",
            text="In the beginning God created the heaven and the earth.",
            source="KJV-1769",
            source_tier=4,
        ),
        TranslationText(
            translation="ASV-1901",
            verse_id="verse:GEN.1.1",
            text="In the beginning God created the heavens and the earth.",
            source="ASV-1901",
            source_tier=4,
        ),
    ])
    translations = store.get_translations_for_verse("verse:GEN.1.1")
    assert len(translations) == 2
    assert {t.translation for t in translations} == {"KJV-1769", "ASV-1901"}


def test_translation_fk_cascade(store):
    """Deleting a verse should cascade-delete its translations."""
    store.insert_verses([_make_verse()])
    store.insert_translations([
        TranslationText(
            translation="KJV-1769",
            verse_id="verse:GEN.1.1",
            text="...",
            source="KJV-1769",
            source_tier=4,
        ),
    ])
    with store._require():
        store._require().execute("DELETE FROM verses WHERE id = ?", ("verse:GEN.1.1",))
    assert store.get_translations_for_verse("verse:GEN.1.1") == []
