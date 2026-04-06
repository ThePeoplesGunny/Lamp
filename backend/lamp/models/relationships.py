"""Edge type definitions — the analytical power of the graph.

Every edge is directed and typed. The type determines inheritance rights,
covenant lineage, tribal identity, and geographic/political relationships.
"""

from enum import StrEnum

from pydantic import BaseModel

from lamp.models.common import ScriptureRef


class EdgeType(StrEnum):
    """All relationship types in the graph."""

    # Genealogical — direction: parent → child, wife → husband
    FATHER_OF = "father_of"
    MOTHER_OF = "mother_of"
    WIFE_OF = "wife_of"
    CONCUBINE_OF = "concubine_of"

    # National/tribal
    ANCESTOR_OF_NATION = "ancestor_of_nation"  # person → nation
    MEMBER_OF_NATION = "member_of_nation"  # person → nation
    ALLIED_WITH = "allied_with"  # nation → nation
    CONFLICT_WITH = "conflict_with"  # nation → nation

    # Geographic
    BORN_AT = "born_at"  # person → place
    DIED_AT = "died_at"  # person → place
    SETTLED_AT = "settled_at"  # person/nation → place
    MIGRATED_TO = "migrated_to"  # person/nation → place
    TERRITORY_OF = "territory_of"  # nation → place

    # Temporal
    DURING_EVENT = "during_event"  # person → event
    CONTEMPORARY_OF = "contemporary_of"  # person → person

    # Scripture
    MENTIONED_IN = "mentioned_in"  # any → scripture_ref


# Which edge types represent parent-child relationships
PARENTAL_EDGES = {EdgeType.FATHER_OF, EdgeType.MOTHER_OF}

# Which edge types represent spousal relationships
SPOUSAL_EDGES = {EdgeType.WIFE_OF, EdgeType.CONCUBINE_OF}


class Edge(BaseModel):
    """A directed relationship between two nodes."""

    source: str  # Node ID
    target: str  # Node ID
    type: EdgeType
    scripture_refs: list[ScriptureRef] = []
    birth_order: int | None = None  # For parent → child edges
    age_at_event: int | None = None  # Parent's age when child born
    order: int | None = None  # Sequence for migrations, etc.
    notes: str | None = None
