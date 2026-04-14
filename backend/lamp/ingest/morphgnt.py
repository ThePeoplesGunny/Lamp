"""MorphGNT (SBLGNT) parser.

Parses one book at a time from the morphgnt/sblgnt flat-file format.

Source: https://github.com/morphgnt/sblgnt (commit captured at ingest time)
License:
  - SBLGNT text itself: governed by SBLGNT EULA (http://sblgnt.com/license/)
    — permits non-commercial academic/personal/research use with attribution.
  - MorphGNT morphological parsing + lemmatization: CC-BY-SA 3.0 (Share-Alike).

File format — one word per line, whitespace-separated columns:
  [0] book/chapter/verse (BBCCVV, 6 digits, NT book numbering 01=Matt .. 27=Rev)
  [1] part-of-speech code (2 chars, padded with `-`)
  [2] parsing code (8 chars, padded with `-`)
  [3] text in context (accented, WITH punctuation)
  [4] word (accented, punctuation stripped)
  [5] normalized word
  [6] lemma (dictionary form)

Text layers derived:
  - text_accented: context text with punctuation (column [3]), joined across the verse
  - text_plain:    diacritics stripped via NFD decomposition + Mn-category filter,
                   lowercased. Punctuation retained for word-boundary legibility.
"""

from __future__ import annotations

import re
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from lamp.models.book_codes import BOOK_CANON, osis_to_lamp
from lamp.models.verse import Verse, VerseWord


# MorphGNT internal book numbers (01-27) → OSIS code. OSIS code then maps to
# Lamp code via lamp.models.book_codes.osis_to_lamp.
MORPHGNT_NUM_TO_OSIS = {
    "01": "Matt",  "02": "Mark",  "03": "Luke",   "04": "John",
    "05": "Acts",  "06": "Rom",   "07": "1Cor",   "08": "2Cor",
    "09": "Gal",   "10": "Eph",   "11": "Phil",   "12": "Col",
    "13": "1Thess","14": "2Thess","15": "1Tim",   "16": "2Tim",
    "17": "Titus", "18": "Phlm",  "19": "Heb",    "20": "Jas",
    "21": "1Pet",  "22": "2Pet",  "23": "1John",  "24": "2John",
    "25": "3John", "26": "Jude",  "27": "Rev",
}


def strip_greek_diacritics(text: str) -> str:
    """Remove all Greek combining marks (accents, breathings, iota subscripts, etc.).

    Uses NFD normalization to separate combining marks from base letters, then
    filters out any Mark-nonspacing (Mn) characters. Result is lowercased.
    """
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return without_marks.lower()


# Whitespace-separated column parsing. MorphGNT uses regular spaces.
_WS_RE = re.compile(r"\s+")


@dataclass
class VerseParseResult:
    verse: Verse
    warnings: list[str]


def _capture_source_version(repo_path: Path) -> str:
    """Return 'MorphGNT-SBLGNT@<short-sha>' for provenance."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return f"MorphGNT-SBLGNT@{result.stdout.strip()}"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "MorphGNT-SBLGNT@unknown"


@dataclass
class _ParsedWord:
    pos_code: str
    parsing_code: str
    text_in_context: str  # with punctuation
    word: str             # punctuation-stripped
    normalized: str
    lemma: str


def _parse_line(line: str) -> tuple[str, _ParsedWord] | None:
    """Parse one MorphGNT line. Returns (BCV, ParsedWord) or None for blank lines."""
    line = line.rstrip("\n\r")
    if not line.strip():
        return None
    parts = _WS_RE.split(line.strip())
    if len(parts) != 7:
        raise ValueError(f"Expected 7 columns, got {len(parts)}: {line!r}")
    bcv, pos, parsing, text_in_context, word, normalized, lemma = parts
    return bcv, _ParsedWord(
        pos_code=pos,
        parsing_code=parsing,
        text_in_context=text_in_context,
        word=word,
        normalized=normalized,
        lemma=lemma,
    )


def _bcv_to_ids(bcv: str) -> tuple[str, int, int]:
    """Split '010101' → ('01', 1, 1) — book code, chapter, verse."""
    if len(bcv) != 6:
        raise ValueError(f"Bad BCV format: {bcv!r}")
    book_num = bcv[0:2]
    chapter = int(bcv[2:4])
    verse = int(bcv[4:6])
    return book_num, chapter, verse


def parse_book(txt_path: Path, source: str | None = None) -> tuple[list[Verse], list[str]]:
    """Parse one MorphGNT book file into Verse records. Returns (verses, warnings)."""
    if source is None:
        repo_root = txt_path.parent
        while repo_root != repo_root.parent and not (repo_root / ".git").exists():
            repo_root = repo_root.parent
        source = _capture_source_version(repo_root)

    warnings: list[str] = []
    verses: list[Verse] = []

    # Group lines by (book, chapter, verse). Order is already source-order.
    current_bcv: str | None = None
    current_words: list[_ParsedWord] = []

    def flush() -> None:
        if current_bcv is None or not current_words:
            return
        try:
            book_num, chapter, verse_num = _bcv_to_ids(current_bcv)
            osis = MORPHGNT_NUM_TO_OSIS[book_num]
            lamp_book = osis_to_lamp(osis)
        except (KeyError, ValueError) as exc:
            warnings.append(f"Skipping malformed BCV {current_bcv!r}: {exc}")
            current_words.clear()
            return

        # Build per-word records and verse-level text layers
        verse_words: list[VerseWord] = []
        accented_pieces: list[str] = []
        plain_pieces: list[str] = []

        for idx, pw in enumerate(current_words, start=1):
            accented_word = pw.word          # punctuation-stripped accented form
            plain_word = strip_greek_diacritics(accented_word)

            verse_words.append(VerseWord(
                position=idx,
                text_canonical=accented_word,   # Greek "read form" = accented
                text_accented=accented_word,
                text_plain=plain_word,
                lemma=pw.lemma,
                strongs=None,                   # MorphGNT doesn't carry Strong's
                morph_code=f"G{pw.pos_code}{pw.parsing_code}",
                sblgnt_index=idx,
            ))

            # Verse-level text is built from the context text (which has punctuation).
            # Space-separate words; punctuation hugs its word.
            accented_pieces.append(pw.text_in_context)
            plain_pieces.append(strip_greek_diacritics(pw.text_in_context))

        accented_text = " ".join(accented_pieces)
        plain_text = " ".join(plain_pieces)

        verses.append(Verse(
            id=f"verse:{lamp_book}.{chapter}.{verse_num}",
            book=lamp_book,
            chapter=chapter,
            verse=verse_num,
            canon=BOOK_CANON[lamp_book],
            language="grc",
            text_canonical=accented_text,
            text_accented=accented_text,
            text_plain=plain_text,
            words=verse_words,
            source=source,
            source_tier=1,
        ))
        current_words.clear()

    with open(txt_path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            try:
                parsed = _parse_line(raw)
            except ValueError as exc:
                warnings.append(f"line {lineno}: {exc}")
                continue
            if parsed is None:
                continue
            bcv, pw = parsed
            if bcv != current_bcv:
                flush()
                current_bcv = bcv
            current_words.append(pw)
        flush()

    return verses, warnings
