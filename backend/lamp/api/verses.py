"""Verse detail API — the frontend's window into the verse substrate.

Exposes per-verse text (three-layer Hebrew or two-layer Greek), per-word
morphology, and reverse MENTIONS traversal. Structured to make the
exegesis-over-eisegesis discipline render cleanly in UI: canonical
original-language text is always primary, translations (when added) will
attach as a separate field.
"""

from fastapi import APIRouter, HTTPException

from lamp.graph.store import GraphStore
from lamp.models.book_codes import LAMP_CODE_TO_NAME

router = APIRouter(prefix="/verse", tags=["verse"])

_store: GraphStore | None = None


def init_store(store: GraphStore) -> None:
    global _store
    _store = store


def get_store() -> GraphStore:
    if _store is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    return _store


def _format_reference(book: str, chapter: int, verse: int) -> str:
    """Human-readable 'Genesis 1:1' from 'GEN', 1, 1."""
    name = LAMP_CODE_TO_NAME.get(book, book)
    return f"{name} {chapter}:{verse}"


def _summarize_mention(node: dict) -> dict:
    return {
        "id": node["id"],
        "node_type": node.get("node_type"),
        "name_english": node.get("name_english"),
        "name_hebrew": node.get("name_hebrew"),
    }


def _summarize_verse_ref(node: dict) -> dict:
    """Short verse summary for 'verses mentioning entity X' lists."""
    book = node.get("book", "")
    chapter = node.get("chapter")
    verse = node.get("verse")
    reference = (
        f"{LAMP_CODE_TO_NAME.get(book, book)} {chapter}:{verse}"
        if chapter and verse
        else node["id"]
    )
    return {
        "id": node["id"],
        "reference": reference,
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "canon": node.get("canon"),
        "language": node.get("language"),
    }


@router.get("/mentioning/{node_id:path}")
def get_verses_mentioning(node_id: str):
    """List verses that have a MENTIONS edge to this Person/Place/Nation.

    Returned in canonical book/chapter/verse order.
    """
    store = get_store()
    if store.get_node(node_id) is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    verses = store.get_verses_mentioning(node_id)
    return [_summarize_verse_ref(v) for v in verses]


@router.get("/{verse_id:path}")
def get_verse(verse_id: str):
    """Return a verse with full text, per-word morphology, and mentioned entities.

    The verse_id may be fully-qualified ('verse:GEN.1.1') or the bare form
    ('GEN.1.1') — the latter is convenient for URL typing.
    """
    store = get_store()

    # Normalize bare form to full id
    if not verse_id.startswith("verse:"):
        verse_id = f"verse:{verse_id}"

    verse = store.get_verse(verse_id)
    if verse is None:
        raise HTTPException(status_code=404, detail=f"Verse not found: {verse_id}")

    mentions = [_summarize_mention(m) for m in store.get_mentions(verse_id)]

    return {
        "id": verse.id,
        "reference": _format_reference(verse.book, verse.chapter, verse.verse),
        "book": verse.book,
        "book_name": LAMP_CODE_TO_NAME.get(verse.book, verse.book),
        "chapter": verse.chapter,
        "verse": verse.verse,
        "canon": str(verse.canon),
        "language": verse.language,
        "text_canonical": verse.text_canonical,
        # Hebrew layers (empty strings for Greek verses)
        "text_consonantal": verse.text_consonantal,
        "text_pointed": verse.text_pointed,
        "text_cantillated": verse.text_cantillated,
        # Greek layers (empty strings for Hebrew verses)
        "text_plain": verse.text_plain,
        "text_accented": verse.text_accented,
        # Hebrew-specific scribal features
        "parashah_marker": verse.parashah_marker,
        "reversed_nun": verse.reversed_nun,
        "notes": verse.notes,
        # Per-word payload
        "words": [
            {
                "position": w.position,
                "text_canonical": w.text_canonical,
                "text_consonantal": w.text_consonantal,
                "text_pointed": w.text_pointed,
                "text_cantillated": w.text_cantillated,
                "text_plain": w.text_plain,
                "text_accented": w.text_accented,
                "lemma": w.lemma,
                "strongs": w.strongs,
                "morph_code": w.morph_code,
                "transliteration": w.transliteration,
                "text_ketiv": w.text_ketiv,
                "text_qere": w.text_qere,
            }
            for w in verse.words
        ],
        # Reverse traversal — entities mentioned in this verse
        "mentions": mentions,
        # Navigation (within-book)
        "prev_id": store.verses.prev_verse_id(verse_id),
        "next_id": store.verses.next_verse_id(verse_id),
        # Provenance
        "source": verse.source,
        "source_tier": verse.source_tier,
    }
