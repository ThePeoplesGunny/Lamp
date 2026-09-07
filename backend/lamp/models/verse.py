"""Verse node model — verses as first-class graph nodes.

Schema locked by backend/docs/verse_graph_schema.md (2026-04-13, Greek addendum 2026-04-13).

Hebrew stratigraphy (Masoretic): consonantal (oldest), pointed (niqqud added
7th–10th c. AD), cantillated (te'amim added same era).
Greek stratigraphy (manuscript tradition): plain (lowercase, no diacritics —
closer to ancient uncial manuscripts) and accented (standard minuscule-era
published form).

Hebrew verses populate the Hebrew trio; Greek verses populate the Greek pair.
`text_canonical` holds the "standard read form" — cantillated for Hebrew,
accented for Greek — so display code does not need language branching.
"""

from pydantic import BaseModel

from lamp.models.book_codes import Canon


class VerseWord(BaseModel):
    """One Hebrew/Greek word within a verse, with full morphology."""

    position: int                    # 1-indexed position within the verse

    # Language-agnostic read form. Cantillated for Hebrew, accented for Greek.
    text_canonical: str = ""

    # Hebrew layers (default empty for non-Hebrew verses)
    text_consonantal: str = ""       # Letters only, no niqqud, no te'amim
    text_pointed: str = ""           # With niqqud (vowel points)
    text_cantillated: str = ""       # With niqqud + te'amim (Masoretic full)

    # Greek layers (default empty for non-Greek verses)
    text_plain: str = ""             # Lowercase, no accents/breathings/iota-subscripts
    text_accented: str = ""          # Standard published form with full diacritics

    # Common morphology
    lemma: str | None = None         # OSHB / MorphGNT dictionary form
    strongs: str | None = None       # Strong's number (Hebrew via OSHB; Greek: None unless tagged)
    morph_code: str | None = None    # "HVqp3ms" (OSHB) or "GN-----NSF-" (MorphGNT, G-prefixed)
    transliteration: str | None = None

    # Hebrew provenance
    oshb_word_id: str | None = None  # Immutable OSHB word id (e.g. "01xeN")

    # Greek provenance
    sblgnt_index: int | None = None  # 1-indexed position in MorphGNT source file

    # Hebrew ketiv/qere variants — populated only when this word has a variant reading
    text_ketiv: str | None = None    # Written form (usually consonantal)
    text_qere: str | None = None     # Read form (usually pointed)


class Verse(BaseModel):
    """A single Bible verse as a graph node."""

    id: str                          # "verse:GEN.5.3" | "verse:JHN.3.16"
    node_type: str = "verse"
    book: str                        # Lamp canonical code: "GEN" | "JHN"
    chapter: int
    verse: int
    canon: Canon                     # tanakh / nt / lxx

    # Text representation metadata
    language: str                    # ISO 639-3: "hbo" (Hebrew) | "grc" (Greek) | "arc" (Aramaic)

    # Language-agnostic read form — cantillated for Hebrew, accented for Greek.
    # Consumers that just want "the text" should use this.
    text_canonical: str = ""

    # Hebrew-stratum text layers (default empty for non-Hebrew)
    text_consonantal: str = ""
    text_pointed: str = ""
    text_cantillated: str = ""

    # Greek-stratum text layers (default empty for non-Greek)
    text_plain: str = ""
    text_accented: str = ""

    # Word-level breakdown with full morphology
    words: list[VerseWord]

    # Provenance of the ORIGINAL-LANGUAGE WITNESS (Research Methodology — all
    # claims carry source). None when the verse has no witness: the 32 verses
    # present in the KJV 1769 base text but absent from the SBLGNT critical text
    # have identity and a base text, but nothing to cite here.
    source: str | None = None        # e.g. "OSHB-WLC@3d15126" | "MorphGNT-SBLGNT@<sha>"
    source_tier: int | None = None   # Per CLAUDE.md; OSHB and MorphGNT are both tier 2

    # Hebrew-specific Masoretic features (default None/False for non-Hebrew)
    # "pe" (petuchah / open) or "samekh" (setumah / closed). Marker appears AFTER verse text.
    parashah_marker: str | None = None
    # Reversed/inverted nun (nun hafukha, ׆ U+05C6). True for the 9 MT verses that carry it.
    reversed_nun: bool = False

    # Free-form textual notes (ketiv/qere commentary, BHS variants, MorphGNT notes)
    notes: list[str] = []


class VerseRef(BaseModel):
    """A verse's identity, independent of any text that witnesses it.

    Introduced 2026-09-07 when verse identity was split from the original-language
    witness. A verse can exist with identity alone: 32 verses are present in the
    KJV 1769 base text but absent from the SBLGNT critical text, so they have no
    Greek witness at all. Before the split they were given fabricated empty Greek
    rows, because the KJV text needed a parent row to hang off.
    """

    id: str                          # "verse:ACT.8.37"
    book: str                        # Lamp canonical code
    chapter: int
    verse: int
    canon: Canon
    notes: list[str] = []            # notes about the verse itself, not about a witness


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
