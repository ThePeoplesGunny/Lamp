# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Testing & linting
- Backend tests: `cd backend && pytest` (107 passing as of v0.2.0). Tests live in `backend/tests/`; pytest config in `backend/pyproject.toml`.
- Single backend test: `cd backend && pytest tests/test_api.py::test_name` or by keyword `pytest -k verse_store`.
- Frontend lint: `cd frontend && npm run lint` (ESLint 9 flat config).
- Frontend build: `cd frontend && npm run build` currently **fails** on pre-existing `GenealogyTree.tsx` TS errors (lines 97-98). Use `cd frontend && npx vite build` to bypass `tsc -b` until those types are fixed (see "Known gaps").
- No Python lint/format tool is configured — match existing style.

## External data sources
- **OSHB (Open Scriptures Hebrew Bible)** — `github.com/openscriptures/morphhb`. Provides Westminster Leningrad Codex in OSIS XML with per-word lemma, Strong's, and morphology. Text is public domain; lemma/morph data is CC-BY-4.0 (must credit OSHB). Clone into `backend/data/external/morphhb/`. Exact commit captured in each verse's `source` field for provenance.
- **MorphGNT / SBLGNT** — `github.com/morphgnt/sblgnt`. SBL Greek New Testament with per-word parsing and lemmatization. **License structure differs from OSHB:** the SBLGNT text itself is governed by the [SBLGNT EULA](http://sblgnt.com/license/) (permits non-commercial academic/personal/research use with attribution — *not* CC-BY); the morphological parsing and lemmatization is CC-BY-**SA** 3.0 (Share-Alike). Implication: if Lamp is ever publicly released, the SA clause forces a CC-BY-SA-3.0-compatible license for derivatives using the MorphGNT data. Clone into `backend/data/external/morphgnt/`. Exact commit captured per verse.
- **KJV 1769** — downloaded from `scrollmapper/bible_databases` (formats/json/KJV.json). Public domain — King James Version 1769 Oxford edition. Used as the primary translation-history reference layer. Stored in the `translations` table keyed by (`KJV-1769`, verse_id). NT fully ingested (Phase 2C-5). OT ingested via versification map in `backend/data/seed/versification_kjv_to_heb.json` (Phase 2C-6) — handles Psalms superscription offsets, Joel & Malachi chapter renumbers. Six books deferred (NUM, 1SA, 1KI, 1CH, NEH, ISA) and 66 chapter-boundary verses in other books remain unmapped pending authoritative per-verse versification tables.

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

**Version:** 0.2.0

**Graph:** 31,172 verse nodes (23,213 Hebrew + 7,927 Greek + 32 KJV-only slots) + 210 entities (151 persons, 18 nations, 41 places). 1,382 edges (182 entity-entity + 1,084 verse→entity MENTIONS + 116 NT→OT QUOTES).

**Corpus:**
- Hebrew OT (OSHB/WLC): 23,213 verses, 305,516 words with lemma + Strong's + morphology + ketiv/qere + parashah + reversed-nun
- Greek NT (MorphGNT/SBLGNT): 7,927 verses, 137,554 words with lemma + POS + parsing codes
- KJV 1769 translations: 25,482 verses attached (7,957 NT + 17,525 OT mapped via Hebrew↔English versification table)

**Tests:** 107 passing.

### Phases complete (chronological)
- **Phase 0** — scaffold, both servers operational
- **Phase 1A** — data models, GraphStore, OT seed data, integrity tests
- **Phase 1B** — genealogy API endpoints, API tests
- **Phase 1C** — frontend genealogy tree, person detail, search, line filters
- **Phase 1D** — URL routing, error states, verification
- **Phase 2A** — chronology timeline (SVG lifespan bars, /chronology API)
- **Phase 2B** — places & geography (18 places, 34 place links, PlacesPage)
- **Phase 2C-1** — verse-graph schema lock + Hebrew OT ingest + entity↔verse MENTIONS seeding
- **Phase 2C-2** — Greek NT ingest via MorphGNT/SBLGNT (2-layer text, G-prefixed morph codes, variant markers preserved)
- **Phase 2C-3** — verse detail API + VersePage with layer toggles + per-word morphology + mention traversal; PersonDetailPanel links to verses
- **Phase 2C-4** — book/chapter navigation (/read route with canon-grouped book list, chapter picker, verse list)
- **Phase 2C-5** — KJV 1769 NT translation layer + Translations panel on VersePage (32 KJV-only slots for SBLGNT-absent verses including pericope adulterae)
- **Phase 2D-1** — lemma / Strong's concordance search (/lexeme route, clickable WordCards, canonical sort order)
- **Phase 2C-6** — KJV 1769 OT translation layer with Hebrew↔English versification mapping (Psalms offsets, Joel & Malachi chapter renumbers)
- **Phase 2D-2** — NT entity seed (40 persons + 23 places) via `persons_nt.json` / `places_nt.json`; `name_greek` + `name_greek_transliterated` added to Person/Place/Nation; 726 new verse→entity MENTIONS edges across 18 NT books
- **Phase 2D-3** — NT→OT QUOTES edges. 116 curated citations across 13 NT books → 16 OT books (Psalms 36, Isaiah 21, Deuteronomy 12 most-cited). Seed file `nt_ot_quotes.json` + idempotent `seed_nt_ot_quotes.py` (clears pre-existing QUOTES before reseed). Edge `notes` field captures LXX-vs-MT deltas, typological readings, attribution puzzles (Matt 27:9 → Zech 11:12 attributed to Jeremiah; Heb 10:5 → Psa 40:7 where LXX σῶμα differs from MT 'ears opened'). Psalms refs use Hebrew versification (superscription = v. 1 shifts 13 of 16 cited psalms +1 vs English)
- **Phase 2D-4** — cross-canon UI surfacing. Backend: `GraphStore.get_cites()` + `get_cited_by()`, `/verse/{id}` response gains `cites[]` + `cited_by[]` (each with reference, canon, edge notes); `name_greek` + `name_greek_transliterated` propagated through person/place/search/mentions API responses. Frontend: `QuotesSection` on VersePage (two-column Cites | Cited by with inline exegetical notes, clickable cross-ref navigation); `GreekText` LTR component used in VersePage mentions, PersonDetailPanel, PlaceCard, SearchBar. `GenealogyTree`/`PersonNode` unchanged — tree is OT-only (NT persons have no parentage edges)

### Known gaps / deferred work
- **KJV OT — 6 books not ingested** (NUM, 1SA, 1KI, 1CH, NEH, ISA): 5,554 verses. Require authoritative per-verse versification table (CrossWire av11n or USFM). Documented in `backend/data/seed/versification_kjv_to_heb.json`.
- **KJV OT — 66 chapter-boundary verses unmapped** across otherwise-aligned books (Gen 31/32, Exo 7/8, Lev 5/6, Dan 3-6, etc.). Same root cause, same follow-up fix.
- **NT entity coverage is first-pass only** — 40 persons, 23 places with anchor refs (not exhaustive linkage). Jerusalem not yet seeded (cross-canon place — belongs in `places.json`; deferred). No biographical cross-relationships (e.g., Peter brother_of Andrew); no Herodian dynasty edges; no NT nations (Romans, Greeks).
- **NT↔OT QUOTES — curated seed only** — 116 high-confidence edges; comprehensive coverage (every NT quotation per STEPBible / UBS5) would require ~350+ edges. Also: no `ALLUDES_TO` / `PARALLEL_TO` edges seeded yet (Synoptic parallels, Kings↔Chronicles, Psalm parallels).
- **KJV OT regenerates on graph rebuild** — `seed_graph.py` wipes the verse SQLite cascade (FK ON DELETE CASCADE from verses→translations), so translation reseed is required after any entity-seed change. Should add a doc note or a safer graph-only rebuild path.
- **Browser-visual QA still pending** — Phase 2D-4's `QuotesSection` and Greek-name rendering pass typecheck + API probes but haven't been eyeballed in a browser. Good first things to open: `/verse/MAT.1.23` (virgin birth cite), `/verse/PSA.110.1` (3 NT citers), `/verse/HEB.10.5` (LXX σῶμα note), `/person/paul` (Greek Παῦλος), search header for "Peter".
- **Pre-existing GenealogyTree.tsx TS errors** (lines 97-98) untouched across all Phase 2C/2D work — unrelated to the verse substrate, `vite build` tolerates them, `tsc -b` flags. `npm run build` therefore fails; use `npx vite build` until the types are fixed.

### Next candidates (pick direction next session)
- **(a) Expand NT entity linkage** — deepen the 40 NT persons (more scripture_refs, biographical edges) or add NT nations + Jerusalem + remaining figures.
- **(b) Expand QUOTES coverage** — swap the curated ~116 seed for STEPBible TAGNT (CC-BY) or equivalent to reach ~350+ edges. Then add `ALLUDES_TO` + `PARALLEL_TO` (Synoptic parallels, Kings↔Chronicles, Psalm parallels).
- **(c) Finish KJV OT** — add the 6 deferred books + 66 gap verses via CrossWire av11n mapping.
- **(d) Second translation** (e.g. ASV 1901, PD) for translation-drift side-by-side.
- **(e) Fix pre-existing GenealogyTree TS errors** — unblocks `npm run build`; small cleanup.
- **(f) Browser-visual QA pass** of Phase 2D-4 + everything built so far (see "Known gaps" for specific URLs).
- **(g) Safer graph-rebuild path** — `seed_graph.py` currently wipes verse SQLite via FK cascade. Could either make it additive (`.load()` + entity-only replace) or add a `reseed_all.sh` that runs the full 6-script chain.
