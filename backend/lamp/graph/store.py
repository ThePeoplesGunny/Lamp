"""Graph persistence and query layer wrapping NetworkX.

This is the core of Lamp. Every feature depends on this being right.
The graph is a NetworkX MultiDiGraph stored as JSON via node_link format.
"""

import json
from pathlib import Path

import networkx as nx

from lamp.models import (
    Person,
    Place,
    Nation,
    Edge,
    EdgeType,
    PARENTAL_EDGES,
    SPOUSAL_EDGES,
)


class GraphStore:
    """Manages the Lamp graph — load, save, query."""

    def __init__(self, graph_path: Path | None = None):
        self.graph_path = graph_path
        self.G: nx.MultiDiGraph = nx.MultiDiGraph()

    # ── Persistence ──────────────────────────────────────────────

    def load(self) -> None:
        """Load graph from JSON file."""
        if self.graph_path and self.graph_path.exists():
            with open(self.graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.G = nx.node_link_graph(data, directed=True, multigraph=True)
        else:
            self.G = nx.MultiDiGraph()

    def save(self) -> None:
        """Save graph to JSON file."""
        if not self.graph_path:
            raise ValueError("No graph_path configured")
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.G)
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Node operations ──────────────────────────────────────────

    def add_person(self, person: Person) -> None:
        """Add a person node to the graph."""
        self.G.add_node(person.id, **person.model_dump(), node_type="person")

    def add_place(self, place: Place) -> None:
        """Add a place node to the graph."""
        self.G.add_node(place.id, **place.model_dump(), node_type="place")

    def add_nation(self, nation: Nation) -> None:
        """Add a nation node to the graph."""
        self.G.add_node(nation.id, **nation.model_dump(), node_type="nation")

    # ── Edge operations ──────────────────────────────────────────

    def add_edge(self, edge: Edge) -> None:
        """Add a typed directed edge between two nodes."""
        if edge.source not in self.G:
            raise ValueError(f"Source node not found: {edge.source}")
        if edge.target not in self.G:
            raise ValueError(f"Target node not found: {edge.target}")
        self.G.add_edge(
            edge.source,
            edge.target,
            key=edge.type,
            **edge.model_dump(),
        )

    # ── Node queries ─────────────────────────────────────────────

    def get_node(self, node_id: str) -> dict | None:
        """Get a node's data by ID. Always includes 'id' in the returned dict."""
        if node_id not in self.G:
            return None
        data = dict(self.G.nodes[node_id])
        data["id"] = node_id
        return data

    def _node_with_id(self, node_id: str) -> dict:
        """Return node data dict with 'id' included."""
        data = dict(self.G.nodes[node_id])
        data["id"] = node_id
        return data

    def get_persons(self) -> list[dict]:
        """Get all person nodes."""
        return [
            self._node_with_id(n)
            for n in self.G.nodes
            if self.G.nodes[n].get("node_type") == "person"
        ]

    def get_nations(self) -> list[dict]:
        """Get all nation nodes."""
        return [
            self._node_with_id(n)
            for n in self.G.nodes
            if self.G.nodes[n].get("node_type") == "nation"
        ]

    def get_places(self) -> list[dict]:
        """Get all place nodes."""
        return [
            self._node_with_id(n)
            for n in self.G.nodes
            if self.G.nodes[n].get("node_type") == "place"
        ]

    # ── Genealogy queries ────────────────────────────────────────

    def get_children(self, person_id: str) -> list[dict]:
        """Get direct children of a person (via father_of or mother_of edges)."""
        children = []
        for _, target, data in self.G.out_edges(person_id, data=True):
            if data.get("type") in PARENTAL_EDGES:
                child_data = self._node_with_id(target)
                child_data["_edge"] = data
                children.append(child_data)
        # Sort by birth_order if available
        children.sort(key=lambda c: c.get("_edge", {}).get("birth_order") or 999)
        return children

    def get_parents(self, person_id: str) -> list[dict]:
        """Get parents of a person (nodes with father_of/mother_of edge to this person)."""
        parents = []
        for source, _, data in self.G.in_edges(person_id, data=True):
            if data.get("type") in PARENTAL_EDGES:
                parent_data = self._node_with_id(source)
                parent_data["_relationship"] = data.get("type")
                parents.append(parent_data)
        return parents

    def get_spouses(self, person_id: str) -> list[dict]:
        """Get spouses of a person (wife_of/concubine_of edges)."""
        spouses = []
        # Check incoming edges (wife → husband)
        for source, _, data in self.G.in_edges(person_id, data=True):
            if data.get("type") in SPOUSAL_EDGES:
                spouse_data = self._node_with_id(source)
                spouse_data["_relationship"] = data.get("type")
                spouses.append(spouse_data)
        # Check outgoing edges (this person as wife)
        for _, target, data in self.G.out_edges(person_id, data=True):
            if data.get("type") in SPOUSAL_EDGES:
                spouse_data = self._node_with_id(target)
                spouse_data["_relationship"] = data.get("type")
                spouses.append(spouse_data)
        return spouses

    def get_ancestors(self, person_id: str) -> list[dict]:
        """Get all ancestors (recursive parents) of a person."""
        ancestors = []
        visited = set()
        queue = [person_id]
        while queue:
            current = queue.pop(0)
            for source, _, data in self.G.in_edges(current, data=True):
                if data.get("type") in PARENTAL_EDGES and source not in visited:
                    visited.add(source)
                    ancestors.append(self._node_with_id(source))
                    queue.append(source)
        return ancestors

    def get_descendants(self, person_id: str, max_depth: int | None = None) -> list[dict]:
        """Get all descendants (recursive children) of a person."""
        descendants = []
        visited = set()
        queue = [(person_id, 0)]
        while queue:
            current, depth = queue.pop(0)
            if max_depth is not None and depth >= max_depth:
                continue
            for _, target, data in self.G.out_edges(current, data=True):
                if data.get("type") in PARENTAL_EDGES and target not in visited:
                    visited.add(target)
                    node_data = self._node_with_id(target)
                    node_data["_depth"] = depth + 1
                    descendants.append(node_data)
                    queue.append((target, depth + 1))
        return descendants

    def get_nations_for_person(self, person_id: str) -> list[dict]:
        """Get nations this person is ancestor of or member of."""
        nations = []
        for _, target, data in self.G.out_edges(person_id, data=True):
            if data.get("type") in (
                EdgeType.ANCESTOR_OF_NATION,
                EdgeType.MEMBER_OF_NATION,
            ):
                nation_data = self._node_with_id(target)
                nation_data["_relationship"] = data.get("type")
                nations.append(nation_data)
        return nations

    # ── Place queries ─────────────────────────────────────────────

    GEOGRAPHIC_EDGES = {
        EdgeType.BORN_AT,
        EdgeType.DIED_AT,
        EdgeType.SETTLED_AT,
        EdgeType.MIGRATED_TO,
        EdgeType.TERRITORY_OF,
    }

    def get_places_for_person(self, person_id: str) -> list[dict]:
        """Get places connected to a person via geographic edges."""
        places = []
        for _, target, data in self.G.out_edges(person_id, data=True):
            if data.get("type") in self.GEOGRAPHIC_EDGES:
                place_data = self._node_with_id(target)
                place_data["_relationship"] = data.get("type")
                place_data["_edge"] = {
                    "notes": data.get("notes"),
                    "order": data.get("order"),
                }
                places.append(place_data)
        return places

    def get_persons_for_place(self, place_id: str) -> list[dict]:
        """Get persons/nations connected to a place (reverse lookup)."""
        connected = []
        for source, _, data in self.G.in_edges(place_id, data=True):
            if data.get("type") in self.GEOGRAPHIC_EDGES:
                node_data = self._node_with_id(source)
                node_data["_relationship"] = data.get("type")
                node_data["_edge"] = {
                    "notes": data.get("notes"),
                    "order": data.get("order"),
                }
                connected.append(node_data)
        return connected

    # ── Tree building ────────────────────────────────────────────

    def build_genealogy_tree(
        self,
        root_id: str,
        max_depth: int | None = None,
    ) -> dict:
        """Build a tree structure from a root person for visualization.

        Returns a dict with 'nodes' and 'edges' lists suitable for React Flow.
        Uses a simple hierarchical layout: x = generation depth, y = sibling index.
        """
        if root_id not in self.G:
            return {"nodes": [], "edges": []}

        tree_nodes = []
        tree_edges = []
        visited = set()

        x_spacing = 250
        y_spacing = 150

        # Track y position per depth level
        y_counters: dict[int, int] = {}

        def traverse(node_id: str, depth: int) -> None:
            if node_id in visited:
                return
            if max_depth is not None and depth > max_depth:
                return
            visited.add(node_id)

            node_data = self._node_with_id(node_id)
            if node_data.get("node_type") != "person":
                return

            y_index = y_counters.get(depth, 0)
            y_counters[depth] = y_index + 1

            tree_nodes.append(
                {
                    "id": node_id,
                    "type": "person",
                    "position": {"x": depth * x_spacing, "y": y_index * y_spacing},
                    "data": {
                        "name_english": node_data.get("name_english", ""),
                        "name_hebrew": node_data.get("name_hebrew"),
                        "meaning": node_data.get("meaning"),
                        "strongs": node_data.get("strongs"),
                        "sex": node_data.get("sex"),
                        "birth_year_am": node_data.get("birth_year_am"),
                        "death_year_am": node_data.get("death_year_am"),
                        "age_at_death": node_data.get("age_at_death"),
                    },
                }
            )

            # Find children via parental edges
            children = []
            for _, target, data in self.G.out_edges(node_id, data=True):
                if data.get("type") in PARENTAL_EDGES and target not in visited:
                    # Only include father_of to avoid duplicate children
                    if data.get("type") == EdgeType.FATHER_OF:
                        children.append((target, data))

            children.sort(key=lambda c: c[1].get("birth_order") or 999)

            for child_id, edge_data in children:
                tree_edges.append(
                    {
                        "id": f"e:{node_id}-{child_id}",
                        "source": node_id,
                        "target": child_id,
                        "data": {
                            "type": edge_data.get("type"),
                            "birth_order": edge_data.get("birth_order"),
                        },
                    }
                )
                traverse(child_id, depth + 1)

        traverse(root_id, 0)
        return {"nodes": tree_nodes, "edges": tree_edges}

    # ── Search ───────────────────────────────────────────────────

    def search(self, query: str, node_type: str | None = None) -> list[dict]:
        """Search nodes by name (English, Hebrew, or Strong's number)."""
        query_lower = query.lower()
        results = []
        for node_id in self.G.nodes:
            data = self.G.nodes[node_id]
            if node_type and data.get("node_type") != node_type:
                continue
            searchable = [
                (data.get("name_english") or "").lower(),
                (data.get("name_hebrew") or "").lower(),
                (data.get("name_hebrew_transliterated") or "").lower(),
                (data.get("strongs") or "").lower(),
            ]
            if any(query_lower in field for field in searchable):
                results.append(self._node_with_id(node_id))
        return results

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return summary counts."""
        persons = sum(
            1 for n in self.G.nodes if self.G.nodes[n].get("node_type") == "person"
        )
        nations = sum(
            1 for n in self.G.nodes if self.G.nodes[n].get("node_type") == "nation"
        )
        places = sum(
            1 for n in self.G.nodes if self.G.nodes[n].get("node_type") == "place"
        )
        edges = self.G.number_of_edges()
        return {
            "persons": persons,
            "nations": nations,
            "places": places,
            "edges": edges,
            "total_nodes": self.G.number_of_nodes(),
        }
