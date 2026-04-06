import type {
  TreeResponse,
  PersonDetail,
  SearchResult,
  NationDetail,
  GraphStats,
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

export function fetchStats(): Promise<GraphStats> {
  return get('/genealogy/stats');
}
