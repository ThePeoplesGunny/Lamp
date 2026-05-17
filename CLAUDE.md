# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Lamp — Project Instructions

## Project Intent & Boundaries

**IS:** Investigation platform for original Hebrew/Greek biblical texts — surfaces patterns, connections, and structures not visible through translation. For one user (the developer).

**IS NOT:** A Bible app. A devotional tool. A commentary system. A translation engine. A concordance replacement (though it contains concordance data). Not multi-user. Not deployed publicly (license constraints from MorphGNT/SBLGNT preclude commercial use).

## Locked Decisions

Decisions made with deliberate analysis. Do not relitigate without new evidence (per global P6).

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | Verse nodes are first-class (Phase 2C-1) | Verses are the atomic unit of biblical text. Everything connects through them. | 2026-04 |
| 2 | Exegetical/eisegetical boundary enforced at storage layer | Interpretive claims cannot masquerade as textual facts. Edge types declare their category. | 2026-04 |
| 3 | Hebrew text three-layer storage (consonantal/pointed/cantillated) | Separable layers preserve pre-Masoretic, voweled, and full-accent forms independently. | 2026-04 |
| 4 | Translations stored separately from canonical verse nodes | Enforces exegesis/eisegesis separation. Translation is interpretation, not source. | 2026-04 |
| 5 | KJV-to-Hebrew versification uses generalized book_overrides schema | Handles all 39 OT books including structural chapter splits, Psalms offsets, merge cases. | 2026-05 |
| 6 | STEPBible TAGNT rejected as citation source | TAGNT tags morphology + TIPNR proper-noun origins, NOT OT citation references. Curated path retained. | 2026-05 |
| 7 | SBL-standard 3-letter book codes (mapped from OSIS on ingest) | Consistent cross-source addressing. | 2026-04 |

## Source Provenance Tiers

| Tier | Authority | Examples |
|------|-----------|----------|
| 0 | User attestation | Direct statements about project intent, interpretation choices |
| 1 | Primary text sources (canonical) | OSHB/WLC (Hebrew OT), MorphGNT/SBLGNT (Greek NT) |
| 2 | Historic translations (public domain) | KJV 1769 Oxford edition |
| 3 | Secondary scholarly sources | Published quotation indices, commentaries, STEPBible datasets |
| 4 | Speculative inference | Interpretive connections not grounded in tier 1-3 |

Claims from tier 3+ must be explicitly noted. Tier 4 cannot be presented as fact.

## Context-Dangerous Zones

- **`backend/data/external/morphhb/`** — full OSHB clone (~50MB). Never bulk-load. Use ingest scripts or grep for specific books.
- **`backend/data/external/morphgnt/`** — full MorphGNT clone. Same rule.
- **`backend/data/graphs/lamp.json`** — serialized graph (grows with seeding). Read via GraphStore API, not raw.
- **`backend/data/verses/verses.db`** — SQLite verse store (31K+ rows). Query via verse_store.py, not raw SQL dumps.

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
- **KJV 1769** — downloaded from `scrollmapper/bible_databases` (formats/json/KJV.json). Public domain — King James Version 1769 Oxford edition. Used as the primary translation-history reference layer. Stored in the `translations` table keyed by (`KJV-1769`, verse_id). NT fully ingested (Phase 2C-5). OT fully ingested (Phase 2C-7) via `backend/data/seed/versification_kjv_to_heb.json` — generalized `book_overrides` schema covers all 39 OT books; Psalms offsets handle superscriptions (incl. 2-line in 51/52/54/60); structural chapter splits (Num 16/17, 1Kgs 4/5, 1Chr 5/6, Neh 3/4) and ±1 trailing/leading shifts handled per-book; 5 merge cases use `extra_targets` for one-KJV-verse-to-many-Heb-verses, and 3 reverse merges (KJV-many-to-Heb-one) concatenate at ingest time. 23,145 KJV OT verses attached, 0 unmapped.

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

**Graph:** 31,172 verse nodes (23,213 Hebrew + 7,927 Greek + 32 KJV-only slots) + 429 entities (293 persons, 25 nations, 111 places). 2,763 edges (249 entity-entity + 2,370 verse→entity MENTIONS + 144 NT→OT QUOTES).

**Corpus:**
- Hebrew OT (OSHB/WLC): 23,213 verses, 305,516 words with lemma + Strong's + morphology + ketiv/qere + parashah + reversed-nun
- Greek NT (MorphGNT/SBLGNT): 7,927 verses, 137,554 words with lemma + POS + parsing codes
- KJV 1769 translations: 31,102 verses attached (7,957 NT + 23,145 OT — full KJV OT, all 39 books)

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
- **Phase 2C-7** — full KJV OT versification. `versification_kjv_to_heb.json` rewritten to a generalized `book_overrides` schema (per-book chapter-range overrides + optional `extra_targets` for merge cases). Closes both prior gaps: the 6 deferred books (NUM, 1SA, 1KI, 1CH, NEH, ISA — 5,554 verses) and the 66 chapter-boundary unmapped verses in aligned books. Also fixes a Phase 2C-6 bug — the Psalms offset table had +1 entries for 15 chapters where OSHB does NOT number the superscription separately (Pss 11, 13, 14, 15, 16, 17, 23, 24, 25, 26, 27, 28, 29, 32, 50); the new table is recomputed mechanically from OSHB↔KJV chapter-size deltas. All boundary verses verified by reading OSHB Hebrew content against expected KJV English at every divergent chapter pair (Num 16/17, 1Kgs 4/5, 1Chr 5/6 = the big structural splits; Gen 31/32, Lev 5/6, Exo 7/8, Deu 12/13, etc. = 51 ±1 trailing/leading shifts). Three Heb verses receive multi-KJV merges (`NEH 7:67`, `ISA 63:19`, `ISA 64:1`) where one KJV verse covers two Heb verses or vice versa — texts concatenated with " | ". Final: 23,145 KJV OT verses attached, 0 unmapped.
- **Phase 2D-5** — comprehensive NT entity coverage. Persons: 40 → 182 (added 142 named NT figures). Places: 41 → 111 (added Jerusalem + 8 cross-canon places to `places.json`; added 47 NT-only places to `places_nt.json` covering Galilean towns, Pauline travel route, Revelation churches, Asia Minor regions, Mediterranean stops). Nations: 18 → 25 (added Romans, Samaritans, Parthians, Cretans, Idumeans, Galatians, Phoenicians). 61 NT biographical relationships seeded — Holy Family, John the Baptist's family, the Twelve as `disciple_of` Jesus, Bethany siblings, Caiaphas/Annas, Herodian dynasty (Herod the Great → Antipas/Archelaus/Philip Tetrarch + Antipas-Herodias-Salome), Agrippa I → Agrippa II/Bernice/Drusilla, Felix-Drusilla, Aquila-Priscilla, Onesimus-Philemon. New `EdgeType` values added: `husband_of`, `brother_of`, `sister_of`, `cousin_of`, `relative_of`, `son_in_law_of`, `daughter_in_law_of`, `disciple_of`, `slave_of`. MENTIONS edges grew 1,084 → 2,370 from the new anchor refs. 107 tests still pass.
- **Phase 2D-6 batch 1** — QUOTES expansion, Hebrews. +28 NT→OT edges (Hebrews 16 → 44; overall 116 → 144). STEPBible TAGNT was investigated first as a bulk source per the speculative Next-candidate plan — confirmed it tags morphology + TIPNR proper-noun *origin* anchors (e.g. `Immanuel@Isa.7.14` is where the name was first introduced, NOT a citation marker) but does NOT carry inline OT-citation references; no quotation index exists elsewhere in STEPBible-Data. Fell back to curated expansion using a published quotation index as a factual checklist (a list of references is uncopyrightable). New Hebrews edges preserve LXX/MT deltas (Psa 40:7 σῶμα for MT 'ears opened'; Pro 3:12 LXX 'scourges' vs MT 'as a father delights'; Deu 32:43 4QDeutq agrees with LXX), re-quote relationships (Psa 95:7+11 trio at Heb 3:7,11,15 / 4:3,5,7; Psa 110:4 triple at Heb 5:6 / 7:17 / 7:21; Psa 40:7-8 split at Heb 10:5 / 10:7; Jer 31:31-34 anchor at Heb 8:8 + condensed re-quote at 10:16-17), and hermeneutical moves (Psa 2:7 dual application — enthronement at Heb 1:5, priestly calling at 5:5; Deu 32:35 redirected from Rom 12:19 'don't take vengeance' to Heb 10:30 'God will'; Moses' Deu 9:19 golden-calf trembling relocated to Sinai at Heb 12:21). All 107 tests still pass.

### Known gaps / deferred work
- **NT↔OT QUOTES — curated expansion in progress** — 144 high-confidence edges. Hebrews batch 1 done (44 edges); planned remaining batches: Romans (~25), Synoptics fill-in (~30), Pauline epistles fill-in (~30), Catholic epistles + Revelation (~25). Target ~250+. Also: no `ALLUDES_TO` / `PARALLEL_TO` edges seeded yet (Synoptic parallels, Kings↔Chronicles, Psalm parallels).
- **KJV OT regenerates on graph rebuild** — `seed_graph.py` wipes the verse SQLite cascade (FK ON DELETE CASCADE from verses→translations), so translation reseed is required after any entity-seed change. Should add a doc note or a safer graph-only rebuild path.
- **Browser-visual QA still pending** — Phase 2D-4's `QuotesSection` and Greek-name rendering pass typecheck + API probes but haven't been eyeballed in a browser. Good first things to open: `/verse/MAT.1.23` (virgin birth cite), `/verse/PSA.110.1` (3 NT citers), `/verse/HEB.10.5` (LXX σῶμα note), `/person/paul` (Greek Παῦλος), search header for "Peter".
- **Pre-existing GenealogyTree.tsx TS errors** (lines 97-98) untouched across all Phase 2C/2D work — unrelated to the verse substrate, `vite build` tolerates them, `tsc -b` flags. `npm run build` therefore fails; use `npx vite build` until the types are fixed.

### Next candidates (pick direction next session)
- **(a) Continue QUOTES expansion** — Hebrews batch 1 complete (+28 edges, 144 total). Remaining curated batches: Romans (~25), Synoptics fill-in (~30), Pauline epistles fill-in (~30), Catholic epistles + Revelation (~25). Note: STEPBible TAGNT was investigated as a bulk source but does NOT tag OT citations inline (only morphology + TIPNR proper-noun *origin* anchors), so curated path was retained. After QUOTES reach ~250+, add `ALLUDES_TO` + `PARALLEL_TO` edge types (Synoptic parallels, Kings↔Chronicles, Psalm parallels).
- **(b) Second translation** (e.g. ASV 1901, PD) for translation-drift side-by-side. Now that the KJV↔Heb versification map is solid, a second English translation can reuse the same `versification_kjv_to_heb.json` if it follows KJV numbering.
- **(c) Fix pre-existing GenealogyTree TS errors** — unblocks `npm run build`; small cleanup.
- **(d) Browser-visual QA pass** of Phase 2D-4/2D-5 + everything built so far. Good URLs to spot-check: `/person/peter` (now has brother_of Andrew, disciple_of Jesus), `/person/herod_antipas` (now has father, brother, wife edges), `/place/jerusalem` (cross-canon — should show OT + NT mentions).
- **(e) Safer graph-rebuild path** — `seed_graph.py` currently wipes verse SQLite via FK cascade. Could either make it additive (`.load()` + entity-only replace) or add a `reseed_all.sh` that runs the full 6-script chain.
- **(f) Frontend rendering for new edge types** — `husband_of`, `brother_of`, `disciple_of` etc. are now in the data; `GenealogyTree` (OT-focused) doesn't traverse them. A fresh `RelationshipsPanel` or extended `PersonDetailPanel` could surface them.

## Agents & Skills

Three agents in `.claude/agents/` evaluate data integrity from specialized perspectives:
- **text-integrity** — Hebrew three-layer fidelity, Greek morphology consistency, encoding correctness
- **graph-analyst** — Relationship correctness, edge type validity, structural integrity, path analysis
- **source-validator** — OSHB/MorphGNT consistency, license compliance, data freshness, provenance chain

Three skills in `.claude/commands/`:
- **/session-start** — state verification (tests, graph stats, verse counts, alignment)
- **/session-close** — session close (state update, verification, commit)
- **/verify** — change-type verification matrix (backend, frontend, schema, ingest, text, versification, edge)

## Cross-Project Connections

- **No direct dependencies.** Lamp is self-contained.
- **Methodological inheritance:** Source provenance tiers and three-layer text fidelity model may inform other projects with structured data requirements.
