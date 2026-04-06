"""Common types shared across all models."""

from pydantic import BaseModel


class ScriptureRef(BaseModel):
    """A reference to a specific verse in the Bible."""

    book: str  # e.g. "GEN", "EXO", "PSA"
    chapter: int
    verse: int
    verse_end: int | None = None  # For ranges like Gen 5:3-5

    def __str__(self) -> str:
        ref = f"{self.book} {self.chapter}:{self.verse}"
        if self.verse_end:
            ref += f"-{self.verse_end}"
        return ref
