"""Mixed-canon tests — Hebrew and Greek verses coexist in GraphStore + VerseStore."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lamp.graph.store import GraphStore
from lamp.models import Canon, Edge, EdgeType, Verse, VerseWord


def _hebrew_verse(vid: str, book: str, chapter: int, verse: int) -> Verse:
    return Verse(
        id=vid,
        book=book,
        chapter=chapter,
        verse=verse,
        canon=Canon.TANAKH,
        language="hbo",
        text_canonical="בְּרֵאשִׁ֖ית",
        text_consonantal="בראשית",
        text_pointed="בְּרֵאשִׁית",
        text_cantillated="בְּרֵאשִׁ֖ית",
        words=[VerseWord(
            position=1,
            text_canonical="בְּרֵאשִׁ֖ית",
            text_consonantal="בראשית",
            text_pointed="בְּרֵאשִׁית",
            text_cantillated="בְּרֵאשִׁ֖ית",
            lemma="b/7225",
            strongs="7225",
            morph_code="HR/Ncfsa",
        )],
        source="OSHB-WLC@test",
        source_tier=1,
    )


def _greek_verse(vid: str, book: str, chapter: int, verse: int) -> Verse:
    return Verse(
        id=vid,
        book=book,
        chapter=chapter,
        verse=verse,
        canon=Canon.NT,
        language="grc",
        text_canonical="Βίβλος",
        text_accented="Βίβλος",
        text_plain="βιβλος",
        words=[VerseWord(
            position=1,
            text_canonical="Βίβλος",
            text_accented="Βίβλος",
            text_plain="βιβλος",
            lemma="βίβλος",
            morph_code="GN-----NSF-",
        )],
        source="MorphGNT-SBLGNT@test",
        source_tier=1,
    )


@pytest.fixture
def store():
    s = GraphStore(graph_path=None, verse_db_path=None)
    s.load()
    yield s
    s.close()


def test_hebrew_and_greek_coexist(store):
    store.add_verses([
        _hebrew_verse("verse:GEN.1.1", "GEN", 1, 1),
        _greek_verse("verse:MAT.1.1", "MAT", 1, 1),
    ])
    hebrew = store.get_verse("verse:GEN.1.1")
    greek = store.get_verse("verse:MAT.1.1")

    # Hebrew verse has Hebrew fields populated, Greek fields empty
    assert hebrew.text_cantillated != ""
    assert hebrew.text_plain == ""
    assert hebrew.text_accented == ""
    assert hebrew.language == "hbo"
    assert hebrew.canon == Canon.TANAKH

    # Greek verse has Greek fields populated, Hebrew fields empty
    assert greek.text_accented != ""
    assert greek.text_cantillated == ""
    assert greek.text_pointed == ""
    assert greek.text_consonantal == ""
    assert greek.language == "grc"
    assert greek.canon == Canon.NT

    # Both have text_canonical populated (the language-agnostic read form)
    assert hebrew.text_canonical != ""
    assert greek.text_canonical != ""


def test_cross_canon_quotes_edge(store):
    """NT quoting OT is the classic cross-canon analytical operation.

    Model Mat 1:23 quoting Isa 7:14 via a QUOTES edge and confirm traversal.
    """
    store.add_verses([
        _hebrew_verse("verse:ISA.7.14", "ISA", 7, 14),
        _greek_verse("verse:MAT.1.23", "MAT", 1, 23),
    ])
    store.add_edge(Edge(
        source="verse:MAT.1.23",
        target="verse:ISA.7.14",
        type=EdgeType.QUOTES,
    ))

    # From the NT side: which OT verse does Matt 1:23 quote?
    out = list(store.G.out_edges("verse:MAT.1.23", data=True))
    quotes = [(tgt, d) for _, tgt, d in out if d.get("type") == EdgeType.QUOTES]
    assert len(quotes) == 1
    assert quotes[0][0] == "verse:ISA.7.14"

    # From the OT side: what NT verses quote Isa 7:14?
    quoted_by = [src for src, _, d in store.G.in_edges("verse:ISA.7.14", data=True)
                 if d.get("type") == EdgeType.QUOTES]
    assert quoted_by == ["verse:MAT.1.23"]


def test_canon_filter_via_graph_node_attrs(store):
    store.add_verses([
        _hebrew_verse("verse:GEN.1.1", "GEN", 1, 1),
        _hebrew_verse("verse:EXO.1.1", "EXO", 1, 1),
        _greek_verse("verse:MAT.1.1", "MAT", 1, 1),
        _greek_verse("verse:JHN.3.16", "JHN", 3, 16),
    ])
    # Filter by canon using graph node metadata (no SQLite hit)
    tanakh = [n for n, d in store.G.nodes(data=True)
              if d.get("node_type") == "verse" and d.get("canon") == "tanakh"]
    nt = [n for n, d in store.G.nodes(data=True)
          if d.get("node_type") == "verse" and d.get("canon") == "nt"]
    assert sorted(tanakh) == ["verse:EXO.1.1", "verse:GEN.1.1"]
    assert sorted(nt) == ["verse:JHN.3.16", "verse:MAT.1.1"]


def test_language_on_graph_node(store):
    store.add_verses([
        _hebrew_verse("verse:GEN.1.1", "GEN", 1, 1),
        _greek_verse("verse:MAT.1.1", "MAT", 1, 1),
    ])
    assert store.G.nodes["verse:GEN.1.1"]["language"] == "hbo"
    assert store.G.nodes["verse:MAT.1.1"]["language"] == "grc"
