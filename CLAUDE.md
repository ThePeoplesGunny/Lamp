# Lamp — Project Instructions

## Overview
Biblical analytical tool — investigation platform for original Hebrew/Greek texts. Strips noise, surfaces patterns, connections, and structures not visible through translation.

## Architecture
- **Backend:** FastAPI + Python 3.12, NetworkX graph engine, JSON graph + SQLite verse store
- **Frontend:** React 19 + TypeScript + Vite, React Flow (genealogy trees), Tailwind CSS 4
- **Data model:** Property graph — Person, Place, Nation, Event, **Verse** nodes connected by typed directed edges. Verses are first-class nodes and the core engine (Phase 2C-1).
- **Persistence split:** graph structure (nodes + edges) lives in `backend/data/graphs/lamp.json`; verse text (three-layer Hebrew + per-word morphology) and translations live in `backend/data/verses/verses.db` keyed by verse ID. GraphStore coordinates both.

## Project Structure
```
backend/
  docs/           # Design docs (schema, architecture decisions)
  lamp/           # Python package
    main.py       # FastAPI app
    config.py     # Paths and settings
    verse_store.py  # SQLite persistence for verse text, morphology, translations
    models/       # Pydantic models (nodes, edges, verses, book codes)
    graph/        # NetworkX graph store and queries (coordinates VerseStore)
    api/          # FastAPI route modules
    ingest/       # Data loading: seed data, OSHB XML parser
    services/     # Business logic
  data/
    seed/         # Hand-curated JSON seed data
    external/     # Downloaded open datasets incl. OSHB (gitignored)
    graphs/       # Serialized NetworkX graph (gitignored)
    verses/       # SQLite verse/translations store (gitignored)
  tests/
frontend/
  src/
    components/   # React components by feature
    api/          # API client
    hooks/        # React hooks
    types/        # TypeScript types
scripts/
  dev.sh              # Start both servers (bash)
  dev.bat             # Start both servers (Windows)
  seed_graph.py       # Rebuild entity graph from seed data
  seed_verses.py      # Rebuild Hebrew OT verse nodes + SQLite from OSHB source
  seed_verses_nt.py   # Rebuild Greek NT verse nodes + SQLite from MorphGNT source
  seed_verse_links.py # Create MENTIONS edges from entity scripture_refs to verse nodes
```

## Running
- Backend: `cd backend && python -m uvicorn lamp.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Both (bash): `bash scripts/dev.sh`
- Both (Windows): `scripts\dev.bat`
- Rebuild entity graph: `python scripts/seed_graph.py`
- Rebuild Hebrew OT verses: `python scripts/seed_verses.py` (requires OSHB cloned into `backend/data/external/morphhb/`)
- Rebuild Greek NT verses: `python scripts/seed_verses_nt.py` (requires MorphGNT cloned into `backend/data/external/morphgnt/`)
- API docs: http://localhost:8000/docs

## External data sources
- **OSHB (Open Scriptures Hebrew Bible)** — `github.com/openscriptures/morphhb`. Provides Westminster Leningrad Codex in OSIS XML with per-word lemma, Strong's, and morphology. Text is public domain; lemma/morph data is CC-BY-4.0 (must credit OSHB). Clone into `backend/data/external/morphhb/`. Exact commit captured in each verse's `source` field for provenance.
- **MorphGNT / SBLGNT** — `github.com/morphgnt/sblgnt`. SBL Greek New Testament with per-word parsing and lemmatization. **License structure differs from OSHB:** the SBLGNT text itself is governed by the [SBLGNT EULA](http://sblgnt.com/license/) (permits non-commercial academic/personal/research use with attribution — *not* CC-BY); the morphological parsing and lemmatization is CC-BY-**SA** 3.0 (Share-Alike). Implication: if Lamp is ever publicly released, the SA clause forces a CC-BY-SA-3.0-compatible license for derivatives using the MorphGNT data. Clone into `backend/data/external/morphgnt/`. Exact commit captured per verse.
- **KJV 1769** — downloaded from `scrollmapper/bible_databases` (formats/json/KJV.json). Public domain — King James Version 1769 Oxford edition. Used as the primary translation-history reference layer. Stored in the `translations` table keyed by (`KJV-1769`, verse_id). Currently NT only; OT deferred to Phase 2C-6 pending Hebrew↔English versification mapping (Psalms superscriptions, etc.).

## Conventions
- Node IDs are namespaced: `person:adam`, `place:eden`, `nation:canaanites`, `verse:GEN.5.3`
- Hebrew text stored as Unicode, RTL handled in frontend
- Edge types preserve biblical distinctions (father_of vs mother_of vs wife_of vs concubine_of)
- Verse edges encode exegetical distinctions: `mentions` vs `spoken_by` vs `addressed_to` vs `set_in` vs `quotes` vs `alludes_to` vs `parallel_to`
- Scripture refs use format: `{"book": "GEN", "chapter": 5, "verse": 3}`
- Book codes are SBL-standard uppercase 3-letter (GEN, EXO, PSA, 1SA, NAM, …). OSIS codes (Gen, Exod, Ps, 1Sam, Nah) are mapped to Lamp codes on ingest via `lamp.models.book_codes`.
- Hebrew text is preserved in three separable layers: consonantal (pre-Masoretic), pointed (niqqud), cantillated (full Masoretic with te'amim). Total-accuracy directive — Ketiv/Qere, parashah markers, and reversed nun (nun hafukha) are all preserved as distinct features.
- Chronology uses Anno Mundi (AM) year system where calculable
- Translations live in a separate store from canonical verse nodes by design (enforces exegesis/eisegesis separation at the storage layer)

## Current State
- Version: 0.1.0
- Phase 0 complete: project scaffold, both servers operational
- Phase 1A complete: data models, GraphStore, seed data (111 persons, 18 nations, 148 edges), 13 integrity tests passing
- Phase 1B complete: all genealogy API endpoints, 14 API tests passing (27 total)
- Phase 1C complete: full frontend — genealogy tree, person detail, search, line filters
- Phase 1D complete: URL routing (react-router-dom), error states (inline retry + error boundary), final verification
- Phase 2A complete: chronology timeline — SVG lifespan bars, shared AppLayout with Tree/Timeline nav, /chronology API endpoint
- Phase 2B complete: places & geography — 18 places, 34 place links, /places and /place/{id} endpoints, PlacesPage with filters, places in PersonDetailPanel
- Phase 2C-1 Step 1 complete: locked verse-graph schema (`backend/docs/verse_graph_schema.md`) — verses as first-class nodes, three-layer Hebrew text, per-word morphology, 8 verse-edge types, translations stored separately from canonical verse nodes
- Phase 2C-1 Step 2 complete: full Hebrew OT ingest from OSHB. 23,213 verse nodes (matches WLC reference exactly), 305,516 words with lemma/Strong's/morphology, 1,277 ketiv/qere variants, 3,130 parashah markers, 9 reversed-nun verses, 3,120 Masoretic notes preserved. Zero parse warnings. VerseStore (SQLite WAL) + GraphStore coordination. 65 tests passing.
- Phase 2C-1 Step 3 complete: entity→verse link seeding. 358 `MENTIONS` edges created from the 188 curated scripture_refs on 146 entities (110 persons, 18 nations, 18 places). Verse-side traversal works (e.g. `GEN.5.3` → Adam + Seth); entity-side traversal works (e.g. `person:noah` → 7 verses). Script is idempotent — re-run overwrites existing edges.
- Phase 2C-5 complete: KJV 1769 NT translation layer. 7,957 KJV verses attached via the `translations` table (structurally separate from canonical verse nodes — enforces exegesis-over-eisegesis discipline). 32 new verse slots created for KJV verses absent from SBLGNT (pericope adulterae, Matt 17:21/18:11/23:14, and similar textual-critical omissions) — these have empty Greek text with explanatory note, ready for Byzantine/TR ingest later. VersePage surfaces translations in a reference panel beneath the original. 98 tests passing.
- Phase 2C-4 complete: book/chapter navigation — /read route with book list grouped by canon, chapter picker, verse list. /books and /book/{code}/chapter/{n} API endpoints. 95 tests passing.
- Phase 2C-3 complete: verse-detail API (/verse/{id}) + VersePage with three-layer Hebrew / two-layer Greek, layer toggles, per-word morphology, mentioned entities. PersonDetailPanel links to verse pages via materialized MENTIONS edges.
- Phase 2C-2 complete: Greek NT ingest via MorphGNT / SBLGNT. Schema addendum added `text_plain` + `text_accented` Greek layers alongside the Hebrew trio, plus language-agnostic `text_canonical` convenience field (= cantillated for Hebrew, accented for Greek). 7,927 NT verse nodes across all 27 books (legitimately fewer than KJV/TR's 7,957 — SBLGNT omits ~30 Byzantine-only verses per modern critical-text decisions). 137,554 words with part-of-speech + parsing-code morphology (G-prefixed codes like `GV-3AAI-S--`). SBLGNT variant markers (`⸀ ⸂ ⸃` etc.) preserved verbatim in verse text. Zero parse warnings. 83 tests passing.
- Graph: **31,287 nodes** (111 persons, 18 nations, 18 places, 23,213 Hebrew verses, 7,927 Greek verses), **540 edges** (182 entity-entity + 358 verse→entity MENTIONS). Verse-to-verse edges (QUOTES, PARALLEL_TO, ALLUDES_TO) infrastructure ready; no instances seeded yet.
- Next: Phase 2C-3 (TBD). Most likely: (a) NT entity seed + link-seeding (add NT persons/places to graph and create MENTIONS edges), (b) verse-detail API + frontend view, or (c) NT↔OT `QUOTES` edge seeding (e.g. Matt 1:23 → Isa 7:14).
