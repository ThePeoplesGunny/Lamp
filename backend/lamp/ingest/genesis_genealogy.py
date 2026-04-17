"""Load Genesis genealogy seed data into the graph."""

import json
from pathlib import Path

from lamp.models import Person, Place, Nation, Edge, EdgeType, ScriptureRef
from lamp.graph.store import GraphStore


def _load_persons_file(path: Path, store: GraphStore, counts: dict) -> None:
    """Load persons + nations + relationships + nation_links from one JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for p in data.get("persons", []):
        refs = [ScriptureRef(**r) for r in p.get("scripture_refs", [])]
        person = Person(
            id=p["id"],
            name_english=p["name_english"],
            name_hebrew=p.get("name_hebrew"),
            name_hebrew_transliterated=p.get("name_hebrew_transliterated"),
            name_greek=p.get("name_greek"),
            name_greek_transliterated=p.get("name_greek_transliterated"),
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

    for n in data.get("nations", []):
        refs = [ScriptureRef(**r) for r in n.get("scripture_refs", [])]
        nation = Nation(
            id=n["id"],
            name_english=n["name_english"],
            name_hebrew=n.get("name_hebrew"),
            name_hebrew_transliterated=n.get("name_hebrew_transliterated"),
            name_greek=n.get("name_greek"),
            name_greek_transliterated=n.get("name_greek_transliterated"),
            strongs=n.get("strongs"),
            meaning=n.get("meaning"),
            eponymous_ancestor=n.get("eponymous_ancestor"),
            scripture_refs=refs,
            notes=n.get("notes"),
        )
        store.add_nation(nation)
        counts["nations"] += 1

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

    for nl in data.get("nation_links", []):
        edge = Edge(
            source=nl["source"],
            target=nl["target"],
            type=EdgeType(nl["type"]),
        )
        store.add_edge(edge)
        counts["nation_links"] += 1


def _load_places_file(path: Path, store: GraphStore, counts: dict) -> None:
    """Load places + place_links from one JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        places_data = json.load(f)

    for p in places_data.get("places", []):
        refs = [ScriptureRef(**r) for r in p.get("scripture_refs", [])]
        place = Place(
            id=p["id"],
            name_english=p["name_english"],
            name_hebrew=p.get("name_hebrew"),
            name_hebrew_transliterated=p.get("name_hebrew_transliterated"),
            name_greek=p.get("name_greek"),
            name_greek_transliterated=p.get("name_greek_transliterated"),
            strongs=p.get("strongs"),
            meaning=p.get("meaning"),
            place_type=p.get("place_type"),
            latitude=p.get("latitude"),
            longitude=p.get("longitude"),
            scripture_refs=refs,
            notes=p.get("notes"),
        )
        store.add_place(place)
        counts["places"] += 1

    for pl in places_data.get("place_links", []):
        refs = [ScriptureRef(**r) for r in pl.get("scripture_refs", [])]
        edge = Edge(
            source=pl["source"],
            target=pl["target"],
            type=EdgeType(pl["type"]),
            scripture_refs=refs,
            order=pl.get("order"),
            notes=pl.get("notes"),
        )
        store.add_edge(edge)
        counts["place_links"] += 1


def load_seed_data(seed_path: Path, store: GraphStore) -> dict:
    """Load seed data into the graph store.

    seed_path can be a file (persons.json) or a directory. When a directory
    is given, loads persons.json + places.json and their NT counterparts
    persons_nt.json + places_nt.json if present. Returns a summary dict with
    counts.
    """
    if seed_path.is_dir():
        seed_dir = seed_path
        persons_path = seed_dir / "persons.json"
    else:
        seed_dir = seed_path.parent
        persons_path = seed_path

    counts = {"persons": 0, "nations": 0, "relationships": 0, "nation_links": 0,
              "places": 0, "place_links": 0}

    _load_persons_file(persons_path, store, counts)

    nt_persons_path = seed_dir / "persons_nt.json"
    if nt_persons_path.exists():
        _load_persons_file(nt_persons_path, store, counts)

    places_path = seed_dir / "places.json"
    if places_path.exists():
        _load_places_file(places_path, store, counts)

    nt_places_path = seed_dir / "places_nt.json"
    if nt_places_path.exists():
        _load_places_file(nt_places_path, store, counts)

    return counts
