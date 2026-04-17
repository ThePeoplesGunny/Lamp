"""Person node model — individuals in the biblical text."""

from pydantic import BaseModel

from lamp.models.common import ScriptureRef


class Person(BaseModel):
    """A named individual in the biblical text."""

    id: str  # e.g. "person:adam"
    name_english: str
    name_hebrew: str | None = None
    name_hebrew_transliterated: str | None = None
    name_greek: str | None = None
    name_greek_transliterated: str | None = None
    strongs: str | None = None  # e.g. "H120" (OT) or "G2424" (NT)
    meaning: str | None = None  # Name meaning
    sex: str  # "male" or "female"
    birth_year_am: int | None = None  # Anno Mundi
    death_year_am: int | None = None
    age_at_death: int | None = None
    scripture_refs: list[ScriptureRef] = []
    notes: str | None = None
