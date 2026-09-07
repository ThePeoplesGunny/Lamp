# Lamp — Technical Debt Register

## OPEN

### TD-001 | HIGH | Hardcoded node IDs across codebase
**Found:** 2026-04-06 | **Pedigree:** B2
"person:adam", "person:shem", etc. repeated as magic strings in API endpoints, frontend routing, and seed scripts (~15 occurrences across 5+ files). No constants module. If ID format changes, grep-and-replace across backend and frontend.
**Files:** `backend/lamp/api/genealogy.py`, `frontend/src/App.tsx`, `frontend/src/components/genealogy/LineageFilter.tsx`

### TD-002 | HIGH | Linear search across all nodes
**Found:** 2026-04-06 | **Pedigree:** A1
`GraphStore.search()` iterates every node, checking 4 string fields per node. O(n*m). At 147 nodes this is <1ms, but no indexing exists. Threshold: ~1000 nodes before this becomes noticeable.
**File:** `backend/lamp/graph/store.py:329-345`

### TD-003 | MEDIUM | No frontend test coverage
**Found:** 2026-04-06 | **Pedigree:** A1 | **Raised 2026-09-07**
16 .tsx component files, zero test files. All validation is manual. Risk: regressions in routing, data rendering, and error states go undetected.
2026-09-07 raises the stake: the KJV base-text work put real branching logic into components — `VersePage` picks between three notes headings and two reference forms, `ReadPage` renders a null KJV verse number as an em-dash, `GreekVerseBody` suppresses its layer toggle when there is no witness. All of it was verified by eye in a browser once and nothing re-checks it. Every backend counterpart got a test.
**Files:** `frontend/src/components/**/*.tsx`

### TD-004 | MEDIUM | Repeated response marshaling
**Found:** 2026-04-06 | **Pedigree:** B2
`summarize()` and `summarize_nations()` in the person endpoint, plus similar field-extraction patterns in places and chronology endpoints. Not yet a maintenance burden, but will compound as more node types are added.
**File:** `backend/lamp/api/genealogy.py`

### TD-005 | MEDIUM | Hardcoded Flood year in frontend
**Found:** 2026-04-06 | **Pedigree:** B2
`FLOOD_YEAR = 1656` hardcoded in TimelineChart. Should come from seed data or API config. Currently correct but not connected to the data source.
**File:** `frontend/src/components/timeline/TimelineChart.tsx:17`

### TD-006 | MEDIUM | CORS localhost-only
**Found:** 2026-04-06 | **Pedigree:** A1
`allow_origins=["http://localhost:5173"]` hardcoded. No env-based override for deployment. Blocks any non-local access.
**File:** `backend/lamp/main.py:32`

### TD-007 | LOW | Unused edge types
**Found:** 2026-04-06 | **Pedigree:** A1
`CONTEMPORARY_OF`, `MENTIONED_IN`, `DURING_EVENT` defined in EdgeType enum but never used in any endpoint, seed data, or query method. Not harmful but adds surface area.
**File:** `backend/lamp/models/relationships.py`

### TD-009 | LOW | `_doc` prose sits inside a dict keyed by book code
**Found:** 2026-09-07 | **Pedigree:** A1
`versification_kjv_to_heb.json` puts a `_doc` string inside `book_overrides`, whose other keys are book codes, and another inside `psalms_offsets`. Nothing reads them by book code so the resolver is safe, but any code iterating the mapping must skip underscore keys — `test_every_override_range_is_well_formed` hit exactly this and needed a guard. A sibling `_notes` object would remove the special case.
**File:** `backend/data/seed/versification_kjv_to_heb.json`

### TD-008 | LOW | Place type filter hardcoded in frontend
**Found:** 2026-04-06 | **Pedigree:** B2
`PLACE_TYPES = ['all', 'region', 'city', 'mountain', 'garden']` hardcoded. If new place types are added to seed data (e.g., "river", "valley"), the filter won't show them without a frontend change.
**File:** `frontend/src/components/places/PlacesPage.tsx:22`

## CLOSED

(none)

## DEFERRED

(none)
