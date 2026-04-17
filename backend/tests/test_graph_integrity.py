"""Graph integrity tests — ensure the seed data is consistent and complete."""

import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lamp.config import SEED_DIR
from lamp.graph.store import GraphStore
from lamp.models import EdgeType, PARENTAL_EDGES
from lamp.ingest.genesis_genealogy import load_seed_data


@pytest.fixture(scope="module")
def store():
    """Load the seed data into a fresh graph store."""
    s = GraphStore()
    load_seed_data(SEED_DIR / "persons.json", s)
    return s


def test_graph_not_empty(store):
    stats = store.stats()
    assert stats["persons"] > 0
    assert stats["nations"] > 0
    assert stats["edges"] > 0


def test_all_persons_have_required_fields(store):
    for person in store.get_persons():
        assert person["id"].startswith("person:"), f"Bad ID: {person['id']}"
        assert person["name_english"], f"Missing name: {person['id']}"
        assert person["sex"] in ("male", "female"), f"Bad sex: {person['id']}"


def test_all_nations_have_required_fields(store):
    for nation in store.get_nations():
        assert nation["id"].startswith("nation:"), f"Bad ID: {nation['id']}"
        assert nation["name_english"], f"Missing name: {nation['id']}"


def test_no_orphan_person_nodes(store):
    """Every person in the OT genealogical lines should have at least one parent.

    Exceptions: root persons (Adam, Eve), persons whose parentage
    is not recorded in the text (wives, handmaids brought into the narrative
    without genealogical context), and NT persons (scoped out of
    parent-child edges in the current seed).
    """
    # Persons whose parentage is not recorded in Genesis
    unrecorded_parentage = {
        "person:adam", "person:eve", "person:naamah_noah",
        "person:sarah", "person:hagar", "person:keturah",
        "person:rebekah", "person:leah", "person:rachel",
        "person:bilhah", "person:zilpah",
    }
    nt_books = {
        "MAT", "MRK", "LUK", "JHN", "ACT",
        "ROM", "1CO", "2CO", "GAL", "EPH", "PHP", "COL",
        "1TH", "2TH", "1TI", "2TI", "TIT", "PHM",
        "HEB", "JAS", "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
    }
    for person in store.get_persons():
        pid = person["id"]
        if pid in unrecorded_parentage:
            continue
        refs = person.get("scripture_refs") or []
        if refs and all(r["book"] in nt_books for r in refs):
            continue  # NT person — parent-child edges not yet seeded
        parents = store.get_parents(pid)
        assert len(parents) > 0, f"Orphan person (no parents): {pid}"


def test_no_self_referential_edges(store):
    """No node should have an edge to itself."""
    for u, v, data in store.G.edges(data=True):
        assert u != v, f"Self-referential edge: {u} -> {v} ({data.get('type')})"


def test_no_cycles_in_parent_child(store):
    """Parent-child relationships should form a DAG (no cycles)."""
    import networkx as nx

    parent_child = nx.DiGraph()
    for u, v, data in store.G.edges(data=True):
        if data.get("type") in PARENTAL_EDGES:
            parent_child.add_edge(u, v)

    assert nx.is_directed_acyclic_graph(parent_child), "Cycle detected in parent-child graph"


def test_adam_is_root(store):
    """Adam should have no parents."""
    parents = store.get_parents("person:adam")
    assert len(parents) == 0


def test_noah_has_three_sons(store):
    children = store.get_children("person:noah")
    child_ids = {c["id"] for c in children}
    assert "person:shem" in child_ids
    assert "person:ham" in child_ids
    assert "person:japheth" in child_ids


def test_jacob_has_thirteen_children(store):
    """Jacob has 12 sons + Dinah = 13 children."""
    children = store.get_children("person:jacob")
    assert len(children) == 13, f"Expected 13 children, got {len(children)}: {[c['id'] for c in children]}"


def test_nation_links_point_to_valid_nodes(store):
    """Every nation link should connect a valid person to a valid nation."""
    for u, v, data in store.G.edges(data=True):
        if data.get("type") == EdgeType.ANCESTOR_OF_NATION:
            assert store.G.nodes[u].get("node_type") == "person", f"Nation link source not a person: {u}"
            assert store.G.nodes[v].get("node_type") == "nation", f"Nation link target not a nation: {v}"


def test_covenant_line_unbroken(store):
    """The covenant line from Adam to Jacob should be traceable."""
    covenant_line = [
        "person:adam", "person:seth", "person:enosh", "person:kenan",
        "person:mahalalel", "person:jared", "person:enoch", "person:methuselah",
        "person:lamech_seth", "person:noah", "person:shem", "person:arphaxad",
        "person:shelah", "person:eber", "person:peleg", "person:reu",
        "person:serug", "person:nahor", "person:terah", "person:abraham",
        "person:isaac", "person:jacob",
    ]
    for i in range(len(covenant_line) - 1):
        parent = covenant_line[i]
        child = covenant_line[i + 1]
        children = store.get_children(parent)
        child_ids = {c["id"] for c in children}
        assert child in child_ids, f"Covenant line break: {parent} -> {child}"


def test_tree_building(store):
    """The tree builder should produce valid output from Adam."""
    tree = store.build_genealogy_tree("person:adam", max_depth=2)
    assert len(tree["nodes"]) > 0
    assert len(tree["edges"]) > 0
    # Adam should be the first node
    assert tree["nodes"][0]["id"] == "person:adam"


def test_search(store):
    results = store.search("Noah")
    assert any(r["id"] == "person:noah" for r in results)

    results = store.search("H3290")  # Jacob's Strong's
    assert any(r["id"] == "person:jacob" for r in results)


# ── NT↔OT QUOTES seed integrity (Phase 2D-3) ──────────────────────────────

NT_BOOKS = {
    "MAT", "MRK", "LUK", "JHN", "ACT",
    "ROM", "1CO", "2CO", "GAL", "EPH", "PHP", "COL",
    "1TH", "2TH", "1TI", "2TI", "TIT", "PHM",
    "HEB", "JAS", "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
}


def _load_quotes():
    import json
    with open(SEED_DIR / "nt_ot_quotes.json", "r", encoding="utf-8") as f:
        return json.load(f)["quotes"]


def test_nt_ot_quotes_seed_format():
    quotes = _load_quotes()
    assert len(quotes) >= 50, f"Expected >= 50 curated quotes, got {len(quotes)}"
    for i, q in enumerate(quotes):
        assert "nt" in q and "ot" in q, f"Entry {i} missing nt/ot"
        for side in ("nt", "ot"):
            ref = q[side]
            assert isinstance(ref["book"], str) and len(ref["book"]) == 3
            assert isinstance(ref["chapter"], int) and ref["chapter"] > 0
            assert isinstance(ref["verse"], int) and ref["verse"] > 0


def test_nt_ot_quotes_direction():
    """QUOTES edges must point NT → OT, never reverse."""
    quotes = _load_quotes()
    for q in quotes:
        assert q["nt"]["book"] in NT_BOOKS, f"NT source book not in NT canon: {q['nt']}"
        assert q["ot"]["book"] not in NT_BOOKS, f"OT target book is in NT canon: {q['ot']}"
