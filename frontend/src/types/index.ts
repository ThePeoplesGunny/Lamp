/** Scripture reference */
export interface ScriptureRef {
  book: string;
  chapter: number;
  verse: number;
  verse_end?: number;
}

/** A person node from the API tree endpoint */
export interface TreePersonNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: {
    name_english: string;
    name_hebrew?: string;
    meaning?: string;
    strongs?: string;
    sex?: string;
    birth_year_am?: number;
    death_year_am?: number;
    age_at_death?: number;
  };
}

/** An edge from the API tree endpoint */
export interface TreeEdge {
  id: string;
  source: string;
  target: string;
  data: {
    type: string;
    birth_order?: number;
  };
}

/** Tree response from /api/v1/genealogy/tree */
export interface TreeResponse {
  nodes: TreePersonNode[];
  edges: TreeEdge[];
}

/** Related person summary (parents, children, spouses) */
export interface RelatedPerson {
  id: string;
  name_english: string;
  name_hebrew?: string;
  sex?: string;
  relationship?: string;
  birth_order?: number;
}

/** Related nation summary */
export interface RelatedNation {
  id: string;
  name_english: string;
  name_hebrew?: string;
  relationship?: string;
}

/** Full person detail from /api/v1/genealogy/person/{id} */
export interface PersonDetail {
  id: string;
  name_english: string;
  name_hebrew?: string;
  name_hebrew_transliterated?: string;
  strongs?: string;
  meaning?: string;
  sex?: string;
  birth_year_am?: number;
  death_year_am?: number;
  age_at_death?: number;
  scripture_refs: ScriptureRef[];
  notes?: string;
  parents: RelatedPerson[];
  spouses: RelatedPerson[];
  children: RelatedPerson[];
  nations: RelatedNation[];
  places: RelatedPlace[];
}

/** Search result item */
export interface SearchResult {
  id: string;
  name_english: string;
  name_hebrew?: string;
  strongs?: string;
  node_type?: string;
  meaning?: string;
}

/** Nation with ancestor info */
export interface NationDetail {
  id: string;
  name_english: string;
  name_hebrew?: string;
  strongs?: string;
  meaning?: string;
  eponymous_ancestor?: {
    id: string;
    name_english: string;
    name_hebrew?: string;
  };
  scripture_refs: ScriptureRef[];
  notes?: string;
}

/** Related place summary (for person detail) */
export interface RelatedPlace {
  id: string;
  name_english: string;
  name_hebrew?: string;
  place_type?: string;
  relationship?: string;
  notes?: string;
}

/** Connected person/nation summary (for place detail) */
export interface PlaceConnection {
  id: string;
  name_english: string;
  name_hebrew?: string;
  sex?: string;
  node_type?: string;
  relationship?: string;
  notes?: string;
}

/** Place summary from /api/v1/genealogy/places */
export interface PlaceSummary {
  id: string;
  name_english: string;
  name_hebrew?: string;
  name_hebrew_transliterated?: string;
  strongs?: string;
  meaning?: string;
  place_type?: string;
  scripture_refs: ScriptureRef[];
  notes?: string;
  connected_persons: PlaceConnection[];
}

/** Full place detail from /api/v1/genealogy/place/{id} */
export interface PlaceDetail {
  id: string;
  name_english: string;
  name_hebrew?: string;
  name_hebrew_transliterated?: string;
  strongs?: string;
  meaning?: string;
  place_type?: string;
  scripture_refs: ScriptureRef[];
  notes?: string;
  persons: PlaceConnection[];
  nations: PlaceConnection[];
}

/** Chronology person for timeline */
export interface ChronologyPerson {
  id: string;
  name_english: string;
  name_hebrew?: string;
  sex: string;
  birth_year_am: number;
  death_year_am: number;
  age_at_death?: number;
  generation: number;
}

/** Chronology response from /api/v1/genealogy/chronology */
export interface ChronologyResponse {
  persons: ChronologyPerson[];
  year_range: { min: number; max: number };
}

/** Graph stats */
export interface GraphStats {
  persons: number;
  nations: number;
  places: number;
  verses?: number;
  edges: number;
  total_nodes: number;
}

// ── Verse types ───────────────────────────────────────────

/** One word within a verse, with full morphology. */
export interface VerseWord {
  position: number;
  text_canonical: string;
  // Hebrew layers (empty strings for Greek)
  text_consonantal: string;
  text_pointed: string;
  text_cantillated: string;
  // Greek layers (empty strings for Hebrew)
  text_plain: string;
  text_accented: string;
  // Morphology
  lemma?: string;
  strongs?: string;
  morph_code?: string;
  transliteration?: string;
  // Hebrew variant readings
  text_ketiv?: string;
  text_qere?: string;
}

/** Entity mentioned in a verse (reverse traversal). */
export interface VerseMention {
  id: string;
  node_type?: string;
  name_english?: string;
  name_hebrew?: string;
}

/** A translation of a single verse, attached to the canonical verse node. */
export interface Translation {
  translation: string;    // "KJV-1769"
  text: string;
  source: string;
  source_tier: number;
}

/** Full verse payload from /api/v1/verse/{id}. */
export interface VerseDetail {
  id: string;
  reference: string;              // "Genesis 1:1"
  book: string;
  book_name: string;
  chapter: number;
  verse: number;
  canon: 'tanakh' | 'nt' | 'lxx';
  language: 'hbo' | 'grc' | 'arc';
  text_canonical: string;
  // Hebrew layers
  text_consonantal: string;
  text_pointed: string;
  text_cantillated: string;
  // Greek layers
  text_plain: string;
  text_accented: string;
  // Hebrew-specific scribal features
  parashah_marker?: string | null;
  reversed_nun: boolean;
  notes: string[];
  // Payload
  words: VerseWord[];
  mentions: VerseMention[];
  translations: Translation[];
  prev_id: string | null;
  next_id: string | null;
  source: string;
  source_tier: number;
}

/** Short verse reference for lists of "verses mentioning X". */
export interface VerseRef {
  id: string;
  reference: string;
  book: string;
  chapter: number;
  verse: number;
  canon?: string;
  language?: string;
}

/** Book summary for the navigation UI. */
export interface BookSummary {
  book: string;              // "GEN"
  name: string;              // "Genesis"
  canon: 'tanakh' | 'nt' | 'lxx';
  language: 'hbo' | 'grc' | 'arc';
  chapter_count: number;
  verse_count: number;
}

/** Lightweight verse for the chapter verse-list. */
export interface ChapterVerse {
  id: string;
  verse: number;
  text_canonical: string;
  parashah_marker?: string | null;
  reversed_nun: boolean;
}

/** Chapter payload from /api/v1/book/{code}/chapter/{n}. */
export interface ChapterDetail {
  book: string;
  book_name: string;
  chapter: number;
  verses: ChapterVerse[];
}
