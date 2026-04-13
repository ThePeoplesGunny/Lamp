"""Verse node model — verses as first-class graph nodes.

Schema locked by backend/docs/verse_graph_schema.md (2026-04-13).

Three-layer text preserves the Masoretic stratigraphy: consonantal (oldest),
pointed (niqqud added 7th–10th c. AD), cantillated (te'amim added same era).
Any analytical query can request the text at any stratum without losing fidelity.
"""

from pydantic import BaseModel

from lamp.models.book_codes import Canon


class VerseWord(BaseModel):
    """One Hebrew/Greek word within a verse, with full morphology."""

    position: int                    # 1-indexed position within the verse
    text_consonantal: str            # Letters only, no niqqud, no te'amim
    text_pointed: str                # With niqqud (vowel points)
    text_cantillated: str            # With niqqud + te'amim (Masoretic full)
    lemma: str | None = None         # OSHB lemma, may include prefix segmentation (e.g. "c/m/6529")
    strongs: str | None = None       # Extracted numeric Strong's (e.g. "6529") for easy search
    morph_code: str | None = None    # OSHB morphology code (e.g. "HC/R/Ncmsc")
    transliteration: str | None = None
    oshb_word_id: str | None = None  # OSHB immutable word id (e.g. "01xeN")

    # Ketiv/Qere variants — populated only when this word has a variant reading
    text_ketiv: str | None = None    # Written form (usually consonantal)
    text_qere: str | None = None     # Read form (usually pointed)


class Verse(BaseModel):
    """A single Bible verse as a graph node."""

    id: str                          # "verse:GEN.5.3"
    node_type: str = "verse"
    book: str                        # Lamp canonical code: "GEN"
    chapter: int
    verse: int
    canon: Canon                     # tanakh / nt / lxx

    # Text representation metadata
    language: str                    # ISO 639-3: "hbo" | "grc" | "arc"

    # Three-layer canonical text (whole verse, joined from words)
    text_consonantal: str
    text_pointed: str
    text_cantillated: str

    # Word-level breakdown with full morphology
    words: list[VerseWord]

    # Provenance (Research Methodology — all claims carry source)
    source: str                      # Exact version, e.g. "OSHB-WLC@3d15126f"
    source_tier: int                 # Per CLAUDE.md; OSHB = tier 1

    # Ancient paragraph markers (Masoretic parashah)
    # Values from OSHB: "pe" (petuchah / open) or "samekh" (setumah / closed).
    # Marker appears AFTER this verse's text (end-of-paragraph marker).
    parashah_marker: str | None = None

    # Reversed/inverted nun (nun hafukha, ׆ U+05C6) — rare scribal bracket marking
    # textually-set-apart passages. True for the 9 verses in the MT that carry it
    # (bracketing Num 10:35-36 and bracketing three sections in Ps 107).
    reversed_nun: bool = False

    # Free-form Masoretic notes (ketiv/qere commentary, BHS variants)
    notes: list[str] = []


class TranslationText(BaseModel):
    """A translation of a single verse. Stored separately from canonical verse nodes.

    Separation is deliberate — enforces exegesis/eisegesis discipline in the data model
    and makes translation-history comparison a first-class operation.
    """

    translation: str                 # "KJV-1769" | "ASV-1901" | "WEB" | "GEN-1599" | "TYN" | "DRA"
    verse_id: str                    # FK to Verse.id — "verse:GEN.5.3"
    text: str
    source: str                      # Exact edition identifier
    source_tier: int
