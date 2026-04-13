# Verse-Graph Schema — Design Doc

**Status:** LOCKED — approved by Gunny 2026-04-13, all 4 open questions confirmed per proposed defaults
**Phase:** 2C-1 Step 1 (complete)
**Date:** 2026-04-13

## Purpose

Bible verses become first-class nodes in the Lamp graph, linked by typed directed edges to existing `Person`, `Place`, `Nation`, and (future) `Event` nodes. This is the core engine of the entire project — every future analytical feature (cross-references, morphology, thematic analysis, translation-drift study) attaches to this substrate.

The schema must be designed once and held stable. Getting it wrong means ripping out the engine later.

---

## Guiding Principles

1. **Exegesis, not eisegesis.** Original-language text is canonical; translations are reference layers atop it. The schema must never force a translator's gloss to stand in for the source text.
2. **Total accuracy, layered.** Hebrew text is stored in three separable strata:
    - **Consonantal** — the oldest stratum, matching pre-Masoretic manuscripts (DSS, LXX Vorlage)
    - **Pointed (niqqud)** — vowel pointing added by the Masoretes (~7th–10th c. AD)
    - **Cantillated (te'amim)** — cantillation marks added with the pointing, encoding phrasing and accentuation
    Any query can request the text at any stratum.
3. **Preserve translation distinctions.** Translation drift across history is itself analytical material. Translations attach as separate layers, not mutations of the canonical text.
4. **Every edge is exegetically meaningful.** Edge types encode distinctions the text itself makes — `spoken_by` ≠ `mentions` ≠ `addressed_to`.

---

## Node: Verse

### ID Format

```
verse:{BOOK}.{CHAPTER}.{VERSE}
```

Examples:
- `verse:GEN.1.1`
- `verse:GEN.5.3`
- `verse:PSA.119.105`
- `verse:JHN.3.16`

`BOOK` is the 3-letter book code already used in `ScriptureRef.book` (GEN, EXO, LEV, …). Dot-delimited to keep colons reserved for the node-type prefix.

### Payload (Hebrew OT — Phase 2C-1 Step 2)

```python
class Verse(BaseModel):
    id: str                          # "verse:GEN.5.3"
    node_type: str = "verse"
    book: str                        # "GEN"
    chapter: int                     # 5
    verse: int                       # 3
    canon: str                       # "tanakh" | "nt" | "lxx"
    language: str                    # "hbo" (Hebrew) | "grc" (Greek) | "arc" (Aramaic)

    # Three-layer canonical text (Hebrew OT)
    text_consonantal: str            # Unpointed Hebrew — pre-Masoretic stratum
    text_pointed: str                # With niqqud (vowels)
    text_cantillated: str            # With niqqud + te'amim (full Masoretic)

    # Word-level morphology (per-word, in verse order)
    words: list[VerseWord]

    # Source provenance (Research Methodology requirement)
    source: str                      # "OSHB-WLC-2.5" or similar exact version
    source_tier: int                 # Tier per CLAUDE.md — OSHB = Tier 1
```

### Word-level morphology

```python
class VerseWord(BaseModel):
    position: int                    # 1-indexed position in verse
    text_consonantal: str            # This word, consonantal only
    text_pointed: str                # With niqqud
    text_cantillated: str            # With te'amim
    lemma: str | None                # Dictionary form
    strongs: str | None              # "H1254"
    morph_code: str | None           # OSHB morphology code, e.g. "HVqp3ms"
    transliteration: str | None      # For non-Hebrew readers
```

Why word-level: morphology is exegesis-grade data. "God created" (`bara'`, H1254, perfect 3ms) is load-bearing — the grammatical form is part of what the text says. Storing only verse-level text throws away the exegesis payload OSHB hands us for free.

### Scaling note (for Gunny visibility, not blocking)

~23,000 verses × ~15 words/verse = ~345,000 word records. Current graph JSON is ~180 edges, 147 nodes. Adding verse nodes expands the graph by 3 orders of magnitude.

**Recommendation:** keep verse nodes in the same NetworkX graph (unified traversal is the whole point), but split persistence — canonical verse text lives in a separate JSON (or SQLite) keyed by verse ID, graph stores only the node ID + minimal metadata + edges. Loads on demand. Decision deferrable to Step 2; schema doesn't depend on it.

---

## Edge Types (Verse ↔ Existing Nodes)

All edges are directed. Source and target listed per type.

### `mentions` — verse → person/place/nation
The node is named or referenced in the verse. Most common edge. Seeded from existing `scripture_refs` fields in Step 3.

### `spoken_by` — verse → person
The verse is direct speech attributed to this person. Exegetically distinct from `mentions`: Jesus speaking in John 3:16 is different from being named in Matthew 1:1.

### `addressed_to` — verse → person/nation
The verse is speech/writing directed *at* this recipient. Paul's letters, prophetic oracles ("Thus says the LORD to Pharaoh…").

### `set_in` — verse → place
The narrative action of the verse occurs at this location. Different from `mentions`: Gen 22:2 *mentions* Moriah but the binding-of-Isaac narrative is *set in* Moriah across multiple verses.

### `occurs_during` — verse → event  *(future, when Event nodes exist)*
The verse narrates an event node (the Exodus, the Flood, the Davidic coronation).

### `quotes` — verse → verse
This verse quotes another verse. Primary use: NT quoting OT. Direction: quoting verse → quoted verse. Edge metadata should record the translation stratum being quoted (MT vs. LXX vs. paraphrase) — a major exegetical signal.

### `parallel_to` — verse ↔ verse
Synoptic parallels (Matt/Mark/Luke), Chronicles/Kings parallels, Psalm parallels. Undirected in meaning but stored as two directed edges or a symmetric edge type — TBD in Step 2.

### `alludes_to` — verse → verse  *(softer than `quotes`)*
Lexical or thematic allusion without direct quotation. Marked separately so "alludes" doesn't get counted as "quotes" in analysis.

### Exegetical rationale for this set

Every distinction above is one the text itself makes and serious exegesis relies on. Collapsing `spoken_by` into `mentions` loses the difference between what Jesus said and what Matthew said about Jesus. Collapsing `quotes` into `alludes_to` loses the ability to track NT use of OT precisely. These are not ergonomic conveniences — they are the analytical substrate.

### Deferred / not included

- Sentiment, theme, doctrine edges: interpretive, not textual. Would be eisegesis baked into the schema.
- Chapter/book container edges: derivable from verse ID (`verse:GEN.5.3` → chapter 5 of GEN). Don't materialize what you can compute.

---

## Translation Layers

### Decision: translations as separate verse-reference records, not mutations of canonical verse nodes

Each translation is a separate store keyed by `(translation_id, book, chapter, verse)`:

```python
class TranslationText(BaseModel):
    translation: str                 # "KJV-1769" | "ASV-1901" | "WEB" | "GEN-1599" | "TYN" | "DRA"
    verse_id: str                    # "verse:GEN.5.3" — foreign key to canonical verse node
    text: str                        # The translated text
    source: str                      # Exact source file/edition
    source_tier: int
```

### Why not on the verse node

1. **Exegesis discipline.** A translation on the canonical node invites treating it as equivalent to the original. Physical separation in storage enforces epistemic separation in use.
2. **Translation history.** Comparing KJV 1769 vs. ASV 1901 vs. Geneva 1599 on the same verse is a first-class analytical operation. Separate store makes the comparison trivial.
3. **Scaling.** Adding translations doesn't bloat the canonical graph.

### Not on the graph at all

Translations are reference data, not graph-structural. A KJV verse doesn't have edges to Abraham — the **canonical verse** does. Translations are looked up *from* the canonical verse node when the user wants to display or compare renderings.

---

## Link Seeding (Phase 2C-1 Step 3)

Every existing Person, Place, and Nation has `scripture_refs: list[ScriptureRef]`. Step 3 walks those and creates `mentions` edges from each referenced verse node to the entity.

**Example:** `person:adam` has `scripture_refs: [ScriptureRef(book="GEN", chapter=1, verse=26), ScriptureRef(book="GEN", chapter=5, verse=3), ...]`. Step 3 creates:

```
verse:GEN.1.26 --mentions--> person:adam
verse:GEN.5.3  --mentions--> person:adam
```

This is pure mechanical translation of existing curated data into graph edges. No new claims, no inference — just materializing what's already asserted.

**`spoken_by`, `addressed_to`, `set_in`, `quotes`, `parallel_to`** are not auto-seeded from existing data (we don't have that information on current nodes). They get populated by:
- Hand-curation into a new seed file (`backend/data/seed/verse_edges.json`)
- Future auto-detection passes (e.g., regex-based direct-speech extraction) — flagged as `inferred` per Research Methodology, staged, not auto-canonical

---

## Model Changes Summary

### New files (Step 2)
- `backend/lamp/models/verse.py` — `Verse`, `VerseWord`, `TranslationText`
- `backend/lamp/ingest/oshb.py` — OSHB XML parser → Verse records
- `backend/lamp/graph/store.py` — add `add_verse`, `get_verse`, `get_verses_mentioning(node_id)`, `get_mentions(verse_id)`

### Changes to existing code
- `models/relationships.py` — expand `EdgeType`: add `MENTIONS` (verse→any), `SPOKEN_BY`, `ADDRESSED_TO`, `SET_IN`, `OCCURS_DURING`, `QUOTES`, `PARALLEL_TO`, `ALLUDES_TO`. The existing `MENTIONED_IN` (any → scripture_ref) stays for backward compat during migration or gets deprecated — decide in Step 2.
- `graph/store.py` — add verse-aware query methods

### Unchanged
- Person, Place, Nation models — no changes. Their `scripture_refs` field remains as curated metadata; the graph edges are derived from it, not replacing it.

---

## Resolved Decisions (locked 2026-04-13)

1. **Book codes:** uppercase 3-letter (`GEN`, `EXO`, `LEV` …); OSIS codes mapped on ingest via a book-code table.
2. **Canon scope:** ingest all LXX books including deuterocanon/apocrypha; each verse node carries `canon` field (`tanakh` | `nt` | `lxx`) so filtering is trivial.
3. **Ketiv/Qere:** preserve both on the word record (`text_ketiv`, `text_qere` fields on `VerseWord` when they differ) — exegesis over smoothing.
4. **Parashah markers:** preserve OSHB section markers (samekh/pe) as verse-level metadata.

---

## What this doc is NOT

- Not a commitment to implementation details of Step 2 or 3. Those are design decisions for when we get there.
