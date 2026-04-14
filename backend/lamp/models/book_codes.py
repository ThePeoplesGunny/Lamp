"""Book code mapping — OSIS ↔ SBL 3-letter.

Lamp canonical book codes are SBL-standard uppercase 3-letter (GEN, EXO, PSA, ...).
OSHB and other OSIS-formatted sources use mixed-case codes (Gen, Exod, Ps, ...).
This module maps between the two and also tracks canon membership (tanakh / nt / lxx).
"""

from enum import StrEnum


class Canon(StrEnum):
    TANAKH = "tanakh"  # Hebrew Bible / Protestant OT
    NT = "nt"          # Greek New Testament
    LXX = "lxx"        # Septuagint, including deuterocanon


# Canonical Lamp book codes (SBL style).
# Ordered per the Hebrew Bible tripartite structure (Torah, Nevi'im, Ketuvim),
# then NT, then LXX-only deuterocanon (added in Phase 2C-1 Step 2.5).
LAMP_CODE_TO_NAME = {
    # Torah
    "GEN": "Genesis",
    "EXO": "Exodus",
    "LEV": "Leviticus",
    "NUM": "Numbers",
    "DEU": "Deuteronomy",
    # Nevi'im — Former Prophets
    "JOS": "Joshua",
    "JDG": "Judges",
    "1SA": "1 Samuel",
    "2SA": "2 Samuel",
    "1KI": "1 Kings",
    "2KI": "2 Kings",
    # Nevi'im — Latter Prophets
    "ISA": "Isaiah",
    "JER": "Jeremiah",
    "EZK": "Ezekiel",
    "HOS": "Hosea",
    "JOL": "Joel",
    "AMO": "Amos",
    "OBA": "Obadiah",
    "JON": "Jonah",
    "MIC": "Micah",
    "NAM": "Nahum",
    "HAB": "Habakkuk",
    "ZEP": "Zephaniah",
    "HAG": "Haggai",
    "ZEC": "Zechariah",
    "MAL": "Malachi",
    # Ketuvim
    "PSA": "Psalms",
    "PRO": "Proverbs",
    "JOB": "Job",
    "SNG": "Song of Songs",
    "RUT": "Ruth",
    "LAM": "Lamentations",
    "ECC": "Ecclesiastes",
    "EST": "Esther",
    "DAN": "Daniel",
    "EZR": "Ezra",
    "NEH": "Nehemiah",
    "1CH": "1 Chronicles",
    "2CH": "2 Chronicles",
    # New Testament
    "MAT": "Matthew",
    "MRK": "Mark",
    "LUK": "Luke",
    "JHN": "John",
    "ACT": "Acts",
    "ROM": "Romans",
    "1CO": "1 Corinthians",
    "2CO": "2 Corinthians",
    "GAL": "Galatians",
    "EPH": "Ephesians",
    "PHP": "Philippians",
    "COL": "Colossians",
    "1TH": "1 Thessalonians",
    "2TH": "2 Thessalonians",
    "1TI": "1 Timothy",
    "2TI": "2 Timothy",
    "TIT": "Titus",
    "PHM": "Philemon",
    "HEB": "Hebrews",
    "JAS": "James",
    "1PE": "1 Peter",
    "2PE": "2 Peter",
    "1JN": "1 John",
    "2JN": "2 John",
    "3JN": "3 John",
    "JUD": "Jude",
    "REV": "Revelation",
}

# OSIS (OSHB / SBLGNT) codes → Lamp canonical codes
OSIS_TO_LAMP = {
    # Torah
    "Gen": "GEN",
    "Exod": "EXO",
    "Lev": "LEV",
    "Num": "NUM",
    "Deut": "DEU",
    # Former Prophets
    "Josh": "JOS",
    "Judg": "JDG",
    "Ruth": "RUT",
    "1Sam": "1SA",
    "2Sam": "2SA",
    "1Kgs": "1KI",
    "2Kgs": "2KI",
    # Latter Prophets
    "Isa": "ISA",
    "Jer": "JER",
    "Lam": "LAM",
    "Ezek": "EZK",
    "Hos": "HOS",
    "Joel": "JOL",
    "Amos": "AMO",
    "Obad": "OBA",
    "Jonah": "JON",
    "Mic": "MIC",
    "Nah": "NAM",
    "Hab": "HAB",
    "Zeph": "ZEP",
    "Hag": "HAG",
    "Zech": "ZEC",
    "Mal": "MAL",
    # Ketuvim
    "Ps": "PSA",
    "Prov": "PRO",
    "Job": "JOB",
    "Song": "SNG",
    "Eccl": "ECC",
    "Esth": "EST",
    "Dan": "DAN",
    "Ezra": "EZR",
    "Neh": "NEH",
    "1Chr": "1CH",
    "2Chr": "2CH",
    # NT (MorphGNT / SBLGNT OSIS codes)
    "Matt": "MAT",
    "Mark": "MRK",
    "Luke": "LUK",
    "John": "JHN",
    "Acts": "ACT",
    "Rom": "ROM",
    "1Cor": "1CO",
    "2Cor": "2CO",
    "Gal": "GAL",
    "Eph": "EPH",
    "Phil": "PHP",
    "Col": "COL",
    "1Thess": "1TH",
    "2Thess": "2TH",
    "1Tim": "1TI",
    "2Tim": "2TI",
    "Titus": "TIT",
    "Phlm": "PHM",
    "Heb": "HEB",
    "Jas": "JAS",
    "1Pet": "1PE",
    "2Pet": "2PE",
    "1John": "1JN",
    "2John": "2JN",
    "3John": "3JN",
    "Jude": "JUD",
    "Rev": "REV",
}

LAMP_TO_OSIS = {v: k for k, v in OSIS_TO_LAMP.items()}

# Set of Lamp codes that belong to each canon; derived once for O(1) lookup.
_NT_CODES = {
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
}


def _canon_for(code: str) -> Canon:
    if code in _NT_CODES:
        return Canon.NT
    return Canon.TANAKH  # LXX-only deuterocanon additions come later


BOOK_CANON: dict[str, Canon] = {code: _canon_for(code) for code in LAMP_CODE_TO_NAME}


def osis_to_lamp(osis_code: str) -> str:
    """Convert an OSIS book code to Lamp canonical code. Raises KeyError on unknown."""
    return OSIS_TO_LAMP[osis_code]
