# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Lamp — Project Instructions

## Project Intent & Boundaries

**IS:** Investigation platform built on the **KJV 1769 as the base text**. The KJV is the heart of this project; the original-language witnesses (OSHB/WLC Hebrew, MorphGNT/SBLGNT Greek) and everything else in the repo exist to support and illuminate it. Surfaces patterns, connections, and structures in the text. For one user (the developer).

**Base-text decision (2026-09-07, operator-stated):** "the heart of this project is the KJV.. everything else supports." This governs the provenance tiers and Locked Decisions 2, 4 and 8 below. It is a tier-0 attestation — the operator's statement about his own project — and is not to be relitigated against the earlier original-languages-are-canonical framing, which it replaces.

**IS NOT:** A Bible app. A devotional tool. A commentary system. A translation engine. A concordance replacement (though it contains concordance data). Not multi-user. Not deployed publicly (license constraints from MorphGNT/SBLGNT preclude commercial use).

## Locked Decisions

Decisions made with deliberate analysis. Do not relitigate without new evidence.

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | Verse nodes are first-class (Phase 2C-1) | Verses are the atomic unit of biblical text. Everything connects through them. | 2026-04 |
| 2 | Exegetical/eisegetical boundary enforced at storage layer | Interpretive claims cannot masquerade as textual facts. Edge types declare their category. **Amended 2026-09-07:** the boundary still holds and the edge-type machinery is unchanged; what moved is the base it is drawn against. "Textual fact" now means what the KJV 1769 says. Original-language readings are supporting evidence about that text, not the text itself. | 2026-04, amended 2026-09 |
| 3 | Hebrew text three-layer storage (consonantal/pointed/cantillated) | Separable layers preserve pre-Masoretic, voweled, and full-accent forms independently. | 2026-04 |
| 4 | KJV text stored in its own table, separate from the original-language verse rows | **Rewritten 2026-09-07.** The separation stands, but its meaning is inverted. It was "translation is interpretation, not source". It now reads: the KJV is the source, and the separate table keeps it from being confused with the original-language witnesses that support it. The storage layout has not changed yet — see the two open items under "Known gaps" — so the KJV is still an FK-dependent child of a verse row, which contradicts this decision and is scheduled to be fixed. | 2026-04, rewritten 2026-09 |
| 5 | KJV-to-Hebrew versification uses generalized book_overrides schema | Handles all 39 OT books including structural chapter splits, Psalms offsets, merge cases. | 2026-05 |
| 6 | STEPBible TAGNT rejected as citation source | TAGNT tags morphology + TIPNR proper-noun origins, NOT OT citation references. Curated path retained. | 2026-05 |
| 7 | SBL-standard 3-letter book codes (mapped from OSIS on ingest) | Consistent cross-source addressing. | 2026-04 |
| 8 | **KJV 1769 is the base text; original languages are supporting witnesses** | Operator attestation, 2026-09-07: "the heart of this project is the KJV.. everything else supports." Sets the provenance tiers below (KJV tier 1, OSHB/MorphGNT tier 2) and governs decisions 2 and 4. | 2026-09 |

## Source Provenance Tiers

| Tier | Authority | Examples |
|------|-----------|----------|
| 0 | User attestation | Direct statements about project intent, interpretation choices |
| 1 | **The base text (canonical)** | **KJV 1769 Oxford edition** |
| 2 | Original-language witnesses (supporting) | OSHB/WLC (Hebrew), MorphGNT/SBLGNT (Greek) |
| 3 | Secondary scholarly sources | Published quotation indices, commentaries, STEPBible datasets |
| 4 | Speculative inference | Interpretive connections not grounded in tier 1-3 |

Claims from tier 3+ must be explicitly noted. Tier 4 cannot be presented as fact.

**Inverted 2026-09-07** per Locked Decision 8. Tiers 1 and 2 previously held the
original languages and the KJV respectively. The tier values in the database were
migrated by re-running the ingest scripts, not by hand-patching rows: KJV
translations and the 32 KJV-sourced slot verses are `source_tier = 1`; the 23,213
OSHB and 7,927 MorphGNT verses are `source_tier = 2`. The tier is set in exactly
four places — `TRANSLATION_TIER` in `seed_translations_kjv_nt.py` and
`seed_translations_kjv_ot.py`, and `source_tier=` in `lamp/ingest/oshb.py` and
`lamp/ingest/morphgnt.py`.

## Context-Dangerous Zones

- **`backend/data/external/morphhb/`** — full OSHB clone (~50MB). Never bulk-load. Use ingest scripts or grep for specific books.
- **`backend/data/external/morphgnt/`** — full MorphGNT clone. Same rule.
- **`backend/data/graphs/lamp.json`** — serialized graph (grows with seeding). Read via GraphStore API, not raw.
- **`backend/data/verses/verses.db`** — SQLite verse store (31K+ rows). Query via verse_store.py, not raw SQL dumps.

## Overview
Biblical analytical tool — investigation platform built on the KJV 1769 as the base text, with the original-language witnesses (OSHB/WLC Hebrew, MorphGNT/SBLGNT Greek) supporting it. Strips noise, surfaces patterns, connections, and structures in the text.

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
- Backend tests: `cd backend && pytest` (121 passing as of v0.2.0). Tests live in `backend/tests/`; pytest config in `backend/pyproject.toml`.
- Single backend test: `cd backend && pytest tests/test_api.py::test_name` or by keyword `pytest -k verse_store`.
- Frontend lint: `cd frontend && npm run lint` (ESLint 9 flat config).
- Frontend build: `cd frontend && npm run build` (runs `tsc -b && vite build`). Passes.
- No Python lint/format tool is configured — match existing style.

## External data sources
- **OSHB (Open Scriptures Hebrew Bible)** — `github.com/openscriptures/morphhb`. Provides Westminster Leningrad Codex in OSIS XML with per-word lemma, Strong's, and morphology. Text is public domain; lemma/morph data is CC-BY-4.0 (must credit OSHB). Clone into `backend/data/external/morphhb/`. Exact commit captured in each verse's `source` field for provenance.
- **MorphGNT / SBLGNT** — `github.com/morphgnt/sblgnt`. SBL Greek New Testament with per-word parsing and lemmatization. **License structure differs from OSHB:** the SBLGNT text itself is governed by the [SBLGNT EULA](http://sblgnt.com/license/) (permits non-commercial academic/personal/research use with attribution — *not* CC-BY); the morphological parsing and lemmatization is CC-BY-**SA** 3.0 (Share-Alike). Implication: if Lamp is ever publicly released, the SA clause forces a CC-BY-SA-3.0-compatible license for derivatives using the MorphGNT data. Clone into `backend/data/external/morphgnt/`. Exact commit captured per verse.
- **KJV 1769** — downloaded from `scrollmapper/bible_databases` (formats/json/KJV.json). Public domain — King James Version 1769 Oxford edition. **This is the project's base text** (Locked Decision 8), stored at `source_tier = 1`. Stored in the `translations` table keyed by (`KJV-1769`, verse_id). NT fully ingested (Phase 2C-5). OT fully ingested (Phase 2C-7) via `backend/data/seed/versification_kjv_to_heb.json` — generalized `book_overrides` schema covers all 39 OT books; Psalms offsets handle superscriptions (incl. 2-line in 51/52/54/60); structural chapter splits (Num 16/17, 1Kgs 4/5, 1Chr 5/6, Neh 3/4) and ±1 trailing/leading shifts handled per-book; 5 merge cases use `extra_targets` for one-KJV-verse-to-many-Heb-verses, and 3 reverse merges (KJV-many-to-Heb-one) concatenate at ingest time. 23,145 KJV OT verses attached, 0 unmapped.

## Conventions
- Node IDs are namespaced: `person:adam`, `place:eden`, `nation:canaanites`, `verse:GEN.5.3`
- Hebrew text stored as Unicode, RTL handled in frontend
- Edge types preserve biblical distinctions (father_of vs mother_of vs wife_of vs concubine_of)
- Verse edges encode exegetical distinctions: `mentions` vs `spoken_by` vs `addressed_to` vs `set_in` vs `quotes` vs `alludes_to` vs `parallel_to`
- Scripture refs use format: `{"book": "GEN", "chapter": 5, "verse": 3}`
- Book codes are SBL-standard uppercase 3-letter (GEN, EXO, PSA, 1SA, NAM, …). OSIS codes (Gen, Exod, Ps, 1Sam, Nah) are mapped to Lamp codes on ingest via `lamp.models.book_codes`.
- Hebrew text is preserved in three separable layers: consonantal (pre-Masoretic), pointed (niqqud), cantillated (full Masoretic with te'amim). Total-accuracy directive — Ketiv/Qere, parashah markers, and reversed nun (nun hafukha) are all preserved as distinct features.
- Chronology uses Anno Mundi (AM) year system where calculable
- The KJV base text lives in the `translations` table, separate from the original-language verse rows. The separation is deliberate, but note its meaning inverted on 2026-09-07: it now keeps the base text distinct from the supporting witnesses, rather than keeping an interpretation out of the source. The storage layout has NOT caught up — the KJV is still an FK-dependent child of a verse row, which is listed under Known gaps.

## Current State

**Version:** 0.2.0

**Graph:** 31,172 verse nodes (23,213 Hebrew + 7,927 Greek + 32 KJV-only slots) + 429 entities (293 persons, 25 nations, 111 places). 2,770 edges (249 entity-entity + 2,377 verse→entity MENTIONS + 144 NT→OT QUOTES).

**Corpus:**
- Hebrew OT (OSHB/WLC): 23,213 verses, 305,516 words with lemma + Strong's + morphology + ketiv/qere + parashah + reversed-nun
- Greek NT (MorphGNT/SBLGNT): 7,927 verses, 137,554 words with lemma + POS + parsing codes
- KJV 1769 translations: **31,104 rows** in the `translations` table (7,957 NT + 23,147 OT — full KJV OT, all 39 books).
  Two different quantities are in play and both are correct: the OT ingest reports **23,145 KJV source verses attached**,
  while the table holds **23,147 rows**. 5 `extra_targets` entries attach one KJV verse to a second Hebrew verse
  (+5 rows: NUM 25:19, 1SA 21:1, 1KI 22:44, 1CH 12:5, ISA 64:1) and 3 reverse merges concatenate several KJV verses
  into a single row (−3 rows: ISA 63:19, ISA 64:1, NEH 7:67). 23,145 + 5 − 3 = 23,147.

**Tests:** 121 passing.

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
- **Phase 2D-7** — closed two of the three standing gaps and corrected the record on a third.
  **(1) GenealogyTree TS errors fixed.** `useNodesState([])` / `useEdgesState([])` inferred their state type as `never[]`, so `setNodes` and `setEdges` (lines 97-98) rejected real nodes and edges. Typed as `useNodesState<Node>([])` / `useEdgesState<Edge>([])`. `npm run build` now exits 0; `npm run lint` exits 0.
  **(2) Destructive-reseed path closed at the root — and the previously documented mechanism was wrong.** `seed_graph.py` never opened `verses.db` at all; it constructed an empty `GraphStore`, never called `.load()`, and saved over `lamp.json`, erasing all 31,172 verse nodes and 144 verse→verse QUOTES edges. The translation loss happened one step later, during the recovery: `insert_verses` used `INSERT OR REPLACE`, which SQLite performs as DELETE-then-INSERT, firing `ON DELETE CASCADE` on `translations.verse_id`. Both halves fixed. `verse_store.py` now upserts via `INSERT … ON CONFLICT(id) DO UPDATE`, built from a `VERSE_COLUMNS` list so the column list, placeholders and SET clause cannot drift; `seed_graph.py` now loads the existing graph, replaces only person/place/nation nodes, relinks MENTIONS in-process via the new `lamp/ingest/verse_links.py`, and refuses to save if the verse-node count changed. Both old behaviours were replayed against the new tests and confirmed red first: translations 1 → 0 on reseed, verse nodes 3 → 0 and QUOTES 1 → 0 on entity reseed.
  **(3) MENTIONS edges 2,370 → 2,377.** The live additive rerun recovered 7 edges that were never created because `seed_verse_links.py` last ran before Phase 2C-5 added the 32 KJV-only slots, so those refs were silently skipped as missing verse nodes. All 7 point at four SBLGNT-absent verses (`canonical_len=0`, 0 words, KJV source only): ACT 8:37 → Philip the evangelist + the Ethiopian eunuch; ACT 19:41 → Demetrius the silversmith + Ephesus; ACT 24:7 → Claudius Lysias + Felix; JHN 5:4 → the pool of Bethesda. `verses.db` was byte-identical before and after the run (115,998,720 bytes), confirming the graph reseed does not touch SQLite. 9 new tests; 107 → 116 passing.
  **(4) Browser-visual QA pass done, two defects found and fixed.** Pages checked in Chrome at 1440x1000: `/verse/PSA.110.1`, `/verse/MAT.1.23`, `/verse/HEB.10.5`, `/verse/ACT.8.37`, `/verse/GEN.32.1`, `/verse/GEN.1.12`, `/person/paul`, `/person/adam`, and the search header. Rendering that was verified correct: Hebrew RTL with cantillation, Greek LTR with accents, mixed-direction notes (Hebrew עַלְמָה and Greek παρθένος inside English sentences — the Psa 40:7 note's Hebrew was confirmed to be stored in logical order, אָזְנַיִם then כָּרִיתָ, so the browser's bidi rendering is correct), `QuotesSection` two-column layout with inline notes, the full genealogy tree (which is the runtime proof of the `useNodesState<Node>` fix), and the KJV-only slots, which render `WORDS (0)` with an explanatory banner rather than breaking.
  Defect A — **two endpoints silently dropped `name_greek_transliterated`.** Phase 2D-4 claimed it was propagated through person/place/search/mentions; it was not. `search_persons` in `api/genealogy.py` and `_summarize_mention` in `api/verses.py` set `name_greek` but not its transliteration, so search returned `null` for Peter while the data held `Petros`. `name_hebrew_transliterated` was missing from both too. Added to both, with 3 tests that go red without the fix.
  Defect B — **the verse notes heading was wrong for 2,059 of 3,152 notes.** A single heading read "Masoretic notes" over a field carrying three unrelated kinds of record: 2,027 KJV versification mappings (a translation-layer artifact, e.g. `KJV:Gen.31.55` on GEN 32:1), 1,093 genuine Masoretic apparatus entries (844 Ketiv/Qere and accent notes, 249 scribal notes), and 32 SBLGNT-absent/Byzantine notes on **Greek NT** verses, where "Masoretic" cannot apply at all. `VersePage` now splits them: KJV mappings render under "KJV versification", and the rest under "Masoretic notes" for tanakh verses or "Textual notes" otherwise.
  Defect C — **the 32 KJV-only slots rendered a labelled empty box.** `GreekVerseBody` drew the panel and its plain/accented toggle unconditionally, so a verse with no SBLGNT text (Acts 8:37, John 5:4, etc.) showed an empty container and a toggle choosing between two empty strings — it read as a load failure rather than a deliberate textual-critical absence. The panel now says "Greek text — none in SBLGNT", explains the absence in place, and hides the toggle. All 32 such verses are NT; no tanakh verse has empty text.
  Gate coverage added afterwards: `seed_graph.py`'s refuse-to-save check is now tested by forcing a verse-node loss and asserting `main()` returns 1 **and** the file on disk is byte-identical — verified discriminating by disabling the gate and watching the test fail. The fresh-clone path (no existing `lamp.json`, so the relink is skipped) is covered too. `seed_verse_links.py` was executed after its rewrite: exit 0, 2,377 edges, 0 refs skipped, and a second run produces a byte-identical file. `VERSE_COLUMNS` was checked against the real migrated 116MB database, not just a fresh in-memory schema: 17 columns each side, no drift.
- **Phase 2D-8** — KJV provenance tier corrected, 4 → 2. Every one of the 31,104 KJV rows, and the 32 KJV-only slot verse rows, were stamped `source_tier = 4`. Tier 4 in this project's own table means "Speculative inference" and carries the rule "Tier 4 cannot be presented as fact"; tier 2 is defined as "Historic translations (public domain)" and names the KJV 1769 Oxford edition explicitly. Root cause was in `seed_translations_kjv_nt.py`: `TRANSLATION_TIER = 4  # Translation; lower than primary-source tier 1` — the author wanted a value below tier 1 and read the scale as a generic ranking rather than a set of defined categories. Every verse page printed "tier 4" on the KJV panel. Fixed in both ingest scripts and re-run; `test_api.py` had been asserting `source_tier == 4`, so the suite encoded the defect instead of catching it — that assertion now asserts 2.
  A second defect surfaced while fixing it: the NT script's slot guard read `if verse_id not in store.G`, so it only ever *created* KJV-only slots and never refreshed them. The tier correction therefore did not reach the 32 rows already on disk. The guard now also refreshes slots matching `TRANSLATION_SOURCE`, added via `VerseStore.verse_ids_by_source()`; matching on the source string is what keeps it safe, since a slot carries the KJV file as its source while real verses carry OSHB-WLC or MorphGNT-SBLGNT, so it can never rewrite a verse holding actual Hebrew or Greek text.
  That re-run is also the first live proof of the Phase 2D-7 upsert on the real 116MB database: the 32 slot verses were genuinely rewritten (tier 4 → 2 shows the write happened) while the 32 translations attached to them survived. Under the old `INSERT OR REPLACE` that identical write would have cascade-deleted all 32. Totals unchanged: 31,172 verses, 443,070 words, 31,104 translations, 7,927 SBLGNT verses with text intact.
- **Phase 2D-9** — **base-text inversion.** Operator statement 2026-09-07: "the heart of this project is the KJV.. everything else supports." The KJV 1769 is now the base text (tier 1) and the original-language witnesses support it (tier 2). What changed, in one pass so no enforcer was left pointing the old way:
  - **Tiers in code** — `TRANSLATION_TIER` 2 → 1 in both KJV ingest scripts; `source_tier` 1 → 2 in `lamp/ingest/oshb.py` and `lamp/ingest/morphgnt.py`. Those four constants are the only places the tier is set.
  - **Tiers in data** — migrated by re-running all four ingest scripts against their sources, not by hand-patching rows. Result: KJV 31,104 translations + 32 slot verses at tier 1; 23,213 OSHB + 7,927 MorphGNT verses at tier 2. Totals unchanged throughout: 31,172 verses, 443,070 words, 31,104 translations.
  - **Governance** — Project Intent rewritten; Locked Decision 2 amended (the exegesis/eisegesis boundary and its edge-type machinery are unchanged, but "textual fact" now means what the KJV says); Locked Decision 4 rewritten; new Locked Decision 8 records the base-text call; tier table inverted; Conventions and the KJV source entry swept.
  - **UI** — the KJV panel now leads the verse page, above the Hebrew/Greek witness. Its heading was "Translations (n) — Reference layer, never replaces the original text"; it now reads "Base text — KJV 1769 — the text this project is about, original-language witnesses below support it".
  - **Memory** — `feedback_exegesis.md` and `project_verse_node_architecture.md` both asserted the originals were canonical; both corrected. `project_context.md` records the operator's words.
  - **Tests** — three assertions encoded the old tiers and failed on the inversion, which is the suite doing its job: `test_api.py` KJV tier → 1, `test_oshb_ingest.py` and `test_morphgnt_ingest.py` → 2.
  - **A broken detector found on the way.** `seed_verses.py` computed `ok = total_warnings == 0 and sqlite_verse_count == total_verses`, comparing the 23,213 Hebrew verses it parsed against a whole-table count of 31,172. From the moment Phase 2C-2 added the Greek NT this could never be true, so every successful run printed "ISSUES DETECTED" and returned exit code 1. `count_verses()` now takes an optional `canon` and the comparison is scoped to the tanakh; the script reports INGEST OK and exits 0. `seed_verses_nt.py` checks warnings only and was never affected.
  - **The upsert proved at full scale.** Re-ingesting all 23,213 Hebrew verses while translations were attached left all 31,104 translations intact. Under the pre-2D-7 `INSERT OR REPLACE` that single run would have destroyed all 23,147 OT translations.

### Known gaps / deferred work
- **The KJV is still stored as a dependent of the thing it now outranks** — `translations` has `FOREIGN KEY (verse_id) REFERENCES verses(id) ON DELETE CASCADE`, so a KJV verse cannot exist without an original-language verse row to hang off. This directly contradicts Locked Decision 8. The visible symptom is the 32 KJV-only slots: verses in the KJV but absent from the SBLGNT (Acts 8:37, John 5:4, and 30 more) required manufacturing empty Greek verse rows — zero text, zero words — purely as hangers. Fix is a schema change giving KJV verses standing of their own.
- **Versification is still Hebrew-primary** — `versification_kjv_to_heb.json` maps KJV numbering *onto* the Hebrew spine, and verse IDs (`verse:GEN.32.1`) follow Hebrew numbering. Under Locked Decision 8 the KJV should be the addressing spine with the Hebrew mapped onto it. This is the largest piece of deferred work: it touches 31,172 node IDs, 2,770 edges, every `scripture_refs` entry in the seed files, and `nt_ot_quotes.json`, which deliberately uses Hebrew Psalms numbering. Not to be attempted without a migration plan and a reversible checkpoint.
- **NT↔OT QUOTES — curated expansion in progress** — 144 high-confidence edges. Hebrews batch 1 done (44 edges); planned remaining batches: Romans (~25), Synoptics fill-in (~30), Pauline epistles fill-in (~30), Catholic epistles + Revelation (~25). Target ~250+. Also: no `ALLUDES_TO` / `PARALLEL_TO` edges seeded yet (Synoptic parallels, Kings↔Chronicles, Psalm parallels).

### Next candidates (pick direction next session)
- **(a) Continue QUOTES expansion** — Hebrews batch 1 complete (+28 edges, 144 total). Remaining curated batches: Romans (~25), Synoptics fill-in (~30), Pauline epistles fill-in (~30), Catholic epistles + Revelation (~25). Note: STEPBible TAGNT was investigated as a bulk source but does NOT tag OT citations inline (only morphology + TIPNR proper-noun *origin* anchors), so curated path was retained. After QUOTES reach ~250+, add `ALLUDES_TO` + `PARALLEL_TO` edge types (Synoptic parallels, Kings↔Chronicles, Psalm parallels).
- **(b) Second translation** (e.g. ASV 1901, PD) for translation-drift side-by-side. Now that the KJV↔Heb versification map is solid, a second English translation can reuse the same `versification_kjv_to_heb.json` if it follows KJV numbering.
- **(f) Frontend rendering for new edge types** — `husband_of`, `brother_of`, `disciple_of` etc. are now in the data; `GenealogyTree` (OT-focused) doesn't traverse them. A fresh `RelationshipsPanel` or extended `PersonDetailPanel` could surface them.

## Agents & Skills

Three agents in `.claude/agents/` evaluate data integrity from specialized perspectives:
- **text-integrity** — Hebrew three-layer fidelity, Greek morphology consistency, encoding correctness
- **graph-analyst** — Relationship correctness, edge type validity, structural integrity, path analysis
- **source-validator** — OSHB/MorphGNT consistency, license compliance, data freshness, provenance chain

Three skills in `.claude/commands/`:
- state verification (tests, graph stats, verse counts, alignment) runs from CLAUDE.md's command list; `/session-start` was retired 2026-08-19
- **/session-close** — session close (state update, verification, commit)
- **/verify** — change-type verification matrix (backend, frontend, schema, ingest, text, versification, edge)

## Cross-Project Connections

- **No direct dependencies.** Lamp is self-contained.
- **Methodological inheritance:** Source provenance tiers and three-layer text fidelity model may inform other projects with structured data requirements.
