from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lamp.config import API_PREFIX, GRAPH_FILE, VERSES_DB_FILE
from lamp.graph.store import GraphStore
from lamp.api.genealogy import router as genealogy_router, init_store
from lamp.api.verses import (
    router as verses_router,
    nav_router as nav_router,
    init_store as init_verse_store,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load the graph + verse SQLite
    store = GraphStore(GRAPH_FILE, VERSES_DB_FILE)
    store.load()
    init_store(store)
    init_verse_store(store)
    stats = store.stats()
    print(f"Lamp graph loaded: {stats['total_nodes']} nodes, {stats['edges']} edges")
    yield
    store.close()


app = FastAPI(
    title="Lamp",
    description="Biblical analytical tool — investigation platform for original Hebrew/Greek texts",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{API_PREFIX}/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


app.include_router(genealogy_router, prefix=API_PREFIX)
app.include_router(verses_router, prefix=API_PREFIX)
app.include_router(nav_router, prefix=API_PREFIX)
