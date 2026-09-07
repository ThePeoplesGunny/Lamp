"""VerseStore (SQLite) round-trip and query tests.

All tests use in-memory SQLite (db_path=None) — no filesystem dependency.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lamp.models import Canon, TranslationText, Verse, VerseRef, VerseWord
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


def test_deleting_verse_identity_cascades_to_everything(store):
    """Deleting the verse ITSELF removes the base text and the witness with it.

    Rewritten 2026-09-07. This used to delete from `verses` and assert the
    translations went too — correct when `translations` hung off `verses`, and
    exactly the behaviour the identity/witness split removed. The cascade now
    runs from identity: dropping the verse drops everything about it, while
    dropping only a witness leaves the base text standing
    (test_deleting_a_witness_leaves_the_base_text_standing).
    """
    store.insert_verses([_make_verse()])
    store.insert_translations([
        TranslationText(
            translation="KJV-1769",
            verse_id="verse:GEN.1.1",
            text="...",
            source="KJV-1769",
            source_tier=1,
        ),
    ])
    conn = store._require()
    with conn:
        conn.execute("DELETE FROM verse_refs WHERE id = ?", ("verse:GEN.1.1",))

    assert store.get_translations_for_verse("verse:GEN.1.1") == []
    assert store.get_verse("verse:GEN.1.1") is None
    assert store.count_words() == 0


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


def test_deleting_a_witness_leaves_the_base_text_standing(store):
    """THE acceptance test for the identity/witness split.

    Under Locked Decision 8 the KJV 1769 is the base text and the
    original-language text is a supporting witness. Removing a witness must
    therefore not destroy the base text. Before the split, `translations` had
    ON DELETE CASCADE onto `verses`, so deleting the Hebrew or Greek row for a
    verse silently deleted its KJV text — the base text dying as a side effect
    of dropping a supporting source.

    The words go with the witness, because they are part of it.
    """
    store.insert_verses([_make_verse()])
    store.insert_translations([
        TranslationText(
            translation="KJV-1769",
            verse_id="verse:GEN.1.1",
            text="In the beginning God created the heaven and the earth.",
            source="KJV-1769",
            source_tier=1,
        ),
    ])
    assert len(store.get_translations_for_verse("verse:GEN.1.1")) == 1
    assert store.count_words() == 1

    # Drop the original-language witness only.
    conn = store._require()
    with conn:
        conn.execute("DELETE FROM verses WHERE id = ?", ("verse:GEN.1.1",))

    survivors = store.get_translations_for_verse("verse:GEN.1.1")
    assert len(survivors) == 1, "deleting a witness destroyed the KJV base text"
    assert survivors[0].text.startswith("In the beginning")
    assert store.count_words() == 0, "words belong to the witness and should go with it"


def test_upsert_covers_every_verse_ref_column(store):
    """Same structural gate as the witness table, for verse_refs."""
    from lamp.verse_store import VERSE_REF_COLUMNS

    live = [row[1] for row in store._require().execute("PRAGMA table_info(verse_refs)")]
    assert set(live) == set(VERSE_REF_COLUMNS), (
        f"verse_refs and VERSE_REF_COLUMNS disagree: "
        f"only in table={sorted(set(live) - set(VERSE_REF_COLUMNS))}, "
        f"only in VERSE_REF_COLUMNS={sorted(set(VERSE_REF_COLUMNS) - set(live))}"
    )


def _kjv_only(store, verse_id="verse:ACT.8.37", book="ACT", chapter=8, verse=37):
    """A verse with identity and a base text but no original-language witness."""
    store.insert_verse_refs([
        VerseRef(
            id=verse_id, book=book, chapter=chapter, verse=verse,
            canon=Canon.NT,
            notes=["Verse absent from SBLGNT critical text; present in KJV/Byzantine."],
        ),
    ])
    store.insert_translations([
        TranslationText(
            translation="KJV-1769", verse_id=verse_id,
            text="And Philip said, If thou believest with all thine heart, thou mayest.",
            source="KJV-1769", source_tier=1,
        ),
    ])


def test_kjv_only_verse_needs_no_fabricated_witness(store):
    """A KJV verse can now exist with no original-language row behind it.

    This is the whole point of the split. Acts 8:37 is in the KJV and absent from
    the SBLGNT; it used to require a fabricated empty Greek row in `verses`, with
    the KJV file as its source, purely so the base text had a parent.
    """
    _kjv_only(store)

    assert store.count_verses() == 1, "the verse exists"
    assert store.count_witnesses() == 0, "and has no fabricated witness row"

    v = store.get_verse("verse:ACT.8.37")
    assert v is not None, "a witness-less verse must not read as 'not found'"
    assert v.book == "ACT" and v.chapter == 8 and v.verse == 37
    assert v.text_canonical == ""
    assert v.words == []
    assert v.source is None and v.source_tier is None, (
        "no witness means no witness provenance to cite"
    )
    assert v.language == "grc", "display language falls back to the canon"
    assert v.notes and "absent from SBLGNT" in v.notes[0]

    kjv = store.get_translations_for_verse("verse:ACT.8.37")
    assert len(kjv) == 1 and kjv[0].source_tier == 1


def test_kjv_only_verse_stays_visible_in_navigation(store):
    """Identity drives navigation, so a witness-less verse is still reachable.

    If these queries read the witness table, Acts 8:37 would vanish from /read
    and prev/next would silently skip it — invisible to any count-based check.
    """
    store.insert_verses([
        _make_verse(verse_id="verse:ACT.8.36", book="ACT", chapter=8, verse=36,
                    canon=Canon.NT, language="grc"),
        _make_verse(verse_id="verse:ACT.8.38", book="ACT", chapter=8, verse=38,
                    canon=Canon.NT, language="grc"),
    ])
    _kjv_only(store)
    # The ingest always writes addresses; NT numbering is shared with the KJV.
    store.set_kjv_addresses({
        "verse:ACT.8.36": ("ACT", 8, 36),
        "verse:ACT.8.37": ("ACT", 8, 37),
        "verse:ACT.8.38": ("ACT", 8, 38),
    })

    listed = store.chapter_verses("ACT", 8)
    assert [r["verse"] for r in listed] == [36, 37, 38], "KJV-only verse dropped out of /read"

    assert store.next_verse_id("verse:ACT.8.36") == "verse:ACT.8.37"
    assert store.prev_verse_id("verse:ACT.8.38") == "verse:ACT.8.37"

    books = {b["book"]: b for b in store.books_summary()}
    assert books["ACT"]["verse_count"] == 3, "identity drives the count"
    assert books["ACT"]["language"] == "grc", "language still derived from the witnesses"
    assert store.count_by_book()["ACT"] == 3


def test_kjv_address_is_recorded_and_resolvable(store):
    """The KJV address is first-class data on identity, and resolves back."""
    store.insert_verses([
        _make_verse(verse_id="verse:GEN.32.1", book="GEN", chapter=32, verse=1),
        _make_verse(verse_id="verse:GEN.32.2", book="GEN", chapter=32, verse=2),
    ])
    store.set_kjv_addresses({
        "verse:GEN.32.1": ("GEN", 31, 55),   # the boundary case
        "verse:GEN.32.2": ("GEN", 32, 1),
    })

    v = store.get_verse("verse:GEN.32.1")
    assert (v.book, v.chapter, v.verse) == ("GEN", 32, 1), "witness numbering is unchanged"
    assert (v.kjv_book, v.kjv_chapter, v.kjv_verse) == ("GEN", 31, 55)

    assert store.id_for_kjv_reference("GEN", 31, 55) == "verse:GEN.32.1"
    assert store.id_for_kjv_reference("GEN", 32, 1) == "verse:GEN.32.2"
    assert store.id_for_kjv_reference("GEN", 99, 1) is None


def test_kjv_lookup_is_deterministic_when_two_verses_share_an_address(store):
    """Not a bijection: 5 KJV verses attach to two Hebrew verses each.

    Whichever row the engine happens to return first is not an answer, so the
    lookup orders by witness numbering and returns the start of the span.
    """
    store.insert_verses([
        _make_verse(verse_id="verse:NUM.25.19", book="NUM", chapter=25, verse=19),
        _make_verse(verse_id="verse:NUM.26.1", book="NUM", chapter=26, verse=1),
    ])
    store.set_kjv_addresses({
        "verse:NUM.25.19": ("NUM", 26, 1),
        "verse:NUM.26.1": ("NUM", 26, 1),
    })
    for _ in range(3):
        assert store.id_for_kjv_reference("NUM", 26, 1) == "verse:NUM.25.19"


def test_clearing_kjv_addresses_is_scoped_to_one_canon(store):
    """A reseed of one canon must not blank the other's addresses."""
    store.insert_verses([
        _make_verse(verse_id="verse:GEN.1.1", book="GEN", chapter=1, verse=1),
        _make_verse(verse_id="verse:MAT.1.1", book="MAT", chapter=1, verse=1,
                    canon=Canon.NT, language="grc"),
    ])
    store.set_kjv_addresses({
        "verse:GEN.1.1": ("GEN", 1, 1),
        "verse:MAT.1.1": ("MAT", 1, 1),
    })
    store.clear_kjv_addresses("tanakh")

    assert store.get_verse("verse:GEN.1.1").kjv_verse is None
    assert store.get_verse("verse:MAT.1.1").kjv_verse == 1


def test_verse_with_no_kjv_address_keeps_its_witness_numbering(store):
    """Psalms superscriptions have no KJV verse; the address stays null."""
    store.insert_verses([_make_verse(verse_id="verse:PSA.13.1", book="PSA", chapter=13, verse=1)])
    v = store.get_verse("verse:PSA.13.1")
    assert v.kjv_verse is None and v.kjv_chapter is None and v.kjv_book is None
    assert (v.book, v.chapter, v.verse) == ("PSA", 13, 1)


def test_chapter_grouping_follows_the_kjv_boundary(store):
    """/read groups by KJV chapter, so a verse crosses the boundary with it.

    Hebrew Genesis 32:1 is KJV Genesis 31:55. Grouped by witness numbering it
    opened chapter 32; grouped by the base text it closes chapter 31, where its
    text belongs. No gap and no duplicate across the boundary — which a
    count-only check would not catch, since the totals are the same either way.
    """
    store.insert_verses([
        _make_verse(verse_id="verse:GEN.31.54", book="GEN", chapter=31, verse=54),
        _make_verse(verse_id="verse:GEN.32.1", book="GEN", chapter=32, verse=1),
        _make_verse(verse_id="verse:GEN.32.2", book="GEN", chapter=32, verse=2),
        _make_verse(verse_id="verse:GEN.32.3", book="GEN", chapter=32, verse=3),
    ])
    store.set_kjv_addresses({
        "verse:GEN.31.54": ("GEN", 31, 54),
        "verse:GEN.32.1": ("GEN", 31, 55),   # crosses the boundary
        "verse:GEN.32.2": ("GEN", 32, 1),
        "verse:GEN.32.3": ("GEN", 32, 2),
    })

    ch31 = store.chapter_verses("GEN", 31)
    assert [r["verse"] for r in ch31] == [54, 55]
    assert ch31[-1]["id"] == "verse:GEN.32.1", "KJV 31:55 must close chapter 31"

    ch32 = store.chapter_verses("GEN", 32)
    assert [r["verse"] for r in ch32] == [1, 2], "chapter 32 starts at KJV 1"
    assert ch32[0]["id"] == "verse:GEN.32.2"

    # Every verse appears exactly once across the two chapters.
    ids = [r["id"] for r in ch31] + [r["id"] for r in ch32]
    assert len(ids) == len(set(ids)) == 4


def test_superscriptions_sort_ahead_of_kjv_verse_one(store):
    """A two-line superscription must not sort after the verse it precedes.

    Psalms 51, 52, 54 and 60 carry two superscription lines, neither of which
    has a KJV verse. Ordering by the KJV number with a fallback to the witness
    number would put the SECOND line after KJV 51:1; ordering by witness
    numbering keeps both ahead of it, which is safe because witness order never
    inverts KJV order.
    """
    store.insert_verses([
        _make_verse(verse_id=f"verse:PSA.51.{v}", book="PSA", chapter=51, verse=v)
        for v in (1, 2, 3, 4)
    ])
    store.set_kjv_addresses({
        "verse:PSA.51.3": ("PSA", 51, 1),
        "verse:PSA.51.4": ("PSA", 51, 2),
    })   # 51:1 and 51:2 are the superscription — no KJV verse

    listed = store.chapter_verses("PSA", 51)
    assert [r["id"] for r in listed] == [
        "verse:PSA.51.1", "verse:PSA.51.2", "verse:PSA.51.3", "verse:PSA.51.4",
    ]
    assert [r["verse"] for r in listed] == [None, None, 1, 2]
    assert [r["witness_verse"] for r in listed] == [1, 2, 3, 4]


def test_books_summary_counts_kjv_chapters(store):
    """chapter_count follows the KJV, since /read is grouped by it."""
    store.insert_verses([
        _make_verse(verse_id="verse:GEN.31.54", book="GEN", chapter=31, verse=54),
        _make_verse(verse_id="verse:GEN.32.1", book="GEN", chapter=32, verse=1),
    ])
    store.set_kjv_addresses({
        "verse:GEN.31.54": ("GEN", 31, 54),
        "verse:GEN.32.1": ("GEN", 31, 55),
    })
    gen = next(b for b in store.books_summary() if b["book"] == "GEN")
    assert gen["chapter_count"] == 31, "no KJV chapter 32 exists in this fixture"
    assert gen["verse_count"] == 2
