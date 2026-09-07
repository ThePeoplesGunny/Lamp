"""seed_graph.py must replace ONLY the entity layer.

Regression guard for the data-loss path described in scripts/seed_graph.py.
The script used to construct an empty GraphStore and save it over lamp.json,
erasing 31,172 verse nodes and 144 verse->verse QUOTES edges. Recovering those
meant re-running seed_verses.py, which (before the upsert fix in verse_store.py)
cascade-deleted 31,104 KJV translation rows.

Everything here runs against a tmp_path graph and a tmp_path seed dir. The live
lamp.json and verses.db are never opened.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lamp.graph.store import GraphStore  # noqa: E402
from lamp.models import Canon, Edge, EdgeType, Verse  # noqa: E402

SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "seed_graph.py"


def _load_seed_graph_module():
    """Import scripts/seed_graph.py by path — scripts/ is not a package."""
    spec = importlib.util.spec_from_file_location("_seed_graph_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_verse(verse_id, book, chapter, verse):
    return Verse(
        id=verse_id,
        book=book,
        chapter=chapter,
        verse=verse,
        canon=Canon.TANAKH,
        language="hbo",
        text_consonantal="test",
        text_pointed="test",
        text_cantillated="test",
        words=[],
        source="OSHB-WLC@test",
        source_tier=1,
    )


@pytest.fixture
def prepared(tmp_path):
    """A graph holding verse nodes, a verse->verse QUOTES edge, and stale entities.

    Also writes a minimal seed dir. Returns (graph_path, seed_dir).
    """
    graph_path = tmp_path / "lamp.json"
    # verse_db_path=None -> in-memory SQLite. No real database is touched.
    store = GraphStore(graph_path)
    store.load()

    store.add_verses([
        _make_verse("verse:GEN.2.7", "GEN", 2, 7),
        _make_verse("verse:GEN.5.1", "GEN", 5, 1),
        _make_verse("verse:PSA.110.1", "PSA", 110, 1),
    ])
    # A verse->verse edge, which has nothing to do with entities and must survive.
    store.add_edge(Edge(
        source="verse:PSA.110.1",
        target="verse:GEN.2.7",
        type=EdgeType.QUOTES,
        notes="synthetic test edge",
    ))

    # A stale entity that is NOT in the seed file — it must be gone afterwards.
    from lamp.models import Person
    store.add_person(Person(id="person:stale", name_english="Stale", sex="male"))
    store.add_edge(Edge(
        source="verse:GEN.2.7", target="person:stale", type=EdgeType.MENTIONS
    ))
    store.save()
    store.close()

    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / "persons.json").write_text(json.dumps({
        "persons": [
            {
                "id": "person:adam",
                "name_english": "Adam",
                "sex": "male",
                "scripture_refs": [
                    {"book": "GEN", "chapter": 2, "verse": 7},
                    {"book": "GEN", "chapter": 5, "verse": 1},
                ],
            },
            {
                "id": "person:eve",
                "name_english": "Eve",
                "sex": "female",
                "scripture_refs": [{"book": "GEN", "chapter": 2, "verse": 7}],
            },
        ],
        "relationships": [
            {"source": "person:adam", "target": "person:eve", "type": "wife_of"}
        ],
        "nations": [],
        "nation_links": [],
    }), encoding="utf-8")

    return graph_path, seed_dir


def _run(monkeypatch, graph_path, seed_dir):
    module = _load_seed_graph_module()
    monkeypatch.setattr(module, "GRAPH_FILE", graph_path)
    monkeypatch.setattr(module, "SEED_DIR", seed_dir)
    return module.main()


def test_entity_reseed_preserves_verse_nodes(monkeypatch, prepared):
    graph_path, seed_dir = prepared
    assert _run(monkeypatch, graph_path, seed_dir) == 0

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    verse_ids = {n["id"] for n in data["nodes"] if n.get("node_type") == "verse"}
    assert verse_ids == {"verse:GEN.2.7", "verse:GEN.5.1", "verse:PSA.110.1"}


def test_entity_reseed_preserves_verse_to_verse_edges(monkeypatch, prepared):
    graph_path, seed_dir = prepared
    assert _run(monkeypatch, graph_path, seed_dir) == 0

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    quotes = [e for e in data["edges"] if e.get("type") == "quotes"]
    assert len(quotes) == 1
    assert quotes[0]["source"] == "verse:PSA.110.1"
    assert quotes[0]["target"] == "verse:GEN.2.7"


def test_entity_reseed_replaces_stale_entities(monkeypatch, prepared):
    graph_path, seed_dir = prepared
    assert _run(monkeypatch, graph_path, seed_dir) == 0

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    persons = {n["id"] for n in data["nodes"] if n.get("node_type") == "person"}
    assert persons == {"person:adam", "person:eve"}
    assert "person:stale" not in persons
    # Edges incident to the removed entity go with it.
    assert not [e for e in data["edges"] if e["target"] == "person:stale"]


def test_entity_reseed_relinks_mentions_in_the_same_run(monkeypatch, prepared):
    """The relink is in-process. A printed 'now run seed_verse_links.py' is not
    a guarantee, so the MENTIONS edges must already be present after this run."""
    graph_path, seed_dir = prepared
    assert _run(monkeypatch, graph_path, seed_dir) == 0

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    mentions = {
        (e["source"], e["target"])
        for e in data["edges"]
        if e.get("type") == "mentions"
    }
    assert mentions == {
        ("verse:GEN.2.7", "person:adam"),
        ("verse:GEN.5.1", "person:adam"),
        ("verse:GEN.2.7", "person:eve"),
    }


def test_second_run_is_idempotent(monkeypatch, prepared):
    graph_path, seed_dir = prepared
    assert _run(monkeypatch, graph_path, seed_dir) == 0
    first = json.loads(graph_path.read_text(encoding="utf-8"))
    assert _run(monkeypatch, graph_path, seed_dir) == 0
    second = json.loads(graph_path.read_text(encoding="utf-8"))

    assert len(first["nodes"]) == len(second["nodes"])
    assert len(first["edges"]) == len(second["edges"])
