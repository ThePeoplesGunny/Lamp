"""API endpoint tests."""

import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).parent.parent))

from lamp.main import app
from lamp.config import SEED_DIR, API_PREFIX
from lamp.graph.store import GraphStore
from lamp.api.genealogy import init_store
from lamp.ingest.genesis_genealogy import load_seed_data


@pytest.fixture(scope="module", autouse=True)
def setup_store():
    """Load seed data into the graph store for all tests."""
    store = GraphStore()
    load_seed_data(SEED_DIR / "persons.json", store)
    init_store(store)


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_health(client):
    r = await client.get(f"{API_PREFIX}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.anyio
async def test_stats(client):
    r = await client.get(f"{API_PREFIX}/genealogy/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["persons"] > 100
    assert data["nations"] > 10


@pytest.mark.anyio
async def test_get_tree_default(client):
    r = await client.get(f"{API_PREFIX}/genealogy/tree")
    assert r.status_code == 200
    data = r.json()
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0
    assert data["nodes"][0]["id"] == "person:adam"


@pytest.mark.anyio
async def test_get_tree_with_root(client):
    r = await client.get(f"{API_PREFIX}/genealogy/tree?root=person:noah&depth=1")
    assert r.status_code == 200
    data = r.json()
    node_ids = {n["id"] for n in data["nodes"]}
    assert "person:noah" in node_ids
    assert "person:shem" in node_ids


@pytest.mark.anyio
async def test_get_tree_by_line(client):
    r = await client.get(f"{API_PREFIX}/genealogy/tree?line=ham&depth=1")
    assert r.status_code == 200
    data = r.json()
    assert data["nodes"][0]["id"] == "person:ham"


@pytest.mark.anyio
async def test_get_tree_not_found(client):
    r = await client.get(f"{API_PREFIX}/genealogy/tree?root=person:nobody")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_get_person(client):
    r = await client.get(f"{API_PREFIX}/genealogy/person/person:abraham")
    assert r.status_code == 200
    data = r.json()
    assert data["name_english"] == "Abraham"
    assert data["name_hebrew"] == "אַבְרָהָם"
    assert data["strongs"] == "H85"
    assert len(data["children"]) >= 2  # Ishmael, Isaac
    assert len(data["spouses"]) >= 2  # Sarah, Hagar, Keturah


@pytest.mark.anyio
async def test_get_person_not_found(client):
    r = await client.get(f"{API_PREFIX}/genealogy/person/person:nobody")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_search(client):
    r = await client.get(f"{API_PREFIX}/genealogy/search?q=Noah")
    assert r.status_code == 200
    data = r.json()
    assert any(d["id"] == "person:noah" for d in data)


@pytest.mark.anyio
async def test_search_by_strongs(client):
    r = await client.get(f"{API_PREFIX}/genealogy/search?q=H3290")
    assert r.status_code == 200
    data = r.json()
    assert any(d["id"] == "person:jacob" for d in data)


@pytest.mark.anyio
async def test_search_by_type(client):
    r = await client.get(f"{API_PREFIX}/genealogy/search?q=israel&type=nation")
    assert r.status_code == 200
    data = r.json()
    assert all(d["node_type"] == "nation" for d in data)


@pytest.mark.anyio
async def test_lineage_ancestors(client):
    r = await client.get(f"{API_PREFIX}/genealogy/lineage/person:jacob?direction=ancestors")
    assert r.status_code == 200
    data = r.json()
    ancestor_ids = {a["id"] for a in data["ancestors"]}
    assert "person:isaac" in ancestor_ids
    assert "person:abraham" in ancestor_ids
    assert "person:adam" in ancestor_ids


@pytest.mark.anyio
async def test_lineage_descendants(client):
    r = await client.get(f"{API_PREFIX}/genealogy/lineage/person:noah?direction=descendants")
    assert r.status_code == 200
    data = r.json()
    assert len(data["descendants"]) > 50  # Noah has many descendants in seed data


@pytest.mark.anyio
async def test_nations(client):
    r = await client.get(f"{API_PREFIX}/genealogy/nations")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 18
    # Check Israel is present with Jacob as ancestor
    israel = next(n for n in data if n["id"] == "nation:israel")
    assert israel["eponymous_ancestor"]["id"] == "person:jacob"
