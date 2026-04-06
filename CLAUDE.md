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
  dev.sh          # Start both servers
```

## Running
- Backend: `cd backend && python -m uvicorn lamp.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Both: `bash scripts/dev.sh`
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
- Next: Phase 1D — polish (URL routing, error states, final verification)
