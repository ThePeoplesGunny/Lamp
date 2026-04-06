"""Load Genesis genealogy seed data into the graph."""

import json
from pathlib import Path

from lamp.models import Person, Place, Nation, Edge, EdgeType, ScriptureRef
from lamp.graph.store import GraphStore


def load_seed_data(seed_path: Path, store: GraphStore) -> dict:
    """Load persons.json seed data into the graph store.

    Returns a summary dict with counts.
    """
    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    counts = {"persons": 0, "nations": 0, "relationships": 0, "nation_links": 0}

    # Load persons
    for p in data.get("persons", []):
        # Convert scripture_refs from dicts to ScriptureRef objects
        refs = [ScriptureRef(**r) for r in p.get("scripture_refs", [])]
        person = Person(
            id=p["id"],
            name_english=p["name_english"],
            name_hebrew=p.get("name_hebrew"),
            name_hebrew_transliterated=p.get("name_hebrew_transliterated"),
            strongs=p.get("strongs"),
            meaning=p.get("meaning"),
            sex=p["sex"],
            birth_year_am=p.get("birth_year_am"),
            death_year_am=p.get("death_year_am"),
            age_at_death=p.get("age_at_death"),
            scripture_refs=refs,
            notes=p.get("notes"),
        )
        store.add_person(person)
        counts["persons"] += 1

    # Load nations
    for n in data.get("nations", []):
        refs = [ScriptureRef(**r) for r in n.get("scripture_refs", [])]
        nation = Nation(
            id=n["id"],
            name_english=n["name_english"],
            name_hebrew=n.get("name_hebrew"),
            name_hebrew_transliterated=n.get("name_hebrew_transliterated"),
            strongs=n.get("strongs"),
            meaning=n.get("meaning"),
            eponymous_ancestor=n.get("eponymous_ancestor"),
            scripture_refs=refs,
            notes=n.get("notes"),
        )
        store.add_nation(nation)
        counts["nations"] += 1

    # Load relationships
    for r in data.get("relationships", []):
        refs = [ScriptureRef(**ref) for ref in r.get("scripture_refs", [])]
        edge = Edge(
            source=r["source"],
            target=r["target"],
            type=EdgeType(r["type"]),
            scripture_refs=refs,
            birth_order=r.get("birth_order"),
            age_at_event=r.get("age_at_event"),
            notes=r.get("notes"),
        )
        store.add_edge(edge)
        counts["relationships"] += 1

    # Load nation links
    for nl in data.get("nation_links", []):
        edge = Edge(
            source=nl["source"],
            target=nl["target"],
            type=EdgeType(nl["type"]),
        )
        store.add_edge(edge)
        counts["nation_links"] += 1

    return counts
