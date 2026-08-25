# /verify — Lamp Change-Type Verification Matrix

Run verification appropriate to the type of change just made. Different changes have different blast radii.

## Usage

$ARGUMENTS should specify the change type: `backend`, `frontend`, `schema`, `ingest`, `text`, `versification`, `edge`

## Verification by type

### `backend` — Python logic changes
```bash
cd backend && pytest
cd backend && pytest -k "<affected_module>"
```
All 107+ tests must pass. If adding new functionality, new test(s) should exist.

### `frontend` — React/TypeScript changes
```bash
cd frontend && npx vite build
cd frontend && npm run lint
```
Build must succeed (via vite). Lint must pass. If touching GenealogyTree.tsx, attempt `npm run build` to see if TS errors are resolved.

### `schema` — Graph model or Pydantic model changes
```bash
cd backend && pytest tests/test_graph_integrity.py
cd backend && pytest tests/test_graph_verses.py
cd backend && python -c "from lamp.graph.store import GraphStore; from lamp.config import GRAPH_FILE; g=GraphStore(graph_path=GRAPH_FILE); g.load(); print(f'nodes={g.G.number_of_nodes()} edges={g.G.number_of_edges()}')"
```
Node/edge counts must not decrease unless intentional. All integrity tests pass.

### `ingest` — Data loading script changes
```bash
cd backend && pytest tests/test_oshb_ingest.py tests/test_morphgnt_ingest.py tests/test_verse_store.py
cd backend && python -c "import sqlite3; c=sqlite3.connect('data/verses/verses.db'); print(c.execute('SELECT COUNT(*) FROM verses').fetchone()[0])"
```
Record count must match or exceed previous. Verse store tests pass.

### `text` — Hebrew/Greek text data changes
Three-layer integrity check:
```bash
cd backend && pytest tests/test_oshb_ingest.py -v  # consonantal + pointed + cantillated
cd backend && pytest tests/test_morphgnt_ingest.py -v  # 2-layer Greek
```
Verify: consonantal layer preserved (no niqqud in consonantal-only field), pointed layer has niqqud, cantillated layer has te'amim marks. Ketiv/Qere preserved. Parashah markers intact.

### `versification` — Mapping changes between Hebrew/Greek and English numbering
```bash
cd backend && pytest tests/test_verse_store.py -v
# Spot checks at known boundary chapters:
cd backend && python -c "
import sqlite3
c = sqlite3.connect('data/verses/verses.db')
# Psalm 51 superscription (Hebrew v1 = English title)
r = c.execute(\"SELECT verse_id FROM verses WHERE verse_id LIKE 'PSA.51.%'\").fetchall()
print(f'PSA.51 verses: {len(r)}')
# Num 16/17 split
r = c.execute(\"SELECT verse_id FROM verses WHERE verse_id LIKE 'NUM.17.%'\").fetchall()
print(f'NUM.17 verses: {len(r)}')
"
```

### `edge` — Relationship/citation edge changes
```bash
cd backend && pytest tests/test_graph_integrity.py tests/test_graph_verses.py
cd backend && python -c "
from lamp.graph.store import GraphStore
from lamp.config import GRAPH_FILE
g = GraphStore(graph_path=GRAPH_FILE); g.load()
edges_by_type = {}
for u, v, d in g.G.edges(data=True):
    t = d.get('type', 'unknown')
    edges_by_type[t] = edges_by_type.get(t, 0) + 1
for t, c in sorted(edges_by_type.items()):
    print(f'  {t}: {c}')
"
```
Edge counts should only increase unless a reseed explicitly drops edges.
