# /session-start — Lamp State Verification

Run at the beginning of every session to verify project state before work begins.

## Gather state (all in parallel)

1. **Read CLAUDE.md** — extract Current State section (version, graph counts, test count, phases complete, next candidates)
2. **Read TECH_DEBT.md** — check lifecycle states, any items marked CRITICAL
3. **Git status** — `git status`, `git log --oneline -5`
4. **Backend tests** — `cd backend && python -m pytest --tb=no -q` (record pass count; expected: 107+). **Use `python -m pytest`, not bare `pytest`** — the bare command is not on PATH on this machine and exits `command not found`, which reads as a broken test suite rather than a missing launcher. Verified 2026-08-24: **107 passed in 4.52s**.
5. **Frontend build** — `cd frontend && npm run build` (the GenealogyTree.tsx TS errors this line used to warn about were fixed in Phase 2D-7; `npm run build` exits 0)
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
`npm run build` should exit 0. It failed until Phase 2D-7 on GenealogyTree.tsx TS errors; that is fixed, so a failure now means something new broke.

### Check 5: Uncommitted changes
If uncommitted changes exist — from a prior session that didn't close properly, since a close must end in delivery (commit, deploy, save). Describe what's modified. **This very file was found deleted-in-the-working-tree and uncommitted on 2026-08-24, which is exactly the state this check exists to catch.**

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

Fix discrepancies on the authority of evidence: gather actual state from disk, cross-check it against what this file claims, and correct the claim rather than the reading.
