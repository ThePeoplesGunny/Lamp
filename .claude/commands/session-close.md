# /session-close — Lamp Session Close

Execute after completing a unit of work. Prevents state drift between sessions.

## Required argument

$ARGUMENTS should contain: `<phase_id> <summary>`
Example: `/session-close 2D-6-batch2 QUOTES expansion — Romans (+25 edges)`

If $ARGUMENTS is empty, check git diff and recent work to infer context, then confirm.

## Phase 1: Gather current state

Run in parallel:
1. `git diff --stat` — what changed
2. `cd backend && pytest --tb=no -q` — test count (must still pass)
3. `cd frontend && npm run build` — frontend still builds (read the exit code bare, not through a pipe)
4. Graph/verse counts (same commands as session-start)
5. `git log --oneline -3` — recent commits

## Phase 2: Execute close checklist

### Step 1: Update CLAUDE.md Current State
- **Version:** bump if warranted (minor for new features, patch for fixes)
- **Graph/Corpus counts:** update to actual measured values from Phase 1
- **Tests:** update count if it changed
- **Phases complete:** add entry for this delivery with detail
- **Next candidates:** update if direction changed

### Step 2: Update TECH_DEBT.md
- If any debt was resolved, update lifecycle state
- If new debt was introduced, add entry
- If any item changed criticality, update

### Step 3: Git commit
Stage changed files. Commit message format:
```
Phase <id>: <summary>

<detail if non-obvious>
```
Push to remote.

## Phase 3: Verification

Report:
- Phase delivered: ID and summary
- Tests: before → after count
- Graph: before → after counts
- Files modified
- TECH_DEBT changes (if any)
- Any discrepancies resolved

## Verification by change type — the method matches the blast radius

- **Backend logic** → `cd backend && pytest` (full suite)
- **Frontend component** → `npm run build` (runs `tsc -b && vite build`) + visual check if possible
- **Schema/graph model** → node/edge count validation + test_graph_integrity
- **Data import/ingest** → record count comparison + verse_store tests
- **Hebrew/Greek text** → three-layer integrity: consonantal layer preserved, niqqud intact, cantillation marks present (test_oshb_ingest / test_morphgnt_ingest)
- **Versification changes** → verse count + boundary spot checks (edge chapters)
