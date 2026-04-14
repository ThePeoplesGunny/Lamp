import type {
  TreeResponse,
  PersonDetail,
  SearchResult,
  NationDetail,
  GraphStats,
  ChronologyResponse,
  PlaceSummary,
  PlaceDetail,
  VerseDetail,
  VerseRef,
  BookSummary,
  ChapterDetail,
} from '../types';

const BASE = '/api/v1';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export function fetchTree(
  root = 'person:adam',
  depth?: number,
  line?: string,
): Promise<TreeResponse> {
  const params = new URLSearchParams();
  params.set('root', root);
  if (depth != null) params.set('depth', String(depth));
  if (line) params.set('line', line);
  return get(`/genealogy/tree?${params}`);
}

export function fetchPerson(id: string): Promise<PersonDetail> {
  return get(`/genealogy/person/${id}`);
}

export function searchNodes(q: string, type?: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q });
  if (type) params.set('type', type);
  return get(`/genealogy/search?${params}`);
}

export function fetchNations(): Promise<NationDetail[]> {
  return get('/genealogy/nations');
}

export function fetchPlaces(): Promise<PlaceSummary[]> {
  return get('/genealogy/places');
}

export function fetchPlace(id: string): Promise<PlaceDetail> {
  return get(`/genealogy/place/${id}`);
}

export function fetchChronology(): Promise<ChronologyResponse> {
  return get('/genealogy/chronology');
}

export function fetchStats(): Promise<GraphStats> {
  return get('/genealogy/stats');
}

export function fetchVerse(verseId: string): Promise<VerseDetail> {
  // Accept either 'verse:GEN.1.1' or 'GEN.1.1'
  const id = verseId.startsWith('verse:') ? verseId : `verse:${verseId}`;
  return get(`/verse/${encodeURIComponent(id)}`);
}

export function fetchVersesMentioning(nodeId: string): Promise<VerseRef[]> {
  return get(`/verse/mentioning/${encodeURIComponent(nodeId)}`);
}

export function fetchBooks(): Promise<BookSummary[]> {
  return get('/books');
}

export function fetchChapter(book: string, chapter: number): Promise<ChapterDetail> {
  return get(`/book/${encodeURIComponent(book)}/chapter/${chapter}`);
}
