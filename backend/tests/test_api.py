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
from lamp.api.verses import init_store as init_verse_store
from lamp.ingest.genesis_genealogy import load_seed_data
from lamp.models import Canon, Edge, EdgeType, Verse, VerseWord


def _test_hebrew_verse(verse_id: str, book: str, chapter: int, verse: int) -> Verse:
    return Verse(
        id=verse_id,
        book=book,
        chapter=chapter,
        verse=verse,
        canon=Canon.TANAKH,
        language="hbo",
        text_canonical="בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים",
        text_consonantal="בראשית ברא אלהים",
        text_pointed="בְּרֵאשִׁית בָּרָא אֱלֹהִים",
        text_cantillated="בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים",
        words=[
            VerseWord(
                position=1,
                text_canonical="בְּרֵאשִׁ֖ית",
                text_consonantal="בראשית",
                text_pointed="בְּרֵאשִׁית",
                text_cantillated="בְּרֵאשִׁ֖ית",
                lemma="b/7225",
                strongs="7225",
                morph_code="HR/Ncfsa",
            ),
        ],
        source="OSHB-WLC@test",
        source_tier=1,
    )


def _test_greek_verse(verse_id: str, book: str, chapter: int, verse: int) -> Verse:
    return Verse(
        id=verse_id,
        book=book,
        chapter=chapter,
        verse=verse,
        canon=Canon.NT,
        language="grc",
        text_canonical="Βίβλος γενέσεως",
        text_accented="Βίβλος γενέσεως",
        text_plain="βιβλος γενεσεως",
        words=[
            VerseWord(
                position=1,
                text_canonical="Βίβλος",
                text_accented="Βίβλος",
                text_plain="βιβλος",
                lemma="βίβλος",
                morph_code="GN-----NSF-",
            ),
        ],
        source="MorphGNT-SBLGNT@test",
        source_tier=1,
    )


@pytest.fixture(scope="module", autouse=True)
def setup_store():
    """Load seed data + a minimal verse corpus for API tests."""
    store = GraphStore()
    store.load()  # connects in-memory VerseStore
    load_seed_data(SEED_DIR / "persons.json", store)

    # Minimal verse corpus — three Hebrew (for prev/next nav), one Greek
    store.add_verses([
        _test_hebrew_verse("verse:GEN.1.1", "GEN", 1, 1),
        _test_hebrew_verse("verse:GEN.1.2", "GEN", 1, 2),
        _test_hebrew_verse("verse:GEN.2.1", "GEN", 2, 1),
        _test_greek_verse("verse:MAT.1.1", "MAT", 1, 1),
    ])
    # Adam is mentioned in Gen 1:1
    store.add_edge(Edge(
        source="verse:GEN.1.1",
        target="person:adam",
        type=EdgeType.MENTIONS,
    ))

    init_store(store)
    init_verse_store(store)
    yield
    store.close()


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


# ── Verse API ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_verse_hebrew(client):
    r = await client.get(f"{API_PREFIX}/verse/verse:GEN.1.1")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "verse:GEN.1.1"
    assert data["reference"] == "Genesis 1:1"
    assert data["canon"] == "tanakh"
    assert data["language"] == "hbo"
    assert data["text_cantillated"] != ""
    assert data["text_pointed"] != ""
    assert data["text_consonantal"] != ""
    assert data["text_plain"] == ""
    assert data["text_accented"] == ""
    assert data["text_canonical"] == data["text_cantillated"]
    assert len(data["words"]) >= 1
    assert data["words"][0]["lemma"]
    assert data["words"][0]["morph_code"]


@pytest.mark.anyio
async def test_get_verse_greek(client):
    r = await client.get(f"{API_PREFIX}/verse/verse:MAT.1.1")
    assert r.status_code == 200
    data = r.json()
    assert data["canon"] == "nt"
    assert data["language"] == "grc"
    assert data["text_accented"] != ""
    assert data["text_plain"] != ""
    assert data["text_cantillated"] == ""
    assert data["text_canonical"] == data["text_accented"]
    assert data["words"][0]["morph_code"].startswith("G")


@pytest.mark.anyio
async def test_get_verse_accepts_bare_reference(client):
    """URL-friendly form without 'verse:' prefix."""
    r = await client.get(f"{API_PREFIX}/verse/GEN.1.1")
    assert r.status_code == 200
    assert r.json()["id"] == "verse:GEN.1.1"


@pytest.mark.anyio
async def test_get_verse_404(client):
    r = await client.get(f"{API_PREFIX}/verse/verse:GEN.999.999")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_verse_prev_next(client):
    r = await client.get(f"{API_PREFIX}/verse/verse:GEN.1.1")
    data = r.json()
    assert data["prev_id"] is None
    assert data["next_id"] == "verse:GEN.1.2"

    r = await client.get(f"{API_PREFIX}/verse/verse:GEN.1.2")
    data = r.json()
    assert data["prev_id"] == "verse:GEN.1.1"
    assert data["next_id"] == "verse:GEN.2.1"

    r = await client.get(f"{API_PREFIX}/verse/verse:GEN.2.1")
    data = r.json()
    assert data["prev_id"] == "verse:GEN.1.2"
    assert data["next_id"] is None


@pytest.mark.anyio
async def test_verse_mentions_populated(client):
    r = await client.get(f"{API_PREFIX}/verse/verse:GEN.1.1")
    data = r.json()
    mentioned_ids = [m["id"] for m in data["mentions"]]
    assert "person:adam" in mentioned_ids


@pytest.mark.anyio
async def test_verses_mentioning_person(client):
    r = await client.get(f"{API_PREFIX}/verse/mentioning/person:adam")
    assert r.status_code == 200
    data = r.json()
    verse_ids = [v["id"] for v in data]
    assert "verse:GEN.1.1" in verse_ids
    adam_verse = next(v for v in data if v["id"] == "verse:GEN.1.1")
    assert adam_verse["reference"] == "Genesis 1:1"


@pytest.mark.anyio
async def test_verses_mentioning_unknown_404(client):
    r = await client.get(f"{API_PREFIX}/verse/mentioning/person:nonexistent")
    assert r.status_code == 404
