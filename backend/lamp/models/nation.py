"""Nation/people group node model."""

from pydantic import BaseModel

from lamp.models.common import ScriptureRef


class Nation(BaseModel):
    """A nation or people group, often descending from an eponymous ancestor."""

    id: str  # e.g. "nation:canaanites"
    name_english: str
    name_hebrew: str | None = None
    name_hebrew_transliterated: str | None = None
    name_greek: str | None = None
    name_greek_transliterated: str | None = None
    strongs: str | None = None
    meaning: str | None = None
    eponymous_ancestor: str | None = None  # person ID
    scripture_refs: list[ScriptureRef] = []
    notes: str | None = None
