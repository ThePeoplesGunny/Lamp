# /session-start — Lamp State Verification

Run at the beginning of every session to verify project state before work begins.

## Gather state (all in parallel)

1. **Read CLAUDE.md** — extract Current State section (version, graph counts, test count, phases complete, next candidates)
2. **Read TECH_DEBT.md** — check lifecycle states, any items marked CRITICAL
3. **Git status** — `git status`, `git log --oneline -5`
4. **Backend tests** — `cd backend && pytest --tb=no -q` (record pass count; expected: 107+)
5. **Frontend build** — `cd frontend && npx vite build 2>&1 | tail -5` (note: GenealogyTree.tsx TS errors are KNOWN and expected to fail with `npm run build`; `npx vite build` should succeed)
6. **Graph stats** — `cd backend && python -c "from lamp.graph.store import GraphStore; from lamp.config import GRAPH_FILE; g=GraphStore(graph_path=GRAPH_FILE); g.load(); print(f'nodes={g.G.number_of_nodes()} edges={g.G.number_of_edges()}')"` (compare against CLAUDE.md claims). Note: `GraphStore()` with no `graph_path` loads an **empty** graph — the path arg is required; the attribute is `g.G` (not `g.graph`).
7. **Verse store** — `cd backend && python -c "import sqlite3; c=sqlite3.connect('data/verses/verses.db'); print(c.execute('SELECT COUNT(*) FROM verses').fetchone()[0], 'verses')"` (compare against CLAUDE.md)

## Cross-reference checks

### Check 1: Test count stability
pytest count must be ≥ 107. If lower, something regressed. Report immediately.

### Check 2: Graph stats alignment
Node count and edge count from runtime must match CLAUDE.md "Graph" line (±5 tolerance for recent work). If mismatched, CLAUDE.md is stale — update it.

### Check 3: Verse count alignment
SQLite verse count must match CLAUDE.md corpus numbers (23,213 Hebrew + 7,927 Greek = 31,140 verse rows minimum). If mismatched, a reseed may have occurred without state update.

### Check 4: Frontend build
`npx vite build` should succeed even though `npm run build` fails (known GenealogyTree.tsx issue). If vite build also fails, something new broke.

### Check 5: Uncommitted changes
If uncommitted changes exist — from a prior session that didn't close properly (P5 violation). Describe what's modified.

### Check 6: TECH_DEBT lifecycle states
All items should have valid lifecycle states. Any marked CRITICAL should be surfaced in the report.

## Report format

```
SESSION START — <date>
Version: <from CLAUDE.md>
Tests: <count> passing (expected: 107+)
Graph: <nodes> nodes, <edges> edges (CLAUDE.md says: <claimed>)
Verses: <count> (CLAUDE.md says: <claimed>)
Frontend build: PASS (vite) | FAIL — <reason>
TECH_DEBT critical: NONE | <items>
Uncommitted: NONE | <file list>
Alignment: CLEAN | <discrepancies>
Next candidates: <list from CLAUDE.md>
```

Fix discrepancies on authority of evidence (per global P4).
