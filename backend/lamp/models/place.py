"""Place node model — geographic locations in the biblical text."""

from pydantic import BaseModel

from lamp.models.common import ScriptureRef


class Place(BaseModel):
    """A named geographic location in the biblical text."""

    id: str  # e.g. "place:eden"
    name_english: str
    name_hebrew: str | None = None
    name_hebrew_transliterated: str | None = None
    name_greek: str | None = None
    name_greek_transliterated: str | None = None
    strongs: str | None = None
    meaning: str | None = None
    place_type: str | None = None  # region, city, mountain, river, etc.
    latitude: float | None = None
    longitude: float | None = None
    scripture_refs: list[ScriptureRef] = []
    notes: str | None = None
