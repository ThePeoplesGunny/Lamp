"""Verse detail API — the frontend's window into the verse substrate.

Exposes per-verse text (three-layer Hebrew or two-layer Greek), per-word
morphology, and reverse MENTIONS traversal. Structured to make the
exegesis-over-eisegesis discipline render cleanly in UI: canonical
original-language text is always primary, translations (when added) will
attach as a separate field.
"""

from fastapi import APIRouter, HTTPException, Query

from lamp.graph.store import GraphStore
from lamp.models.book_codes import LAMP_CODE_TO_NAME

router = APIRouter(prefix="/verse", tags=["verse"])
nav_router = APIRouter(tags=["verse-navigation"])

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
        "name_hebrew_transliterated": node.get("name_hebrew_transliterated"),
        "name_greek": node.get("name_greek"),
        "name_greek_transliterated": node.get("name_greek_transliterated"),
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


def _summarize_quote_ref(node: dict) -> dict:
    """Verse summary plus the edge's exegetical notes — for cites/cited_by lists."""
    out = _summarize_verse_ref(node)
    out["notes"] = node.get("_edge_notes")
    return out


@nav_router.get("/books")
def list_books():
    """All ingested books with canon, language, and chapter/verse counts.

    Used by the navigation UI to build the book list and chapter picker.
    Returned in canonical book order (OT → NT).
    """
    store = get_store()
    summaries = store.verses.books_summary()

    # Canonical order: Tanakh (Torah, Nevi'im, Ketuvim) then NT
    canonical_order = [
        # Torah
        "GEN", "EXO", "LEV", "NUM", "DEU",
        # Former Prophets
        "JOS", "JDG", "1SA", "2SA", "1KI", "2KI",
        # Latter Prophets
        "ISA", "JER", "EZK",
        # The Twelve
        "HOS", "JOL", "AMO", "OBA", "JON", "MIC",
        "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
        # Ketuvim
        "PSA", "PRO", "JOB", "SNG", "RUT", "LAM",
        "ECC", "EST", "DAN", "EZR", "NEH", "1CH", "2CH",
        # New Testament
        "MAT", "MRK", "LUK", "JHN", "ACT", "ROM",
        "1CO", "2CO", "GAL", "EPH", "PHP", "COL",
        "1TH", "2TH", "1TI", "2TI", "TIT", "PHM",
        "HEB", "JAS", "1PE", "2PE", "1JN", "2JN",
        "3JN", "JUD", "REV",
    ]
    order_index = {code: i for i, code in enumerate(canonical_order)}

    books = []
    for s in summaries:
        books.append({
            **s,
            "name": LAMP_CODE_TO_NAME.get(s["book"], s["book"]),
        })
    books.sort(key=lambda b: order_index.get(b["book"], 999))
    return books


@nav_router.get("/lexeme/occurrences")
def get_lexeme_occurrences(
    lemma: str | None = Query(None, description="Exact OSHB/MorphGNT lemma (e.g. 'βίβλος' or 'b/7225')"),
    strongs: str | None = Query(None, description="Strong's number — Hebrew only (e.g. '1254')"),
    canon: str | None = Query(None, description="Filter: tanakh, nt, or all (default: all)"),
    limit: int = Query(500, ge=1, le=2000, description="Max results (default 500, max 2000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Find every verse where the given lemma or Strong's number appears.

    Exactly one of `lemma` or `strongs` is required. Greek verses do not carry
    Strong's numbers (MorphGNT doesn't tag them), so Greek searches must use `lemma`.
    """
    store = get_store()
    if (lemma is None) == (strongs is None):
        raise HTTPException(
            status_code=400,
            detail="Exactly one of 'lemma' or 'strongs' is required",
        )

    results, total = store.verses.occurrences(
        lemma=lemma,
        strongs=strongs,
        canon=canon,
        limit=limit,
        offset=offset,
    )

    # Enrich each result with a human-readable reference
    for r in results:
        r["reference"] = (
            f"{LAMP_CODE_TO_NAME.get(r['book'], r['book'])} {r['chapter']}:{r['verse']}"
        )

    return {
        "key": lemma if lemma is not None else strongs,
        "key_type": "lemma" if lemma is not None else "strongs",
        "canon": canon or "all",
        "total": total,
        "limit": limit,
        "offset": offset,
        "returned": len(results),
        "results": results,
    }


@nav_router.get("/book/{book}/chapter/{chapter}")
def get_chapter(book: str, chapter: int):
    """Lightweight list of verses in a chapter — id, number, canonical-text preview.

    Heavy fields (per-word morphology, three-layer text) are NOT included;
    the frontend fetches the full verse via /verse/{id} when one is opened.
    """
    store = get_store()
    book_upper = book.upper()
    verses = store.verses.chapter_verses(book_upper, chapter)
    if not verses:
        raise HTTPException(
            status_code=404,
            detail=f"No verses found for {book_upper} chapter {chapter}",
        )
    return {
        "book": book_upper,
        "book_name": LAMP_CODE_TO_NAME.get(book_upper, book_upper),
        "chapter": chapter,
        "verses": verses,
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
    cites = [_summarize_quote_ref(v) for v in store.get_cites(verse_id)]
    cited_by = [_summarize_quote_ref(v) for v in store.get_cited_by(verse_id)]
    translations = store.verses.get_translations_for_verse(verse_id)

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
        # Cross-canon quote traversal
        "cites": cites,             # verses this one quotes (NT→OT direction)
        "cited_by": cited_by,       # verses that quote this one
        # Translation layer — reference text, never replaces the original
        "translations": [
            {
                "translation": t.translation,
                "text": t.text,
                "source": t.source,
                "source_tier": t.source_tier,
            }
            for t in translations
        ],
        # Navigation (within-book)
        "prev_id": store.verses.prev_verse_id(verse_id),
        "next_id": store.verses.next_verse_id(verse_id),
        # Provenance
        "source": verse.source,
        "source_tier": verse.source_tier,
    }
