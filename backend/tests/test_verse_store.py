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


def test_reinsert_updates_verse_and_purges_old_words(store):
    v1 = _make_verse(text_cantillated="original")
    store.insert_verses([v1])
    v2 = _make_verse(text_cantillated="updated")
    store.insert_verses([v2])
    fetched = store.get_verse("verse:GEN.1.1")
    assert fetched.text_cantillated == "updated"
    # Old words purged on re-insert. Under the former INSERT OR REPLACE this
    # happened twice — once via the FK cascade, once via the explicit DELETE in
    # insert_verses. The upsert deletes nothing, so that explicit DELETE is now
    # the only thing clearing stale words; this assertion guards it.
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


def test_reinsert_verse_preserves_translations(store):
    """Re-ingesting a verse must NOT destroy its attached translations.

    Regression guard. insert_verses originally used INSERT OR REPLACE, which
    SQLite implements as DELETE-then-INSERT. With PRAGMA foreign_keys=ON that
    DELETE fired the ON DELETE CASCADE on translations.verse_id, so re-running
    seed_verses.py silently wiped all 31,104 KJV rows. The upsert form updates
    the row in place and never deletes it, so the translation survives.
    """
    store.insert_verses([_make_verse()])
    store.insert_translations([
        TranslationText(
            translation="KJV-1769",
            verse_id="verse:GEN.1.1",
            text="In the beginning God created the heaven and the earth.",
            source="KJV-1769",
            source_tier=4,
        ),
    ])
    assert len(store.get_translations_for_verse("verse:GEN.1.1")) == 1

    # Re-ingest the same verse id, as a reseed would.
    store.insert_verses([_make_verse()])

    survivors = store.get_translations_for_verse("verse:GEN.1.1")
    assert len(survivors) == 1, "reseeding a verse destroyed its translations"
    assert survivors[0].translation == "KJV-1769"


def test_reinsert_verse_refreshes_all_columns(store):
    """The upsert must refresh every column, not just the ones it happens to list.

    INSERT OR REPLACE rewrote the whole row for free. An ON CONFLICT DO UPDATE
    only touches enumerated columns, so a forgotten column would leave stale
    text in place with no error.
    """
    store.insert_verses([_make_verse()])
    updated = _make_verse(
        text_consonantal="CHANGED-consonantal",
        text_pointed="CHANGED-pointed",
        text_cantillated="CHANGED-cantillated",
        text_plain="CHANGED-plain",
        text_accented="CHANGED-accented",
        text_canonical="CHANGED-canonical",
        parashah_marker="s",
        reversed_nun=True,
        source="OSHB-WLC@newcommit",
        source_tier=2,
        language="arc",
    )
    store.insert_verses([updated])

    fetched = store.get_verse("verse:GEN.1.1")
    assert fetched is not None
    assert fetched.text_consonantal == "CHANGED-consonantal"
    assert fetched.text_pointed == "CHANGED-pointed"
    assert fetched.text_cantillated == "CHANGED-cantillated"
    assert fetched.text_plain == "CHANGED-plain"
    assert fetched.text_accented == "CHANGED-accented"
    assert fetched.text_canonical == "CHANGED-canonical"
    assert fetched.parashah_marker == "s"
    assert fetched.reversed_nun is True
    assert fetched.source == "OSHB-WLC@newcommit"
    assert fetched.source_tier == 2
    assert fetched.language == "arc"


def test_upsert_covers_every_verse_column(store):
    """VERSE_COLUMNS must match the live `verses` table exactly.

    This is the structural gate behind the two tests above. Those check the
    columns they happen to name; this one asks SQLite what columns actually
    exist and fails if VERSE_COLUMNS has drifted. Adding a column to SCHEMA_SQL
    or SCHEMA_MIGRATIONS without adding it here would otherwise leave that
    column stale on every reseed, with no error raised.
    """
    from lamp.verse_store import VERSE_COLUMNS

    live = [row[1] for row in store._require().execute("PRAGMA table_info(verses)")]
    assert set(live) == set(VERSE_COLUMNS), (
        f"verses table and VERSE_COLUMNS disagree: "
        f"only in table={sorted(set(live) - set(VERSE_COLUMNS))}, "
        f"only in VERSE_COLUMNS={sorted(set(VERSE_COLUMNS) - set(live))}"
    )


def test_verse_write_never_uses_or_replace():
    """Guard the fix itself.

    REPLACE on `verses` deletes the row before re-inserting it, which cascades
    into translations and verse_words. Reintroducing it anywhere in the module
    would re-open the data-loss path, so assert the token is absent from the
    verse-writing SQL. insert_translations may use OR REPLACE — `translations`
    has no child table.
    """
    from lamp.verse_store import VERSE_UPSERT_SQL

    assert "OR REPLACE" not in VERSE_UPSERT_SQL.upper()
    assert "ON CONFLICT(id) DO UPDATE" in VERSE_UPSERT_SQL
