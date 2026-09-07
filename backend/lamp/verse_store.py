"""SQLite persistence for verse identity, original-language text, morphology, and
the KJV base text.

Three tables, and the relationship between them is the point:

    verse_refs    verse identity — book/chapter/verse/canon. One row per verse in
                  the corpus, whatever texts do or do not witness it.
      ├── verses       the ORIGINAL-LANGUAGE WITNESS (optional)
      │     └── verse_words   its morphology
      └── translations the KJV 1769 BASE TEXT

Both the witness and the base text hang off identity, so neither depends on the
other. Before 2026-09-07 `translations` hung off `verses`, which had two
consequences that contradicted Locked Decision 8 (the KJV is the base text):
deleting an original-language row destroyed the KJV attached to it, and a KJV
verse could not exist without one — so the 32 verses present in the KJV and
absent from the SBLGNT had to be given fabricated empty Greek rows.

Verse *nodes* live in the NetworkX graph (IDs + minimal metadata + edges); the
text lives here, keyed by verse ID.

Why separate from the graph:
  - Graph load stays fast — a ~150-node graph doesn't want ~23K verses × 15 words × 7 fields
    bloating the JSON by 3+ orders of magnitude.
  - Translation-history comparison ("show KJV, ASV, Geneva for this verse") is a SQL-native
    GROUP BY operation.
  - Physical separation keeps the base text distinguishable from the witnesses
    that support it, which is the exegesis/eisegesis discipline at the storage layer.

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
from lamp.models.verse import TranslationText, Verse, VerseRef, VerseWord


SCHEMA_SQL = """
-- ── Verse identity ──────────────────────────────────────────────────────────
-- One row per verse that exists in the corpus, independent of which texts
-- witness it. This is the spine every navigation query walks, and it is the
-- parent of BOTH the original-language witness and the KJV base text, so
-- neither depends on the other.
CREATE TABLE IF NOT EXISTS verse_refs (
    id         TEXT PRIMARY KEY,
    book       TEXT    NOT NULL,
    chapter    INTEGER NOT NULL,
    verse      INTEGER NOT NULL,
    canon      TEXT    NOT NULL,
    -- Notes about the verse itself rather than about a witness — e.g. "absent
    -- from the SBLGNT critical text". Witness-level notes (Masoretic ketiv/qere,
    -- accent and scribal notes, and the KJV: mapping markers that arrive in the
    -- OSHB source) live on `verses`. Two columns, one owner each, so the two
    -- ingest paths can never overwrite one another.
    notes_json TEXT    NOT NULL DEFAULT '[]',
    -- The verse's address in the KJV 1769, which is the base text (Locked
    -- Decision 8). book/chapter/verse above are the WITNESS's own numbering —
    -- Hebrew for the OT, where the two diverge for 2,027 verses. NULL means the
    -- KJV has no verse here: the 66 Hebrew superscriptions numbered as v.1.
    -- Written by the KJV ingest, which is the only thing that knows the mapping.
    kjv_book    TEXT,
    kjv_chapter INTEGER,
    kjv_verse   INTEGER
);


CREATE INDEX IF NOT EXISTS idx_verse_refs_bcv   ON verse_refs(book, chapter, verse);
CREATE INDEX IF NOT EXISTS idx_verse_refs_canon ON verse_refs(canon);

-- ── Original-language witness (OPTIONAL) ────────────────────────────────────
-- A verse may have no witness at all: 32 verses are in the KJV but absent from
-- the SBLGNT critical text. Before the 2026-09-07 split those 32 were forced to
-- carry a fabricated empty Greek row, because `translations` hung off this table
-- and a KJV verse could not exist without one. It no longer does.
CREATE TABLE IF NOT EXISTS verses (
    id               TEXT PRIMARY KEY,
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
    source_tier      INTEGER NOT NULL,
    FOREIGN KEY (id) REFERENCES verse_refs(id) ON DELETE CASCADE
);

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
    -- Words belong to the witness, so they go when the witness goes.
    FOREIGN KEY (verse_id) REFERENCES verses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_verse_words_strongs ON verse_words(strongs);
CREATE INDEX IF NOT EXISTS idx_verse_words_lemma   ON verse_words(lemma);

-- ── Base text ───────────────────────────────────────────────────────────────
-- The KJV 1769 (Locked Decision 8). Hangs off verse identity, NOT off the
-- original-language witness: deleting a witness must leave the base text
-- standing. It used to reference verses(id), so dropping a Hebrew or Greek row
-- silently destroyed the KJV text attached to it.
CREATE TABLE IF NOT EXISTS translations (
    translation TEXT    NOT NULL,
    verse_id    TEXT    NOT NULL,
    text        TEXT    NOT NULL,
    source      TEXT    NOT NULL,
    source_tier INTEGER NOT NULL,
    PRIMARY KEY (translation, verse_id),
    FOREIGN KEY (verse_id) REFERENCES verse_refs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_translations_verse ON translations(verse_id);
"""


# Schema migrations — applied in order on every connect(). Each entry is a column
# that a pre-Greek-addendum database (Phase 2C-1 schema) will be missing. The
# ADD COLUMN is wrapped in a try/except so re-runs on already-migrated databases
# are no-ops. Order within a table doesn't matter to SQLite.
#
# NOTE: this list can only ADD COLUMNS. The 2026-09-07 identity/witness split
# changes foreign keys, which SQLite cannot do with ALTER TABLE, so that runs as
# its own create-copy-drop-rename step in _migrate_split_identity_from_witness().
SCHEMA_MIGRATIONS: list[tuple[str, str, str]] = [
    ("verses",      "text_canonical",   "TEXT NOT NULL DEFAULT ''"),
    ("verses",      "text_plain",       "TEXT NOT NULL DEFAULT ''"),
    ("verses",      "text_accented",    "TEXT NOT NULL DEFAULT ''"),
    ("verse_words", "text_canonical",   "TEXT NOT NULL DEFAULT ''"),
    ("verse_words", "text_plain",       "TEXT NOT NULL DEFAULT ''"),
    ("verse_words", "text_accented",    "TEXT NOT NULL DEFAULT ''"),
    ("verse_words", "sblgnt_index",     "INTEGER"),
    # 2026-09-07 KJV addressing. Nullable additions, so ADD COLUMN is enough —
    # unlike the identity/witness split, which changed foreign keys and needed
    # its own create-copy-drop-rename.
    ("verse_refs",  "kjv_book",         "TEXT"),
    ("verse_refs",  "kjv_chapter",      "INTEGER"),
    ("verse_refs",  "kjv_verse",        "INTEGER"),
]


# Columns of `verse_refs` (identity) and `verses` (witness), id first in each.
# The upsert SQL below is built from these lists so the INSERT column list, the
# placeholder count and the DO UPDATE SET clause can never drift apart.
# test_upsert_covers_every_verse_column and its verse_refs twin compare them
# against PRAGMA table_info at run time, so adding a column to SCHEMA_SQL without
# adding it here fails the suite instead of silently going stale.
VERSE_REF_COLUMNS: list[str] = [
    "id",
    "book",
    "chapter",
    "verse",
    "canon",
    "notes_json",
    "kjv_book",
    "kjv_chapter",
    "kjv_verse",
]

VERSE_COLUMNS: list[str] = [
    "id",
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


def _build_upsert_sql(table: str, columns: list[str]) -> str:
    """Upsert keyed on `id` — deliberately NOT "INSERT OR REPLACE".

    SQLite implements REPLACE as DELETE-then-INSERT. With PRAGMA foreign_keys=ON
    that DELETE fires every ON DELETE CASCADE pointing at the row, so simply
    re-running an ingest script destroyed the attached translations (31,104 KJV
    rows) without reporting anything. ON CONFLICT(id) DO UPDATE edits the row in
    place, so child rows survive.
    """
    cols = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{c}=excluded.{c}" for c in columns if c != "id")
    return (
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}"
    )


VERSE_REF_UPSERT_SQL = _build_upsert_sql("verse_refs", VERSE_REF_COLUMNS)
VERSE_UPSERT_SQL = _build_upsert_sql("verses", VERSE_COLUMNS)


# Select list for composing a Verse from identity + optional witness. Aliased so
# the two notes_json columns stay distinguishable: identity notes describe the
# verse (e.g. "absent from the SBLGNT"), witness notes describe the text
# (Masoretic ketiv/qere, accent and scribal notes, KJV: mapping markers).
_VERSE_SELECT = (
    "r.id AS id, r.book AS book, r.chapter AS chapter, r.verse AS verse, "
    "r.canon AS canon, r.notes_json AS ref_notes_json, "
    "r.kjv_book AS kjv_book, r.kjv_chapter AS kjv_chapter, r.kjv_verse AS kjv_verse, "
    "v.language AS language, "
    "v.text_canonical AS text_canonical, "
    "v.text_consonantal AS text_consonantal, v.text_pointed AS text_pointed, "
    "v.text_cantillated AS text_cantillated, "
    "v.text_plain AS text_plain, v.text_accented AS text_accented, "
    "v.parashah_marker AS parashah_marker, v.reversed_nun AS reversed_nun, "
    "v.notes_json AS witness_notes_json, "
    "v.source AS source, v.source_tier AS source_tier"
)

# Display language for a verse with no witness. The witness would carry the real
# value; without one, the canon is the only honest signal.
_CANON_DEFAULT_LANGUAGE = {"tanakh": "hbo", "nt": "grc", "lxx": "grc"}


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
        # Indexes over migration-added columns must come AFTER the migrations.
        # On an existing database CREATE TABLE IF NOT EXISTS is a no-op, so those
        # columns do not exist while SCHEMA_SQL runs.
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verse_refs_kjv "
            "ON verse_refs(kjv_book, kjv_chapter, kjv_verse)"
        )
        self.conn.commit()
        self._migrate_split_identity_from_witness()

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

    def _migrate_split_identity_from_witness(self) -> None:
        """One-time 2026-09-07 migration: split verse identity from the witness.

        Before this, `verses` held both the verse's identity (book/chapter/verse/
        canon) and its original-language text, and `translations` hung off it with
        ON DELETE CASCADE. Two consequences, both contradicting Locked Decision 8:

          1. Deleting an original-language row destroyed the KJV base text
             attached to it.
          2. A KJV verse could not exist without an original-language row, so the
             32 verses present in the KJV but absent from the SBLGNT had to be
             given fabricated empty Greek rows to hang off.

        SQLite cannot change a foreign key with ALTER TABLE, so this is a
        create-copy-drop-rename. PRAGMA foreign_keys must be OFF around it — and
        that pragma is a no-op inside a transaction, so it is set outside one.

        A database already carrying the new shape is detected by the absence of a
        `book` column on `verses`, and the method returns without touching it.
        """
        conn = self._require()
        columns = {row[1] for row in conn.execute("PRAGMA table_info(verses)")}
        if "book" not in columns:
            return  # already split

        had_fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            with conn:
                # 1. Identity for every verse that exists today.
                conn.execute(
                    "INSERT OR IGNORE INTO verse_refs (id, book, chapter, verse, canon, notes_json) "
                    "SELECT id, book, chapter, verse, canon, "
                    # Notes move to identity only for rows that are about to lose
                    # their witness; everything else keeps them on the witness.
                    "       CASE WHEN COALESCE(text_canonical, '') = '' "
                    "            THEN notes_json ELSE '[]' END "
                    "FROM verses"
                )

                # 2. Witness rows — only verses that actually have text.
                conn.execute(
                    "CREATE TABLE verses_new ("
                    " id TEXT PRIMARY KEY,"
                    " language TEXT NOT NULL,"
                    " text_canonical TEXT NOT NULL DEFAULT '',"
                    " text_consonantal TEXT NOT NULL DEFAULT '',"
                    " text_pointed TEXT NOT NULL DEFAULT '',"
                    " text_cantillated TEXT NOT NULL DEFAULT '',"
                    " text_plain TEXT NOT NULL DEFAULT '',"
                    " text_accented TEXT NOT NULL DEFAULT '',"
                    " parashah_marker TEXT,"
                    " reversed_nun INTEGER NOT NULL DEFAULT 0,"
                    " notes_json TEXT NOT NULL DEFAULT '[]',"
                    " source TEXT NOT NULL,"
                    " source_tier INTEGER NOT NULL,"
                    " FOREIGN KEY (id) REFERENCES verse_refs(id) ON DELETE CASCADE)"
                )
                conn.execute(
                    "INSERT INTO verses_new SELECT id, language, text_canonical, "
                    "text_consonantal, text_pointed, text_cantillated, text_plain, "
                    "text_accented, parashah_marker, reversed_nun, notes_json, "
                    "source, source_tier FROM verses "
                    "WHERE COALESCE(text_canonical, '') <> ''"
                )
                conn.execute("DROP TABLE verses")
                conn.execute("ALTER TABLE verses_new RENAME TO verses")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_verses_language ON verses(language)"
                )

                # 3. Repoint translations at identity instead of the witness.
                conn.execute(
                    "CREATE TABLE translations_new ("
                    " translation TEXT NOT NULL,"
                    " verse_id TEXT NOT NULL,"
                    " text TEXT NOT NULL,"
                    " source TEXT NOT NULL,"
                    " source_tier INTEGER NOT NULL,"
                    " PRIMARY KEY (translation, verse_id),"
                    " FOREIGN KEY (verse_id) REFERENCES verse_refs(id) ON DELETE CASCADE)"
                )
                conn.execute(
                    "INSERT INTO translations_new SELECT translation, verse_id, text, "
                    "source, source_tier FROM translations"
                )
                conn.execute("DROP TABLE translations")
                conn.execute("ALTER TABLE translations_new RENAME TO translations")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_translations_verse "
                    "ON translations(verse_id)"
                )
        finally:
            conn.execute(f"PRAGMA foreign_keys={'ON' if had_fk else 'OFF'}")

        # Refuse to hand back a database whose references do not resolve.
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(
                f"identity/witness split left {len(violations)} foreign-key "
                f"violation(s); first: {violations[0]}"
            )

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def _require(self) -> sqlite3.Connection:
        if self.conn is None:
            raise RuntimeError("VerseStore not connected; call connect() first")
        return self.conn

    # ── Insert ────────────────────────────────────────────────

    def insert_verse_refs(self, refs: Iterable[VerseRef]) -> int:
        """Create verse identities without any original-language witness.

        This is what a KJV-only verse needs: Acts 8:37 and 31 others are in the
        KJV but absent from the SBLGNT critical text. Before the identity/witness
        split they had to be given a fabricated empty Greek row in `verses`, purely
        so the KJV text had a parent to hang off. Now the identity is enough.
        """
        conn = self._require()
        rows = [
            (r.id, r.book, r.chapter, r.verse, str(r.canon),
             json.dumps(r.notes, ensure_ascii=False),
             r.kjv_book, r.kjv_chapter, r.kjv_verse)
            for r in refs
        ]
        if not rows:
            return 0
        with conn:
            conn.executemany(VERSE_REF_UPSERT_SQL, rows)
        return len(rows)

    def insert_verses(self, verses: Iterable[Verse]) -> int:
        """Batch insert of original-language witnesses. Returns count.

        Writes identity first, then the witness, in one transaction — a witness
        row cannot exist without its identity row, and the FK enforces that.
        """
        conn = self._require()
        verses_list = list(verses)
        if not verses_list:
            return 0

        ref_rows = [
            (
                v.id, v.book, v.chapter, v.verse, str(v.canon),
                # Identity-level notes are owned by insert_verse_refs. An ingest
                # writing a witness must not clobber them, so it preserves
                # whatever is already there and defaults to empty.
                None,
            )
            for v in verses_list
        ]
        verse_rows = [
            (
                v.id, v.language,
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
            # Identity first — the witness FK depends on it. COALESCE keeps any
            # identity-level notes already stored rather than resetting them.
            conn.executemany(
                "INSERT INTO verse_refs (id, book, chapter, verse, canon, notes_json) "
                "VALUES (?, ?, ?, ?, ?, COALESCE(?, '[]')) "
                "ON CONFLICT(id) DO UPDATE SET "
                "book=excluded.book, chapter=excluded.chapter, verse=excluded.verse, "
                "canon=excluded.canon, "
                "notes_json=COALESCE(excluded.notes_json, verse_refs.notes_json)",
                ref_rows,
            )
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
        # LEFT JOIN: a verse with identity but no original-language witness is a
        # real verse (the 32 KJV-only ones), and must not read as "not found".
        vrow = conn.execute(
            f"SELECT {_VERSE_SELECT} FROM verse_refs r "
            "LEFT JOIN verses v ON v.id = r.id WHERE r.id = ?",
            (verse_id,),
        ).fetchone()
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
            f"SELECT {_VERSE_SELECT} FROM verse_refs r "
            f"LEFT JOIN verses v ON v.id = r.id WHERE r.id IN ({placeholder})",
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

    def count_witnesses(self) -> int:
        """Number of original-language witness rows — fewer than count_verses()."""
        return self._require().execute("SELECT COUNT(*) FROM verses").fetchone()[0]

    def set_kjv_addresses(self, addresses: dict[str, tuple[str, int, int]]) -> int:
        """Record each verse's address in the KJV base text.

        Called by the KJV ingest, which is the only thing that knows the mapping.
        Verses absent from `addresses` are left alone rather than nulled, so the
        OT and NT ingests can each write their own half.
        """
        conn = self._require()
        rows = [(b, c, v, vid) for vid, (b, c, v) in addresses.items()]
        if not rows:
            return 0
        with conn:
            conn.executemany(
                "UPDATE verse_refs SET kjv_book=?, kjv_chapter=?, kjv_verse=? WHERE id=?",
                rows,
            )
        return len(rows)

    def clear_kjv_addresses(self, canon: str) -> int:
        """Blank the KJV address for one canon before a reseed.

        Without this a verse that stops being a KJV target keeps a stale address,
        the same way translations kept stale rows before the OT ingest learned to
        delete them.
        """
        conn = self._require()
        with conn:
            cur = conn.execute(
                "UPDATE verse_refs SET kjv_book=NULL, kjv_chapter=NULL, kjv_verse=NULL "
                "WHERE canon = ?",
                (canon,),
            )
        return cur.rowcount

    def id_for_kjv_reference(self, book: str, chapter: int, verse: int) -> str | None:
        """Resolve a KJV reference to a verse id.

        Not a bijection: 5 KJV verses attach to two Hebrew verses each
        (`extra_targets`), so more than one row can claim the same address. The
        ORDER BY makes the answer deterministic — the first Hebrew verse of the
        span — rather than whichever row the engine returns first.
        """
        row = self._require().execute(
            "SELECT id FROM verse_refs WHERE kjv_book=? AND kjv_chapter=? AND kjv_verse=? "
            "ORDER BY chapter, verse LIMIT 1",
            (book, chapter, verse),
        ).fetchone()
        return row[0] if row else None

    def verse_ids_without_witness(self) -> set[str]:
        """Verses that exist but have no original-language text.

        These are the KJV-only verses: present in the base text, absent from the
        SBLGNT critical text. Replaces the old verse_ids_by_source() lookup, which
        identified them by the source string stamped on their fabricated witness
        row — rows that no longer exist.
        """
        return {
            row[0]
            for row in self._require().execute(
                "SELECT r.id FROM verse_refs r "
                "LEFT JOIN verses v ON v.id = r.id WHERE v.id IS NULL"
            )
        }

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
            return conn.execute("SELECT COUNT(*) FROM verse_refs").fetchone()[0]
        return conn.execute(
            "SELECT COUNT(*) FROM verse_refs WHERE canon = ?", (canon,)
        ).fetchone()[0]

    def count_words(self) -> int:
        return self._require().execute("SELECT COUNT(*) FROM verse_words").fetchone()[0]

    def count_by_book(self) -> dict[str, int]:
        rows = self._require().execute(
            "SELECT book, COUNT(*) FROM verse_refs GROUP BY book ORDER BY book"
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def books_summary(self) -> list[dict]:
        """One row per book currently ingested. Used by the navigation UI.

        Returns: book, canon, language, chapter_count, verse_count.
        """
        rows = self._require().execute(
            # Counts come from identity so a KJV-only verse is still counted.
            # `language` is a property of the witness, so it is taken as the
            # commonest witness language in the book via MAX() over the join;
            # grouping BY language here would split a book in two the moment one
            # of its verses had no witness.
            "SELECT r.book AS book, r.canon AS canon, "
            "       MAX(v.language) AS language, "
            "       MAX(r.chapter) AS chapter_count, "
            "       COUNT(*) AS verse_count "
            "FROM verse_refs r LEFT JOIN verses v ON v.id = r.id "
            "GROUP BY r.book, r.canon "
            "ORDER BY r.book"
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
            canon_filter = " AND r.canon = ?"
            canon_params.append(canon)

        count_sql = (
            f"SELECT COUNT(DISTINCT v.id) FROM verse_words w "
            f"JOIN verses v ON w.verse_id = v.id "
            f"JOIN verse_refs r ON r.id = v.id "
            f"WHERE {where_clause}{canon_filter}"
        )
        total = conn.execute(count_sql, (param, *canon_params)).fetchone()[0]

        # Canonical book order baked into SQL via a CASE — Python dict is
        # source of truth, we emit WHEN/THEN pairs for each book. Keeps pagination
        # consistent with in-UI expected ordering (Gen → Mal → Matt → Rev).
        order_case = "CASE r.book " + " ".join(
            f"WHEN '{code}' THEN {idx}" for code, idx in BOOK_ORDER.items()
        ) + " ELSE 999 END"
        query_sql = (
            "SELECT v.id AS id, r.book AS book, r.chapter AS chapter, "
            "r.verse AS verse, r.canon AS canon, v.language AS language, "
            "v.text_canonical AS text_canonical, "
            "GROUP_CONCAT(w.position) AS positions, "
            "COUNT(*) AS match_count "
            "FROM verse_words w "
            "JOIN verses v ON w.verse_id = v.id "
            "JOIN verse_refs r ON r.id = v.id "
            f"WHERE {where_clause}{canon_filter} "
            "GROUP BY v.id, r.book, r.chapter, r.verse, r.canon, v.language, v.text_canonical "
            f"ORDER BY {order_case}, r.chapter, r.verse "
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
            "SELECT r.id AS id, r.verse AS verse, "
            "       COALESCE(v.text_canonical, '') AS text_canonical, "
            "       v.parashah_marker AS parashah_marker, "
            "       COALESCE(v.reversed_nun, 0) AS reversed_nun "
            "FROM verse_refs r LEFT JOIN verses v ON v.id = r.id "
            "WHERE r.book = ? AND r.chapter = ? "
            "ORDER BY r.verse",
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
            "SELECT book, chapter, verse FROM verse_refs WHERE id = ?", (verse_id,)
        ).fetchone()
        if not row:
            return None
        result = conn.execute(
            "SELECT id FROM verse_refs WHERE book = ? AND "
            "(chapter < ? OR (chapter = ? AND verse < ?)) "
            "ORDER BY chapter DESC, verse DESC LIMIT 1",
            (row["book"], row["chapter"], row["chapter"], row["verse"]),
        ).fetchone()
        return result["id"] if result else None

    def next_verse_id(self, verse_id: str) -> str | None:
        """Return the id of the verse immediately after this one, within the same book."""
        conn = self._require()
        row = conn.execute(
            "SELECT book, chapter, verse FROM verse_refs WHERE id = ?", (verse_id,)
        ).fetchone()
        if not row:
            return None
        result = conn.execute(
            "SELECT id FROM verse_refs WHERE book = ? AND "
            "(chapter > ? OR (chapter = ? AND verse > ?)) "
            "ORDER BY chapter ASC, verse ASC LIMIT 1",
            (row["book"], row["chapter"], row["chapter"], row["verse"]),
        ).fetchone()
        return result["id"] if result else None


def _row_to_verse(row: Any, word_rows: list[Any]) -> Verse:
    """Compose a Verse from an identity row LEFT JOINed to its witness.

    Every `v.*` column is None when the verse has no original-language witness,
    so each one needs a default. Identity notes come first, then witness notes.
    """
    canon = row["canon"]
    return Verse(
        id=row["id"],
        book=row["book"],
        chapter=row["chapter"],
        verse=row["verse"],
        canon=Canon(canon),
        language=row["language"] or _CANON_DEFAULT_LANGUAGE.get(canon, "grc"),
        text_canonical=row["text_canonical"] or "",
        text_consonantal=row["text_consonantal"] or "",
        text_pointed=row["text_pointed"] or "",
        text_cantillated=row["text_cantillated"] or "",
        text_plain=row["text_plain"] or "",
        text_accented=row["text_accented"] or "",
        parashah_marker=row["parashah_marker"],
        reversed_nun=bool(row["reversed_nun"]),
        notes=(
            json.loads(row["ref_notes_json"] or "[]")
            + json.loads(row["witness_notes_json"] or "[]")
        ),
        source=row["source"],
        source_tier=row["source_tier"],
        kjv_book=row["kjv_book"],
        kjv_chapter=row["kjv_chapter"],
        kjv_verse=row["kjv_verse"],
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
