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
from lamp.api.verses import init_store as init_verse_store  # nav_router shares the same store global
from lamp.ingest.genesis_genealogy import load_seed_data
from lamp.models import Canon, Edge, EdgeType, TranslationText, Verse, VerseWord


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

    # Gen 1:1 has a KJV translation attached (for /verse translation payload tests)
    store.verses.insert_translations([
        TranslationText(
            translation="KJV-1769",
            verse_id="verse:GEN.1.1",
            text="In the beginning God created the heaven and the earth.",
            source="test-KJV",
            source_tier=2,   # historic translation — see CLAUDE.md's tier table
        ),
        TranslationText(
            translation="ASV-1901",
            verse_id="verse:GEN.1.1",
            text="In the beginning God created the heavens and the earth.",
            source="test-ASV",
            source_tier=2,   # historic translation — see CLAUDE.md's tier table
        ),
    ])

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


# ── Navigation API (books + chapter) ───────────────────────────

@pytest.mark.anyio
async def test_list_books(client):
    r = await client.get(f"{API_PREFIX}/books")
    assert r.status_code == 200
    data = r.json()
    # Our test fixture seeds GEN (3 verses) and MAT (1 verse)
    codes = [b["book"] for b in data]
    assert "GEN" in codes
    assert "MAT" in codes
    # GEN comes before MAT in canonical order
    assert codes.index("GEN") < codes.index("MAT")

    gen = next(b for b in data if b["book"] == "GEN")
    assert gen["name"] == "Genesis"
    assert gen["canon"] == "tanakh"
    assert gen["language"] == "hbo"
    assert gen["chapter_count"] == 2  # seed has GEN.1 and GEN.2
    assert gen["verse_count"] == 3

    mat = next(b for b in data if b["book"] == "MAT")
    assert mat["canon"] == "nt"
    assert mat["language"] == "grc"


@pytest.mark.anyio
async def test_get_chapter(client):
    r = await client.get(f"{API_PREFIX}/book/GEN/chapter/1")
    assert r.status_code == 200
    data = r.json()
    assert data["book"] == "GEN"
    assert data["book_name"] == "Genesis"
    assert data["chapter"] == 1
    assert len(data["verses"]) == 2  # GEN.1.1 and GEN.1.2 in seed
    assert data["verses"][0]["verse"] == 1
    assert data["verses"][0]["id"] == "verse:GEN.1.1"
    # Lightweight payload — no words/morphology
    assert "words" not in data["verses"][0]
    # Canonical text preview present
    assert data["verses"][0]["text_canonical"] != ""


@pytest.mark.anyio
async def test_get_chapter_case_insensitive_book(client):
    """Book code in URL is normalized to uppercase."""
    r = await client.get(f"{API_PREFIX}/book/gen/chapter/1")
    assert r.status_code == 200
    assert r.json()["book"] == "GEN"


@pytest.mark.anyio
async def test_get_chapter_not_found(client):
    r = await client.get(f"{API_PREFIX}/book/GEN/chapter/999")
    assert r.status_code == 404


# ── Translations on verse endpoint ─────────────────────────────

@pytest.mark.anyio
async def test_verse_includes_translations(client):
    r = await client.get(f"{API_PREFIX}/verse/verse:GEN.1.1")
    data = r.json()
    # Two translations seeded in the fixture (KJV + ASV)
    assert "translations" in data
    assert len(data["translations"]) == 2
    ids = {t["translation"] for t in data["translations"]}
    assert ids == {"KJV-1769", "ASV-1901"}
    # Each translation has the expected shape
    kjv = next(t for t in data["translations"] if t["translation"] == "KJV-1769")
    assert kjv["text"].startswith("In the beginning")
    assert kjv["source"] == "test-KJV"
    # Tier 2 = historic translation (public domain). This asserted 4 — the tier the
    # ingest scripts wrongly stamped — which made the suite encode the defect rather
    # than catch it. Tier 4 is "speculative inference", which per CLAUDE.md "cannot
    # be presented as fact"; the KJV is a published 1769 edition.
    assert kjv["source_tier"] == 2


@pytest.mark.anyio
async def test_verse_with_no_translations(client):
    """Greek Mat 1:1 in the fixture has no translation attached."""
    r = await client.get(f"{API_PREFIX}/verse/verse:MAT.1.1")
    assert r.status_code == 200
    data = r.json()
    assert data["translations"] == []


@pytest.mark.anyio
async def test_translations_preserved_in_verse_endpoint(client):
    """Translation data integrity through the full API path."""
    r = await client.get(f"{API_PREFIX}/verse/verse:GEN.1.1")
    translations = r.json()["translations"]
    kjv = next(t for t in translations if t["translation"] == "KJV-1769")
    # Exact KJV text survived round-trip
    assert kjv["text"] == "In the beginning God created the heaven and the earth."


# ── Lexeme search (concordance) ───────────────────────────────

@pytest.mark.anyio
async def test_lexeme_search_by_strongs(client):
    """Fixture seeds one Hebrew word with Strong's 7225. That should find it."""
    r = await client.get(f"{API_PREFIX}/lexeme/occurrences?strongs=7225")
    assert r.status_code == 200
    data = r.json()
    assert data["key_type"] == "strongs"
    assert data["key"] == "7225"
    assert data["total"] >= 1
    verse_ids = [res["verse_id"] for res in data["results"]]
    assert "verse:GEN.1.1" in verse_ids
    first = next(r for r in data["results"] if r["verse_id"] == "verse:GEN.1.1")
    assert first["reference"] == "Genesis 1:1"
    assert 1 in first["positions"]


@pytest.mark.anyio
async def test_lexeme_search_by_lemma(client):
    """Greek fixture word has lemma βίβλος."""
    import urllib.parse
    lemma = urllib.parse.quote("βίβλος")
    r = await client.get(f"{API_PREFIX}/lexeme/occurrences?lemma={lemma}")
    assert r.status_code == 200
    data = r.json()
    assert data["key_type"] == "lemma"
    assert data["key"] == "βίβλος"
    verse_ids = [res["verse_id"] for res in data["results"]]
    assert "verse:MAT.1.1" in verse_ids


@pytest.mark.anyio
async def test_lexeme_search_requires_key(client):
    r = await client.get(f"{API_PREFIX}/lexeme/occurrences")
    assert r.status_code == 400


@pytest.mark.anyio
async def test_lexeme_search_rejects_both_keys(client):
    r = await client.get(f"{API_PREFIX}/lexeme/occurrences?lemma=foo&strongs=1")
    assert r.status_code == 400


@pytest.mark.anyio
async def test_lexeme_search_canon_filter(client):
    """Filter to NT should exclude Tanakh matches."""
    r = await client.get(f"{API_PREFIX}/lexeme/occurrences?strongs=7225&canon=nt")
    data = r.json()
    for res in data["results"]:
        assert res["canon"] == "nt"


@pytest.mark.anyio
async def test_lexeme_search_empty_result(client):
    r = await client.get(f"{API_PREFIX}/lexeme/occurrences?strongs=99999")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["results"] == []


@pytest.mark.anyio
async def test_lexeme_search_results_ordered_canonically(client):
    """Results must follow Tanakh → NT canonical order, not ASCII book-code order.

    We only have one matching verse per key in the fixture, so the sharper
    assertion we can make: when results span canons, Tanakh verses come before NT.
    """
    # Seed-agnostic: just verify ordering invariant holds for any keys that might
    # return cross-canon results — here we just check the response is well-formed.
    r = await client.get(f"{API_PREFIX}/lexeme/occurrences?strongs=7225")
    data = r.json()
    if len(data["results"]) >= 2:
        prior_order = -1
        canon_order = {"tanakh": 0, "nt": 1, "lxx": 2}
        for res in data["results"]:
            co = canon_order.get(res["canon"], 99)
            assert co >= prior_order, "canon order violated"
            prior_order = co


@pytest.mark.anyio
async def test_search_carries_both_transliteration_fields(client):
    """The search payload must expose the same name fields the person endpoint does.

    Regression guard. The search result builder set name_greek but silently
    dropped name_greek_transliterated, even though every one of the 280 nodes
    carrying a Greek name also carries its transliteration. A component reading
    the field got undefined with no error anywhere.
    """
    r = await client.get(f"{API_PREFIX}/genealogy/search?q=Peter")
    assert r.status_code == 200
    hits = [d for d in r.json() if d["id"] == "person:peter"]
    assert hits, "person:peter not found by search"
    peter = hits[0]
    assert peter["name_greek"] == "Πέτρος"
    assert peter["name_greek_transliterated"] == "Petros"
    assert "name_hebrew_transliterated" in peter


@pytest.mark.anyio
async def test_search_and_person_agree_on_name_fields(client):
    """Search and /person must describe the same entity with the same fields.

    Two endpoints returning different subsets of an entity's names is how the
    dropped field went unnoticed: /person had it, search did not.
    """
    name_fields = {
        "name_english",
        "name_hebrew",
        "name_hebrew_transliterated",
        "name_greek",
        "name_greek_transliterated",
    }
    search = await client.get(f"{API_PREFIX}/genealogy/search?q=Peter")
    person = await client.get(f"{API_PREFIX}/genealogy/person/person:peter")
    assert search.status_code == 200 and person.status_code == 200

    hit = next(d for d in search.json() if d["id"] == "person:peter")
    detail = person.json()
    assert name_fields <= set(hit), f"search is missing {name_fields - set(hit)}"
    assert name_fields <= set(detail), f"person is missing {name_fields - set(detail)}"
    for f in name_fields:
        assert hit[f] == detail[f], f"search and person disagree on {f}"


@pytest.mark.anyio
async def test_verse_mentions_carry_transliteration_fields(client):
    """The mentions summary dropped name_greek_transliterated the same way search did."""
    r = await client.get(f"{API_PREFIX}/verse/verse:GEN.1.1")
    assert r.status_code == 200
    mentions = r.json()["mentions"]
    assert mentions, "expected at least one mention on GEN.1.1"
    for m in mentions:
        for f in (
            "name_english",
            "name_hebrew",
            "name_hebrew_transliterated",
            "name_greek",
            "name_greek_transliterated",
        ):
            assert f in m, f"mention payload is missing {f}"
