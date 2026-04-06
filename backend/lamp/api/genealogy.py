"""Genealogy API endpoints."""

from fastapi import APIRouter, HTTPException, Query

from lamp.graph.store import GraphStore

router = APIRouter(prefix="/genealogy", tags=["genealogy"])

# GraphStore instance — injected by main.py at startup
_store: GraphStore | None = None


def init_store(store: GraphStore) -> None:
    global _store
    _store = store


def get_store() -> GraphStore:
    if _store is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    return _store


@router.get("/tree")
def get_tree(
    root: str = Query("person:adam", description="Root node ID"),
    depth: int | None = Query(None, description="Max depth (generations)"),
    line: str | None = Query(None, description="Filter to line: shem, ham, or japheth"),
):
    """Get a genealogy tree for visualization."""
    store = get_store()

    # If filtering by line, use the son of Noah as root
    if line:
        line_map = {
            "shem": "person:shem",
            "ham": "person:ham",
            "japheth": "person:japheth",
        }
        root = line_map.get(line.lower(), root)

    if store.get_node(root) is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {root}")

    tree = store.build_genealogy_tree(root, max_depth=depth)
    return tree


@router.get("/person/{person_id:path}")
def get_person(person_id: str):
    """Get full detail for a person."""
    store = get_store()
    node = store.get_node(person_id)
    if node is None or node.get("node_type") != "person":
        raise HTTPException(status_code=404, detail=f"Person not found: {person_id}")

    parents = store.get_parents(person_id)
    children = store.get_children(person_id)
    spouses = store.get_spouses(person_id)
    nations = store.get_nations_for_person(person_id)

    # Clean internal fields from related entries
    def summarize(entries: list[dict]) -> list[dict]:
        return [
            {
                "id": e["id"],
                "name_english": e.get("name_english", ""),
                "name_hebrew": e.get("name_hebrew"),
                "sex": e.get("sex"),
                "relationship": e.get("_relationship"),
                "birth_order": e.get("_edge", {}).get("birth_order") if "_edge" in e else None,
            }
            for e in entries
        ]

    def summarize_nations(entries: list[dict]) -> list[dict]:
        return [
            {
                "id": e["id"],
                "name_english": e.get("name_english", ""),
                "name_hebrew": e.get("name_hebrew"),
                "relationship": e.get("_relationship"),
            }
            for e in entries
        ]

    return {
        "id": node["id"],
        "name_english": node.get("name_english"),
        "name_hebrew": node.get("name_hebrew"),
        "name_hebrew_transliterated": node.get("name_hebrew_transliterated"),
        "strongs": node.get("strongs"),
        "meaning": node.get("meaning"),
        "sex": node.get("sex"),
        "birth_year_am": node.get("birth_year_am"),
        "death_year_am": node.get("death_year_am"),
        "age_at_death": node.get("age_at_death"),
        "scripture_refs": node.get("scripture_refs", []),
        "notes": node.get("notes"),
        "parents": summarize(parents),
        "spouses": summarize(spouses),
        "children": summarize(children),
        "nations": summarize_nations(nations),
    }


@router.get("/search")
def search_persons(
    q: str = Query(..., min_length=1, description="Search query"),
    type: str | None = Query(None, description="Filter by node type: person, nation, place"),
):
    """Search by English name, Hebrew name, or Strong's number."""
    store = get_store()
    results = store.search(q, node_type=type)

    return [
        {
            "id": r["id"],
            "name_english": r.get("name_english", ""),
            "name_hebrew": r.get("name_hebrew"),
            "strongs": r.get("strongs"),
            "node_type": r.get("node_type"),
            "meaning": r.get("meaning"),
        }
        for r in results[:50]  # Limit results
    ]


@router.get("/lineage/{person_id:path}")
def get_lineage(
    person_id: str,
    direction: str = Query("ancestors", description="ancestors, descendants, or both"),
):
    """Get ancestor or descendant chain for a person."""
    store = get_store()
    node = store.get_node(person_id)
    if node is None or node.get("node_type") != "person":
        raise HTTPException(status_code=404, detail=f"Person not found: {person_id}")

    result = {
        "person": {
            "id": node["id"],
            "name_english": node.get("name_english"),
            "name_hebrew": node.get("name_hebrew"),
        }
    }

    if direction in ("ancestors", "both"):
        ancestors = store.get_ancestors(person_id)
        result["ancestors"] = [
            {
                "id": a["id"],
                "name_english": a.get("name_english"),
                "name_hebrew": a.get("name_hebrew"),
                "birth_year_am": a.get("birth_year_am"),
            }
            for a in ancestors
        ]

    if direction in ("descendants", "both"):
        descendants = store.get_descendants(person_id)
        result["descendants"] = [
            {
                "id": d["id"],
                "name_english": d.get("name_english"),
                "name_hebrew": d.get("name_hebrew"),
                "depth": d.get("_depth"),
            }
            for d in descendants
        ]

    return result


@router.get("/nations")
def get_nations():
    """Get all nations with their eponymous ancestors."""
    store = get_store()
    nations = store.get_nations()
    result = []
    for n in nations:
        ancestor_id = n.get("eponymous_ancestor")
        ancestor = None
        if ancestor_id:
            ancestor_node = store.get_node(ancestor_id)
            if ancestor_node:
                ancestor = {
                    "id": ancestor_node["id"],
                    "name_english": ancestor_node.get("name_english"),
                    "name_hebrew": ancestor_node.get("name_hebrew"),
                }
        result.append(
            {
                "id": n["id"],
                "name_english": n.get("name_english"),
                "name_hebrew": n.get("name_hebrew"),
                "strongs": n.get("strongs"),
                "meaning": n.get("meaning"),
                "eponymous_ancestor": ancestor,
                "scripture_refs": n.get("scripture_refs", []),
                "notes": n.get("notes"),
            }
        )
    return result


@router.get("/stats")
def get_stats():
    """Get summary counts for the graph."""
    return get_store().stats()
