"""GraphStore verse operations — add_verses, get_verse, edge traversals."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lamp.graph.store import GraphStore
from lamp.models import Canon, Edge, EdgeType, Person, Place, Verse, VerseWord


def _verse(vid: str, book: str, chapter: int, verse: int, **kw) -> Verse:
    return Verse(
        id=vid,
        book=book,
        chapter=chapter,
        verse=verse,
        canon=Canon.TANAKH,
        language="hbo",
        text_consonantal="בראשית",
        text_pointed="בְּרֵאשִׁית",
        text_cantillated="בְּרֵאשִׁ֖ית",
        words=[VerseWord(
            position=1,
            text_consonantal="בראשית",
            text_pointed="בְּרֵאשִׁית",
            text_cantillated="בְּרֵאשִׁ֖ית",
            lemma="b/7225",
            strongs="7225",
        )],
        source="OSHB-WLC@test",
        source_tier=1,
        **kw,
    )


@pytest.fixture
def store():
    s = GraphStore(graph_path=None, verse_db_path=None)
    s.load()
    yield s
    s.close()


def test_add_verses_populates_both_stores(store):
    verses = [_verse("verse:GEN.1.1", "GEN", 1, 1), _verse("verse:GEN.1.2", "GEN", 1, 2)]
    count = store.add_verses(verses)
    assert count == 2
    assert store.verses.count_verses() == 2
    assert "verse:GEN.1.1" in store.G
    assert store.G.nodes["verse:GEN.1.1"]["node_type"] == "verse"
    assert store.G.nodes["verse:GEN.1.1"]["canon"] == "tanakh"


def test_graph_node_holds_minimal_metadata_only(store):
    store.add_verses([_verse("verse:GEN.1.1", "GEN", 1, 1, parashah_marker="pe")])
    node_data = store.G.nodes["verse:GEN.1.1"]
    # Expected minimal metadata on graph node
    assert node_data["book"] == "GEN"
    assert node_data["chapter"] == 1
    assert node_data["verse"] == 1
    assert node_data["parashah_marker"] == "pe"
    # Text layers must NOT be on graph node — they live in SQLite
    assert "text_cantillated" not in node_data
    assert "text_pointed" not in node_data
    assert "words" not in node_data


def test_get_verse_returns_full_payload(store):
    original = _verse("verse:GEN.1.1", "GEN", 1, 1)
    store.add_verses([original])
    fetched = store.get_verse("verse:GEN.1.1")
    assert fetched is not None
    assert fetched.text_cantillated == original.text_cantillated
    assert len(fetched.words) == 1
    assert fetched.words[0].strongs == "7225"


def test_get_verse_unknown_returns_none(store):
    assert store.get_verse("verse:GEN.99.99") is None


def test_get_verses_mentioning(store):
    store.add_person(Person(id="person:abraham", name_english="Abraham", sex="male"))
    store.add_verses([
        _verse("verse:GEN.12.1", "GEN", 12, 1),
        _verse("verse:GEN.12.2", "GEN", 12, 2),
        _verse("verse:GEN.17.5", "GEN", 17, 5),
    ])
    for vid in ("verse:GEN.12.1", "verse:GEN.17.5"):
        store.add_edge(Edge(source=vid, target="person:abraham", type=EdgeType.MENTIONS))

    mentioning = store.get_verses_mentioning("person:abraham")
    ids = [v["id"] for v in mentioning]
    assert ids == ["verse:GEN.12.1", "verse:GEN.17.5"]


def test_get_verses_mentioning_sorted_by_reference(store):
    """Returned verses must be sorted by book, chapter, verse for stable UI output."""
    store.add_place(Place(id="place:eden", name_english="Eden"))
    store.add_verses([
        _verse("verse:GEN.3.23", "GEN", 3, 23),
        _verse("verse:GEN.2.8", "GEN", 2, 8),
        _verse("verse:GEN.2.10", "GEN", 2, 10),
    ])
    for vid in ("verse:GEN.3.23", "verse:GEN.2.8", "verse:GEN.2.10"):
        store.add_edge(Edge(source=vid, target="place:eden", type=EdgeType.MENTIONS))

    mentioning = store.get_verses_mentioning("place:eden")
    ids = [v["id"] for v in mentioning]
    assert ids == ["verse:GEN.2.8", "verse:GEN.2.10", "verse:GEN.3.23"]


def test_get_mentions(store):
    store.add_person(Person(id="person:abraham", name_english="Abraham", sex="male"))
    store.add_place(Place(id="place:hebron", name_english="Hebron"))
    store.add_verses([_verse("verse:GEN.23.2", "GEN", 23, 2)])
    store.add_edge(Edge(source="verse:GEN.23.2", target="person:abraham", type=EdgeType.MENTIONS))
    store.add_edge(Edge(source="verse:GEN.23.2", target="place:hebron", type=EdgeType.MENTIONS))

    mentions = store.get_mentions("verse:GEN.23.2")
    target_ids = {m["id"] for m in mentions}
    assert target_ids == {"person:abraham", "place:hebron"}


def test_stats_counts_verses_separately(store):
    store.add_person(Person(id="person:adam", name_english="Adam", sex="male"))
    store.add_verses([
        _verse("verse:GEN.1.1", "GEN", 1, 1),
        _verse("verse:GEN.1.2", "GEN", 1, 2),
    ])
    stats = store.stats()
    assert stats["persons"] == 1
    assert stats["verses"] == 2
    assert stats["total_nodes"] == 3


def test_new_edge_types_roundtrip(store):
    """Every new verse-edge type must serialize into the graph without error."""
    store.add_person(Person(id="person:jesus", name_english="Jesus", sex="male"))
    store.add_place(Place(id="place:nazareth", name_english="Nazareth"))
    store.add_verses([
        _verse("verse:GEN.1.1", "GEN", 1, 1),
        _verse("verse:GEN.1.2", "GEN", 1, 2),
    ])

    all_new_types = [
        EdgeType.MENTIONS,
        EdgeType.SPOKEN_BY,
        EdgeType.ADDRESSED_TO,
        EdgeType.SET_IN,
        EdgeType.QUOTES,
        EdgeType.ALLUDES_TO,
        EdgeType.PARALLEL_TO,
    ]
    # All non-verse→verse types point at an entity
    store.add_edge(Edge(source="verse:GEN.1.1", target="person:jesus", type=EdgeType.MENTIONS))
    store.add_edge(Edge(source="verse:GEN.1.1", target="person:jesus", type=EdgeType.SPOKEN_BY))
    store.add_edge(Edge(source="verse:GEN.1.1", target="person:jesus", type=EdgeType.ADDRESSED_TO))
    store.add_edge(Edge(source="verse:GEN.1.1", target="place:nazareth", type=EdgeType.SET_IN))
    # Verse→verse types
    store.add_edge(Edge(source="verse:GEN.1.2", target="verse:GEN.1.1", type=EdgeType.QUOTES))
    store.add_edge(Edge(source="verse:GEN.1.2", target="verse:GEN.1.1", type=EdgeType.ALLUDES_TO))
    store.add_edge(Edge(source="verse:GEN.1.2", target="verse:GEN.1.1", type=EdgeType.PARALLEL_TO))

    # All present in the graph
    stored_types = {data["type"] for _, _, data in store.G.edges(data=True)}
    for t in all_new_types:
        assert t in stored_types
