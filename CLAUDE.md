# Lamp — Project Instructions

## Overview
Biblical analytical tool — investigation platform for original Hebrew/Greek texts. Strips noise, surfaces patterns, connections, and structures not visible through translation.

## Architecture
- **Backend:** FastAPI + Python 3.12, NetworkX graph engine, JSON persistence
- **Frontend:** React 19 + TypeScript + Vite, React Flow (genealogy trees), Tailwind CSS 4
- **Data model:** Property graph — Person, Place, Nation, Event nodes connected by typed directed edges

## Project Structure
```
backend/
  lamp/           # Python package
    main.py       # FastAPI app
    config.py     # Paths and settings
    models/       # Pydantic models (node types, edge types)
    graph/        # NetworkX graph store and queries
    api/          # FastAPI route modules
    ingest/       # Data loading scripts
    services/     # Business logic
  data/
    seed/         # Hand-curated JSON seed data
    external/     # Downloaded open datasets (gitignored)
    graphs/       # Serialized NetworkX graph (gitignored)
  tests/
frontend/
  src/
    components/   # React components by feature
    api/          # API client
    hooks/        # React hooks
    types/        # TypeScript types
scripts/
  dev.sh          # Start both servers (bash)
  dev.bat         # Start both servers (Windows)
  seed_graph.py   # Rebuild serialized graph from seed data
```

## Running
- Backend: `cd backend && python -m uvicorn lamp.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Both (bash): `bash scripts/dev.sh`
- Both (Windows): `scripts\dev.bat`
- Rebuild graph: `python scripts/seed_graph.py`
- API docs: http://localhost:8000/docs

## Conventions
- Node IDs are namespaced: `person:adam`, `place:eden`, `nation:canaanites`
- Hebrew text stored as Unicode, RTL handled in frontend
- Edge types preserve biblical distinctions (father_of vs mother_of vs wife_of vs concubine_of)
- Scripture refs use format: `{"book": "GEN", "chapter": 5, "verse": 3}`
- Chronology uses Anno Mundi (AM) year system where calculable

## Current State
- Version: 0.1.0
- Phase 0 complete: project scaffold, both servers operational
- Phase 1A complete: data models, GraphStore, seed data (111 persons, 18 nations, 148 edges), 13 integrity tests passing
- Phase 1B complete: all genealogy API endpoints, 14 API tests passing (27 total)
- Phase 1C complete: full frontend — genealogy tree, person detail, search, line filters
- Phase 1D complete: URL routing (react-router-dom), error states (inline retry + error boundary), final verification
- Phase 2A complete: chronology timeline — SVG lifespan bars, shared AppLayout with Tree/Timeline nav, /chronology API endpoint
- Phase 2B complete: places & geography — 18 places, 34 place links, /places and /place/{id} endpoints, PlacesPage with filters, places in PersonDetailPanel
- Graph: 147 nodes (111 persons, 18 nations, 18 places), 182 edges
- Next: Phase 2C (TBD)
