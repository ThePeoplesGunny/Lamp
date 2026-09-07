"""Materialize MENTIONS edges from entity `scripture_refs` to verse nodes.

Extracted from scripts/seed_verse_links.py so that seed_graph.py can re-link in
the same process it re-seeds entities. That matters: replacing an entity node
drops every edge incident to it, including its MENTIONS edges. If re-linking
were only available as a separate script, an entity reseed would leave the graph
silently under-linked until someone remembered to run it.

Pure mechanical translation of curated data — no new claims are introduced.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from lamp.models import Edge, EdgeType

ENTITY_NODE_TYPES = ("person", "place", "nation")


@dataclass
class LinkResult:
    """Counts from one linking pass."""

    edges_added: int = 0
    entities_linked: int = 0
    entities_total: int = 0
    entities_without_refs: int = 0
    per_book_edges: Counter[str] = field(default_factory=Counter)
    per_type_entities: Counter[str] = field(default_factory=Counter)
    missing_verses: Counter[str] = field(default_factory=Counter)


def expand_ref(book: str, chapter: int, verse: int, verse_end: int | None) -> list[str]:
    """Expand a scripture ref (possibly a range) into canonical verse IDs."""
    end = verse_end if verse_end else verse
    return [f"verse:{book}.{chapter}.{v}" for v in range(verse, end + 1)]


def link_entities_to_verses(store) -> LinkResult:
    """Create a MENTIONS edge from each referenced verse node to its entity.

    Idempotent: the graph is a MultiDiGraph keyed by edge type, so re-inserting
    (verse → entity, MENTIONS) overwrites rather than accumulating duplicates.
    Refs pointing at verse nodes that are not in the graph are counted in
    `missing_verses` and skipped, never invented.

    Does NOT save. The caller decides when to persist.
    """
    result = LinkResult()

    for node_id, data in store.G.nodes(data=True):
        if data.get("node_type") not in ENTITY_NODE_TYPES:
            continue
        result.entities_total += 1

        refs = data.get("scripture_refs") or []
        if not refs:
            result.entities_without_refs += 1
            continue

        entity_edges = 0
        seen_verse_ids: set[str] = set()

        for ref in refs:
            book = ref["book"]
            for verse_id in expand_ref(
                book, ref["chapter"], ref["verse"], ref.get("verse_end")
            ):
                if verse_id in seen_verse_ids:
                    continue
                seen_verse_ids.add(verse_id)
                if verse_id not in store.G:
                    result.missing_verses[book] += 1
                    continue
                store.add_edge(
                    Edge(source=verse_id, target=node_id, type=EdgeType.MENTIONS)
                )
                entity_edges += 1
                result.per_book_edges[book] += 1

        if entity_edges > 0:
            result.edges_added += entity_edges
            result.entities_linked += 1
            result.per_type_entities[data["node_type"]] += 1

    return result
