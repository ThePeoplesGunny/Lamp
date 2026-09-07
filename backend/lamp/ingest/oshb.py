"""OSHB (Open Scriptures Hebrew Bible) OSIS-XML parser.

Parses one book at a time from the morphhb `wlc/*.xml` files into Verse records.

Source: https://github.com/openscriptures/morphhb (commit captured at ingest time)
License: WLC text public domain; OSHB lemma/morph data CC-BY-4.0.

Three-layer Hebrew text is derived by Unicode stripping:
  - Cantillated: <w> contents as-is (with segmentation slash removed)
  - Pointed:     cantillated minus te'amim (U+0591-U+05AF, U+05BD, U+05BF)
  - Consonantal: pointed minus niqqud (U+05B0-U+05BC, U+05C1-U+05C2, U+05C7)

Punctuation segments (<seg type="x-sof-pasuq|x-maqqef|x-paseq">) are inlined into
verse-level text so the rendering matches traditional Hebrew Bible typography.
Parashah markers (x-pe, x-samekh) are preserved as verse metadata.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from lamp.models.book_codes import BOOK_CANON, osis_to_lamp
from lamp.models.verse import Verse, VerseWord


OSIS_NS = "http://www.bibletechnologies.net/2003/OSIS/namespace"
NS = {"osis": OSIS_NS}


# Unicode strip patterns
# Te'amim (cantillation marks): U+0591-U+05AF; plus U+05BD (meteg), U+05BF (rafe)
CANTILLATION_RE = re.compile(r"[\u0591-\u05AF\u05BD\u05BF]")
# Niqqud (vowel points): U+05B0-U+05BC, U+05C1, U+05C2, U+05C7
NIQQUD_RE = re.compile(r"[\u05B0-\u05BC\u05C1\u05C2\u05C7]")


def strip_cantillation(text: str) -> str:
    """Remove te'amim, leaving niqqud + consonants."""
    return CANTILLATION_RE.sub("", text)


def strip_niqqud(text: str) -> str:
    """Remove niqqud (vowel points)."""
    return NIQQUD_RE.sub("", text)


def to_consonantal(text: str) -> str:
    """Remove both te'amim and niqqud, leaving only base consonants + punctuation."""
    return strip_niqqud(strip_cantillation(text))


# Strong's numbers are embedded in lemma like "c/m/6529" or "1254 a".
# Extract the first numeric run to give analysts a quick search key.
STRONGS_RE = re.compile(r"(\d+)")


def extract_strongs(lemma: str | None) -> str | None:
    if not lemma:
        return None
    match = STRONGS_RE.search(lemma)
    return match.group(1) if match else None


def clean_word_text(raw: str) -> str:
    """Strip OSHB's `/` segmentation marker; keep all Hebrew content."""
    return raw.replace("/", "")


def q(tag: str) -> str:
    """Build a namespaced tag for ElementTree."""
    return f"{{{OSIS_NS}}}{tag}"


# Child-element names handled inside a <verse>
W = q("w")
SEG = q("seg")
NOTE = q("note")
RDG = q("rdg")


@dataclass
class VerseParseResult:
    verse: Verse
    warnings: list[str]


def _capture_source_version(repo_path: Path) -> str:
    """Return 'OSHB-WLC@<short-sha>' for provenance. Falls back gracefully."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return f"OSHB-WLC@{result.stdout.strip()}"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "OSHB-WLC@unknown"


def _word_from_element(
    w_el: ET.Element,
    position: int,
    ketiv_qere: tuple[str, str] | None = None,
) -> VerseWord:
    """Build a VerseWord from a single <w> element.

    If ketiv_qere is (ketiv_text, qere_text), those are attached to the word.
    """
    raw_text = (w_el.text or "")
    cantillated = clean_word_text(raw_text)
    pointed = strip_cantillation(cantillated)
    consonantal = strip_niqqud(pointed)

    lemma = w_el.get("lemma")
    morph = w_el.get("morph")
    oshb_id = w_el.get("id")

    word = VerseWord(
        position=position,
        text_canonical=cantillated,  # Hebrew "read form" = fully Masoretic
        text_consonantal=consonantal,
        text_pointed=pointed,
        text_cantillated=cantillated,
        lemma=lemma,
        strongs=extract_strongs(lemma),
        morph_code=morph,
        oshb_word_id=oshb_id,
    )
    if ketiv_qere is not None:
        word.text_ketiv, word.text_qere = ketiv_qere
    return word


def _parse_verse(
    verse_el: ET.Element,
    lamp_book: str,
    source: str,
) -> VerseParseResult:
    """Parse one <verse osisID="Gen.1.1">...</verse> into a Verse record."""
    warnings: list[str] = []
    osis_id = verse_el.get("osisID", "")
    try:
        _, chap_str, verse_str = osis_id.split(".")
        chapter = int(chap_str)
        verse_num = int(verse_str)
    except ValueError:
        warnings.append(f"Malformed osisID: {osis_id!r}")
        chapter = 0
        verse_num = 0

    words: list[VerseWord] = []
    notes: list[str] = []
    parashah: str | None = None
    reversed_nun = False
    # Pieces in source order for verse-level text assembly
    cantillated_pieces: list[str] = []
    pointed_pieces: list[str] = []
    consonantal_pieces: list[str] = []

    position = 0

    for child in verse_el:
        tag = child.tag

        if tag == W:
            position += 1
            # Check for ketiv/qere: ketiv word is followed by <note type="variant"><rdg type="x-qere"><w>...
            ketiv_qere: tuple[str, str] | None = None
            if child.get("type") == "x-ketiv":
                ketiv_text = clean_word_text(child.text or "")
                # Resolve qere via a post-loop scan; for now store the ketiv form.
                # Default qere to ketiv — overwritten when we find the <note>.
                ketiv_qere = (ketiv_text, ketiv_text)

            word = _word_from_element(child, position, ketiv_qere)
            words.append(word)

            cantillated_pieces.append(word.text_cantillated)
            pointed_pieces.append(word.text_pointed)
            consonantal_pieces.append(word.text_consonantal)
            # Space between words (overwritten if a maqqef follows)
            cantillated_pieces.append(" ")
            pointed_pieces.append(" ")
            consonantal_pieces.append(" ")

        elif tag == SEG:
            seg_type = child.get("type", "")
            seg_text = child.text or ""
            if seg_type == "x-maqqef":
                # Replace the just-appended space with the maqqef joiner (־)
                if cantillated_pieces and cantillated_pieces[-1] == " ":
                    cantillated_pieces[-1] = seg_text
                    pointed_pieces[-1] = seg_text
                    consonantal_pieces[-1] = seg_text
                else:
                    cantillated_pieces.append(seg_text)
                    pointed_pieces.append(seg_text)
                    consonantal_pieces.append(seg_text)
            elif seg_type == "x-sof-pasuq":
                # End-of-verse mark — hugs last word (no preceding space)
                for pieces in (cantillated_pieces, pointed_pieces, consonantal_pieces):
                    if pieces and pieces[-1] == " ":
                        pieces.pop()
                cantillated_pieces.append(seg_text)
                pointed_pieces.append(seg_text)
                consonantal_pieces.append(seg_text)
            elif seg_type == "x-paseq":
                # Cantillation divider — spaces on both sides in Masoretic convention
                # (leading space already present from prior word; add trailing space)
                for pieces in (cantillated_pieces, pointed_pieces, consonantal_pieces):
                    pieces.append(seg_text)
                    pieces.append(" ")
            elif seg_type == "x-pe":
                parashah = "pe"
            elif seg_type == "x-samekh":
                parashah = "samekh"
            elif seg_type == "x-reversednun":
                # Scribal bracket (nun hafukha) — appears at verse boundary;
                # flag the verse and do not inline the mark into text layers.
                reversed_nun = True
            else:
                warnings.append(f"Unknown seg type {seg_type!r} in {osis_id}")

        elif tag == NOTE:
            note_type = child.get("type", "")
            if note_type == "variant":
                rdg = child.find(RDG)
                if rdg is not None and rdg.get("type") == "x-qere":
                    qere_w = rdg.find(W)
                    qere_text = clean_word_text(qere_w.text or "") if qere_w is not None else ""
                    if qere_w is not None and words and words[-1].text_ketiv is not None:
                        # Qere paired with a preceding ketiv word
                        words[-1].text_qere = qere_text
                    elif qere_w is not None:
                        # Qere-without-ketiv (qere velo ketiv) — reading tradition with no
                        # written counterpart. Insert a word with empty written layers.
                        position += 1
                        placeholder = _word_from_element(qere_w, position)
                        placeholder.text_consonantal = ""
                        placeholder.text_pointed = ""
                        placeholder.text_cantillated = ""
                        placeholder.text_ketiv = ""
                        placeholder.text_qere = qere_text
                        words.append(placeholder)
                        # Intentionally NOT added to verse text pieces — written text
                        # layers must reflect what is consonantally on the page.
            else:
                # Free-form Masoretic note (e.g. n="k" or n="q")
                if child.text:
                    notes.append(child.text.strip())

        # Other element types (e.g. <divineName>) are not expected in wlc/; ignore silently.

    # Trim trailing whitespace from assembled text
    cantillated_text = "".join(cantillated_pieces).rstrip()
    pointed_text = "".join(pointed_pieces).rstrip()
    consonantal_text = "".join(consonantal_pieces).rstrip()

    verse = Verse(
        id=f"verse:{lamp_book}.{chapter}.{verse_num}",
        book=lamp_book,
        chapter=chapter,
        verse=verse_num,
        canon=BOOK_CANON[lamp_book],
        language="hbo",
        text_canonical=cantillated_text,  # Hebrew "read form" = fully Masoretic
        text_consonantal=consonantal_text,
        text_pointed=pointed_text,
        text_cantillated=cantillated_text,
        words=words,
        source=source,
        # Tier 2 = original-language witness, supporting the KJV base text.
        # Was tier 1 until the 2026-09-07 base-text decision, which made the
        # KJV 1769 the canonical layer (tier 1) and moved OSHB/MorphGNT to the
        # supporting-witness tier beneath it. See CLAUDE.md, Locked Decision 8.
        source_tier=2,
        parashah_marker=parashah,
        reversed_nun=reversed_nun,
        notes=notes,
    )
    return VerseParseResult(verse=verse, warnings=warnings)


def parse_book(xml_path: Path, source: str | None = None) -> tuple[list[Verse], list[str]]:
    """Parse one OSHB book XML file into Verse records.

    Returns (verses, warnings).
    """
    if source is None:
        # Walk up from xml_path to find the morphhb repo root
        repo_root = xml_path.parent
        while repo_root != repo_root.parent and not (repo_root / ".git").exists():
            repo_root = repo_root.parent
        source = _capture_source_version(repo_root)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Find the book div — <div type="book" osisID="Gen">
    book_div = None
    for div in root.iter(q("div")):
        if div.get("type") == "book" and div.get("osisID"):
            book_div = div
            break
    if book_div is None:
        raise ValueError(f"No book div found in {xml_path}")

    osis_book = book_div.get("osisID")
    try:
        lamp_book = osis_to_lamp(osis_book)
    except KeyError as exc:
        raise ValueError(f"Unknown OSIS book code: {osis_book!r}") from exc

    verses: list[Verse] = []
    all_warnings: list[str] = []

    for verse_el in book_div.iter(q("verse")):
        if verse_el.get("osisID") is None:
            continue  # Skip <verse eID=...> closing markers if present
        result = _parse_verse(verse_el, lamp_book, source)
        verses.append(result.verse)
        all_warnings.extend(result.warnings)

    return verses, all_warnings
