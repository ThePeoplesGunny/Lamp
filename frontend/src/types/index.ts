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
  edges: number;
  total_nodes: number;
}
