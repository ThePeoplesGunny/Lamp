"""SQLite persistence for verse text, per-word morphology, and translation layers.

Canonical verse *nodes* live in the NetworkX graph (IDs + minimal metadata + edges).
Verse *text* and word-level morphology live here, keyed by verse ID.
Translations also live here, keyed by (translation, verse_id).

Why separate from the graph:
  - Graph load stays fast — a ~150-node graph doesn't want ~23K verses × 15 words × 7 fields
    bloating the JSON by 3+ orders of magnitude.
  - Translation-history comparison ("show KJV, ASV, Geneva for this verse") is a SQL-native
    GROUP BY operation.
  - Physical separation enforces the exegesis/eisegesis discipline at the storage layer:
    canonical original-language text on the verse node, translations as reference data.

Use only via GraphStore. Graph structure and verse text must stay consistent;
GraphStore is the coordinator.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from lamp.models.book_codes import BOOK_ORDER, Canon
from lamp.models.verse import TranslationText, Verse, VerseWord


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS verses (
    id               TEXT PRIMARY KEY,
    book             TEXT    NOT NULL,
    chapter          INTEGER NOT NULL,
    verse            INTEGER NOT NULL,
    canon            TEXT    NOT NULL,
    language         TEXT    NOT NULL,
    text_canonical   TEXT    NOT NULL DEFAULT '',
    text_consonantal TEXT    NOT NULL DEFAULT '',
    text_pointed     TEXT    NOT NULL DEFAULT '',
    text_cantillated TEXT    NOT NULL DEFAULT '',
    text_plain       TEXT    NOT NULL DEFAULT '',
    text_accented    TEXT    NOT NULL DEFAULT '',
    parashah_marker  TEXT,
    reversed_nun     INTEGER NOT NULL DEFAULT 0,
    notes_json       TEXT    NOT NULL DEFAULT '[]',
    source           TEXT    NOT NULL,
    source_tier      INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verses_bcv      ON verses(book, chapter, verse);
CREATE INDEX IF NOT EXISTS idx_verses_canon    ON verses(canon);
CREATE INDEX IF NOT EXISTS idx_verses_language ON verses(language);

CREATE TABLE IF NOT EXISTS verse_words (
    verse_id         TEXT    NOT NULL,
    position         INTEGER NOT NULL,
    text_canonical   TEXT    NOT NULL DEFAULT '',
    text_consonantal TEXT    NOT NULL DEFAULT '',
    text_pointed     TEXT    NOT NULL DEFAULT '',
    text_cantillated TEXT    NOT NULL DEFAULT '',
    text_plain       TEXT    NOT NULL DEFAULT '',
    text_accented    TEXT    NOT NULL DEFAULT '',
    lemma            TEXT,
    strongs          TEXT,
    morph_code       TEXT,
    transliteration  TEXT,
    oshb_word_id     TEXT,
    sblgnt_index     INTEGER,
    text_ketiv       TEXT,
    text_qere        TEXT,
    PRIMARY KEY (verse_id, position),
    FOREIGN KEY (verse_id) REFERENCES verses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_verse_words_strongs ON verse_words(strongs);
CREATE INDEX IF NOT EXISTS idx_verse_words_lemma   ON verse_words(lemma);

CREATE TABLE IF NOT EXISTS translations (
    translation TEXT    NOT NULL,
    verse_id    TEXT    NOT NULL,
    text        TEXT    NOT NULL,
    source      TEXT    NOT NULL,
    source_tier INTEGER NOT NULL,
    PRIMARY KEY (translation, verse_id),
    FOREIGN KEY (verse_id) REFERENCES verses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_translations_verse ON translations(verse_id);
"""


# Schema migrations — applied in order on every connect(). Each entry is a column
# that a pre-Greek-addendum database (Phase 2C-1 schema) will be missing. The
# ADD COLUMN is wrapped in a try/except so re-runs on already-migrated databases
# are no-ops. Order within a table doesn't matter to SQLite.
SCHEMA_MIGRATIONS: list[tuple[str, str, str]] = [
    ("verses",      "text_canonical",   "TEXT NOT NULL DEFAULT ''"),
    ("verses",      "text_plain",       "TEXT NOT NULL DEFAULT ''"),
    ("verses",      "text_accented",    "TEXT NOT NULL DEFAULT ''"),
    ("verse_words", "text_canonical",   "TEXT NOT NULL DEFAULT ''"),
    ("verse_words", "text_plain",       "TEXT NOT NULL DEFAULT ''"),
    ("verse_words", "text_accented",    "TEXT NOT NULL DEFAULT ''"),
    ("verse_words", "sblgnt_index",     "INTEGER"),
]


# Columns of the `verses` table, id first. VERSE_UPSERT_SQL is built from this
# list so the INSERT column list, the placeholder count and the DO UPDATE SET
# clause can never drift apart. test_upsert_covers_every_verse_column compares
# it against PRAGMA table_info at run time, so adding a column to SCHEMA_SQL
# without adding it here fails the suite instead of silently going stale.
VERSE_COLUMNS: list[str] = [
    "id",
    "book",
    "chapter",
    "verse",
    "canon",
    "language",
    "text_canonical",
    "text_consonantal",
    "text_pointed",
    "text_cantillated",
    "text_plain",
    "text_accented",
    "parashah_marker",
    "reversed_nun",
    "notes_json",
    "source",
    "source_tier",
]


def _build_verse_upsert_sql() -> str:
    """Upsert for `verses` — deliberately NOT "INSERT OR REPLACE".

    SQLite implements REPLACE as DELETE-then-INSERT. With PRAGMA foreign_keys=ON
    that DELETE fires ON DELETE CASCADE on translations.verse_id and verse_words,
    so simply re-running an ingest script destroyed every attached translation
    (31,104 KJV rows) without reporting anything. ON CONFLICT(id) DO UPDATE edits
    the existing row in place, so child rows survive.
    """
    cols = ", ".join(VERSE_COLUMNS)
    placeholders = ", ".join("?" for _ in VERSE_COLUMNS)
    updates = ", ".join(
        f"{c}=excluded.{c}" for c in VERSE_COLUMNS if c != "id"
    )
    return (
        f"INSERT INTO verses ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}"
    )


VERSE_UPSERT_SQL = _build_verse_upsert_sql()


class VerseStore:
    """SQLite-backed verse text + translation store.

    Pass db_path=None for in-memory (tests). Pass a Path for persistence.
    """

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        target = ":memory:" if self.db_path is None else str(self.db_path)
        # check_same_thread=False: FastAPI runs endpoints in a thread pool; reads are safe
        # against the single WAL-mode SQLite connection. Writes go through insert_verses
        # (batch, transactional), which is only called from ingest scripts, not the API.
        self.conn = sqlite3.connect(target, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        if self.db_path is not None:
            self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.executescript(SCHEMA_SQL)
        self._apply_migrations()
        self.conn.commit()

    def _apply_migrations(self) -> None:
        """Apply schema additions (new columns) to pre-existing databases."""
        assert self.conn is not None
        for table, column, coldef in SCHEMA_MIGRATIONS:
            existing = {
                row[1]
                for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if column not in existing:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}")

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def _require(self) -> sqlite3.Connection:
        if self.conn is None:
            raise RuntimeError("VerseStore not connected; call connect() first")
        return self.conn

    # ── Insert ────────────────────────────────────────────────

    def insert_verses(self, verses: Iterable[Verse]) -> int:
        """Batch insert. Replaces existing rows with the same id. Returns count."""
        conn = self._require()
        verses_list = list(verses)
        if not verses_list:
            return 0

        verse_rows = [
            (
                v.id, v.book, v.chapter, v.verse, str(v.canon), v.language,
                v.text_canonical,
                v.text_consonantal, v.text_pointed, v.text_cantillated,
                v.text_plain, v.text_accented,
                v.parashah_marker,
                1 if v.reversed_nun else 0,
                json.dumps(v.notes, ensure_ascii=False),
                v.source, v.source_tier,
            )
            for v in verses_list
        ]
        word_rows = [
            (
                v.id, w.position,
                w.text_canonical,
                w.text_consonantal, w.text_pointed, w.text_cantillated,
                w.text_plain, w.text_accented,
                w.lemma, w.strongs, w.morph_code, w.transliteration,
                w.oshb_word_id, w.sblgnt_index,
                w.text_ketiv, w.text_qere,
            )
            for v in verses_list for w in v.words
        ]

        with conn:
            conn.executemany(
                VERSE_UPSERT_SQL,
                verse_rows,
            )
            verse_ids = [row[0] for row in verse_rows]
            placeholder = ",".join("?" for _ in verse_ids)
            conn.execute(
                f"DELETE FROM verse_words WHERE verse_id IN ({placeholder})",
                verse_ids,
            )
            if word_rows:
                conn.executemany(
                    "INSERT INTO verse_words "
                    "(verse_id, position, text_canonical, "
                    "text_consonantal, text_pointed, text_cantillated, "
                    "text_plain, text_accented, "
                    "lemma, strongs, morph_code, transliteration, "
                    "oshb_word_id, sblgnt_index, "
                    "text_ketiv, text_qere) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    word_rows,
                )
        return len(verse_rows)

    def insert_translations(self, translations: Iterable[TranslationText]) -> int:
        conn = self._require()
        rows = [
            (t.translation, t.verse_id, t.text, t.source, t.source_tier)
            for t in translations
        ]
        if not rows:
            return 0
        with conn:
            conn.executemany(
                "INSERT OR REPLACE INTO translations "
                "(translation, verse_id, text, source, source_tier) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    # ── Query ─────────────────────────────────────────────────

    def get_verse(self, verse_id: str) -> Verse | None:
        conn = self._require()
        vrow = conn.execute("SELECT * FROM verses WHERE id = ?", (verse_id,)).fetchone()
        if not vrow:
            return None
        wrows = conn.execute(
            "SELECT * FROM verse_words WHERE verse_id = ? ORDER BY position",
            (verse_id,),
        ).fetchall()
        return _row_to_verse(vrow, wrows)

    def get_verses(self, verse_ids: Iterable[str]) -> list[Verse]:
        conn = self._require()
        ids = list(verse_ids)
        if not ids:
            return []
        placeholder = ",".join("?" for _ in ids)
        vrows = conn.execute(
            f"SELECT * FROM verses WHERE id IN ({placeholder})",
            ids,
        ).fetchall()
        words_by_id: dict[str, list[sqlite3.Row]] = {}
        for row in conn.execute(
            f"SELECT * FROM verse_words WHERE verse_id IN ({placeholder}) "
            f"ORDER BY verse_id, position",
            ids,
        ).fetchall():
            words_by_id.setdefault(row["verse_id"], []).append(row)
        return [_row_to_verse(vr, words_by_id.get(vr["id"], [])) for vr in vrows]

    def verse_ids_by_source(self, source: str) -> set[str]:
        """Every verse id stamped with this exact `source` string.

        Used by the KJV ingest to find the placeholder slots it created on an
        earlier run, so it can refresh them instead of skipping them. The source
        string is the safe discriminator: a slot carries the KJV file as its
        source, while a real verse carries OSHB-WLC or MorphGNT-SBLGNT, so this
        can never select a verse that holds actual Hebrew or Greek text.
        """
        conn = self._require()
        return {
            row[0]
            for row in conn.execute("SELECT id FROM verses WHERE source = ?", (source,))
        }

    def get_translations_for_verse(self, verse_id: str) -> list[TranslationText]:
        conn = self._require()
        rows = conn.execute(
            "SELECT * FROM translations WHERE verse_id = ? ORDER BY translation",
            (verse_id,),
        ).fetchall()
        return [
            TranslationText(
                translation=r["translation"],
                verse_id=r["verse_id"],
                text=r["text"],
                source=r["source"],
                source_tier=r["source_tier"],
            )
            for r in rows
        ]

    # ── Stats ─────────────────────────────────────────────────

    def count_verses(self, canon: str | None = None) -> int:
        """Number of verse rows, optionally restricted to one canon.

        The canon filter exists because a whole-table count is the wrong
        comparison for a single-corpus ingest: seed_verses.py checked its 23,213
        parsed Hebrew verses against every row in the database, so from the moment
        the Greek NT was added it reported ISSUES DETECTED and exited 1 on every
        successful run.
        """
        conn = self._require()
        if canon is None:
            return conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
        return conn.execute(
            "SELECT COUNT(*) FROM verses WHERE canon = ?", (canon,)
        ).fetchone()[0]

    def count_words(self) -> int:
        return self._require().execute("SELECT COUNT(*) FROM verse_words").fetchone()[0]

    def count_by_book(self) -> dict[str, int]:
        rows = self._require().execute(
            "SELECT book, COUNT(*) FROM verses GROUP BY book ORDER BY book"
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def books_summary(self) -> list[dict]:
        """One row per book currently ingested. Used by the navigation UI.

        Returns: book, canon, language, chapter_count, verse_count.
        """
        rows = self._require().execute(
            "SELECT book, canon, language, MAX(chapter) AS chapter_count, "
            "COUNT(*) AS verse_count "
            "FROM verses "
            "GROUP BY book, canon, language "
            "ORDER BY book"
        ).fetchall()
        return [
            {
                "book": r["book"],
                "canon": r["canon"],
                "language": r["language"],
                "chapter_count": r["chapter_count"],
                "verse_count": r["verse_count"],
            }
            for r in rows
        ]

    # ── Lexeme search (concordance) ───────────────────────────

    def occurrences(
        self,
        lemma: str | None = None,
        strongs: str | None = None,
        canon: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Find every verse where a lemma or Strong's number appears.

        Exactly one of `lemma` or `strongs` must be provided. Returns a
        (results, total_count) tuple — results are paginated, total is the
        full match count regardless of limit.

        Each result: {verse_id, book, chapter, verse, canon, language,
                       text_canonical, positions: [int...], match_count}.
        Sorted by canon order (Tanakh before NT), then book, chapter, verse.
        """
        if (lemma is None) == (strongs is None):
            raise ValueError("Exactly one of lemma or strongs must be provided")

        conn = self._require()
        if lemma is not None:
            where_clause = "w.lemma = ?"
            param = lemma
        else:
            where_clause = "w.strongs = ?"
            param = strongs

        canon_filter = ""
        canon_params: list[str] = []
        if canon and canon != "all":
            canon_filter = " AND v.canon = ?"
            canon_params.append(canon)

        count_sql = (
            f"SELECT COUNT(DISTINCT v.id) FROM verse_words w "
            f"JOIN verses v ON w.verse_id = v.id "
            f"WHERE {where_clause}{canon_filter}"
        )
        total = conn.execute(count_sql, (param, *canon_params)).fetchone()[0]

        # Canonical book order baked into SQL via a CASE — Python dict is
        # source of truth, we emit WHEN/THEN pairs for each book. Keeps pagination
        # consistent with in-UI expected ordering (Gen → Mal → Matt → Rev).
        order_case = "CASE v.book " + " ".join(
            f"WHEN '{code}' THEN {idx}" for code, idx in BOOK_ORDER.items()
        ) + " ELSE 999 END"
        query_sql = (
            "SELECT v.id, v.book, v.chapter, v.verse, v.canon, v.language, "
            "v.text_canonical, "
            "GROUP_CONCAT(w.position) AS positions, "
            "COUNT(*) AS match_count "
            "FROM verse_words w "
            "JOIN verses v ON w.verse_id = v.id "
            f"WHERE {where_clause}{canon_filter} "
            "GROUP BY v.id, v.book, v.chapter, v.verse, v.canon, v.language, v.text_canonical "
            f"ORDER BY {order_case}, v.chapter, v.verse "
            "LIMIT ? OFFSET ?"
        )
        rows = conn.execute(
            query_sql, (param, *canon_params, limit, offset),
        ).fetchall()

        results = [
            {
                "verse_id": r["id"],
                "book": r["book"],
                "chapter": r["chapter"],
                "verse": r["verse"],
                "canon": r["canon"],
                "language": r["language"],
                "text_canonical": r["text_canonical"],
                "positions": [int(p) for p in r["positions"].split(",")],
                "match_count": r["match_count"],
            }
            for r in rows
        ]
        return results, total

    def chapter_verses(self, book: str, chapter: int) -> list[dict]:
        """Lightweight verse list for a chapter — id, number, canonical text only.

        Heavy fields (per-word morphology, three-layer text) are NOT loaded;
        callers that need them fetch the verse individually.
        """
        rows = self._require().execute(
            "SELECT id, verse, text_canonical, parashah_marker, reversed_nun "
            "FROM verses WHERE book = ? AND chapter = ? "
            "ORDER BY verse",
            (book, chapter),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "verse": r["verse"],
                "text_canonical": r["text_canonical"],
                "parashah_marker": r["parashah_marker"],
                "reversed_nun": bool(r["reversed_nun"]),
            }
            for r in rows
        ]

    # ── Navigation ────────────────────────────────────────────

    def prev_verse_id(self, verse_id: str) -> str | None:
        """Return the id of the verse immediately before this one, within the same book."""
        conn = self._require()
        row = conn.execute(
            "SELECT book, chapter, verse FROM verses WHERE id = ?", (verse_id,)
        ).fetchone()
        if not row:
            return None
        result = conn.execute(
            "SELECT id FROM verses WHERE book = ? AND "
            "(chapter < ? OR (chapter = ? AND verse < ?)) "
            "ORDER BY chapter DESC, verse DESC LIMIT 1",
            (row["book"], row["chapter"], row["chapter"], row["verse"]),
        ).fetchone()
        return result["id"] if result else None

    def next_verse_id(self, verse_id: str) -> str | None:
        """Return the id of the verse immediately after this one, within the same book."""
        conn = self._require()
        row = conn.execute(
            "SELECT book, chapter, verse FROM verses WHERE id = ?", (verse_id,)
        ).fetchone()
        if not row:
            return None
        result = conn.execute(
            "SELECT id FROM verses WHERE book = ? AND "
            "(chapter > ? OR (chapter = ? AND verse > ?)) "
            "ORDER BY chapter ASC, verse ASC LIMIT 1",
            (row["book"], row["chapter"], row["chapter"], row["verse"]),
        ).fetchone()
        return result["id"] if result else None


def _row_to_verse(row: Any, word_rows: list[Any]) -> Verse:
    return Verse(
        id=row["id"],
        book=row["book"],
        chapter=row["chapter"],
        verse=row["verse"],
        canon=Canon(row["canon"]),
        language=row["language"],
        text_canonical=row["text_canonical"],
        text_consonantal=row["text_consonantal"],
        text_pointed=row["text_pointed"],
        text_cantillated=row["text_cantillated"],
        text_plain=row["text_plain"],
        text_accented=row["text_accented"],
        parashah_marker=row["parashah_marker"],
        reversed_nun=bool(row["reversed_nun"]),
        notes=json.loads(row["notes_json"]),
        source=row["source"],
        source_tier=row["source_tier"],
        words=[_row_to_word(w) for w in word_rows],
    )


def _row_to_word(row: Any) -> VerseWord:
    return VerseWord(
        position=row["position"],
        text_canonical=row["text_canonical"],
        text_consonantal=row["text_consonantal"],
        text_pointed=row["text_pointed"],
        text_cantillated=row["text_cantillated"],
        text_plain=row["text_plain"],
        text_accented=row["text_accented"],
        lemma=row["lemma"],
        strongs=row["strongs"],
        morph_code=row["morph_code"],
        transliteration=row["transliteration"],
        oshb_word_id=row["oshb_word_id"],
        sblgnt_index=row["sblgnt_index"],
        text_ketiv=row["text_ketiv"],
        text_qere=row["text_qere"],
    )
