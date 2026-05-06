"""Edge type definitions — the analytical power of the graph.

Every edge is directed and typed. The type determines inheritance rights,
covenant lineage, tribal identity, and geographic/political relationships.
"""

from enum import StrEnum

from pydantic import BaseModel

from lamp.models.common import ScriptureRef


class EdgeType(StrEnum):
    """All relationship types in the graph."""

    # Genealogical — direction conventions:
    #   parent → child for father_of/mother_of
    #   husband → wife for wife_of/concubine_of (legacy OT convention)
    #   husband → wife for husband_of, source is the husband
    #   sibling → sibling for brother_of/sister_of (symmetric — both directions seeded)
    FATHER_OF = "father_of"
    MOTHER_OF = "mother_of"
    WIFE_OF = "wife_of"
    HUSBAND_OF = "husband_of"
    CONCUBINE_OF = "concubine_of"
    BROTHER_OF = "brother_of"
    SISTER_OF = "sister_of"
    COUSIN_OF = "cousin_of"
    RELATIVE_OF = "relative_of"  # kinship unspecified (Greek syngenis)
    SON_IN_LAW_OF = "son_in_law_of"
    DAUGHTER_IN_LAW_OF = "daughter_in_law_of"

    # Discipleship and household
    DISCIPLE_OF = "disciple_of"
    SLAVE_OF = "slave_of"  # source serves target

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

    # Verse ↔ entity (Phase 2C-1 — verse nodes are first-class)
    # Every edge sources at a verse and encodes a distinct exegetical relationship.
    MENTIONS = "mentions"              # verse → person/place/nation/event
    SPOKEN_BY = "spoken_by"            # verse → person (direct speech)
    ADDRESSED_TO = "addressed_to"      # verse → person/nation (recipient of speech/writing)
    SET_IN = "set_in"                  # verse → place (narrative location)
    OCCURS_DURING = "occurs_during"    # verse → event

    # Verse ↔ verse
    QUOTES = "quotes"                  # verse → verse (e.g. NT citing OT)
    ALLUDES_TO = "alludes_to"          # verse → verse (softer than quotes)
    PARALLEL_TO = "parallel_to"        # verse ↔ verse (synoptic / Kings-Chronicles / Psalm parallels)


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
