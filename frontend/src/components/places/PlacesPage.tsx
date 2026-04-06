import { useState, useCallback, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import PlaceCard from './PlaceCard';
import { fetchPlaces, fetchPlace } from '../../api/client';
import HebrewText from '../hebrew/HebrewText';
import type { PlaceSummary, PlaceDetail, ScriptureRef } from '../../types';

function formatRef(ref: ScriptureRef): string {
  const base = `${ref.book} ${ref.chapter}:${ref.verse}`;
  return ref.verse_end ? `${base}–${ref.verse_end}` : base;
}

const RELATIONSHIP_LABELS: Record<string, string> = {
  born_at: 'Born here',
  died_at: 'Died here',
  settled_at: 'Settled here',
  migrated_to: 'Migrated here',
  territory_of: 'Territory',
};

const PLACE_TYPES = ['all', 'region', 'city', 'mountain', 'garden'] as const;

export default function PlacesPage() {
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');

  const { data: places, isLoading, isError, refetch } = useQuery<PlaceSummary[]>({
    queryKey: ['places'],
    queryFn: fetchPlaces,
  });

  const { data: placeDetail } = useQuery<PlaceDetail>({
    queryKey: ['place', selectedPlaceId],
    queryFn: () => fetchPlace(selectedPlaceId!),
    enabled: !!selectedPlaceId,
  });

  const filteredPlaces = useMemo(() => {
    if (!places) return [];
    if (filterType === 'all') return places;
    return places.filter(p => p.place_type === filterType);
  }, [places, filterType]);

  const handlePlaceClick = useCallback((id: string) => {
    setSelectedPlaceId(prev => prev === id ? null : id);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedPlaceId(null);
  }, []);

  useEffect(() => {
    document.title = 'Places — Lamp';
  }, []);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-text-secondary">Loading places...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-text-secondary mb-2">Failed to load places</div>
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 text-sm rounded border cursor-pointer transition-colors"
            style={{
              borderColor: 'var(--color-accent)',
              color: 'var(--color-accent)',
              backgroundColor: 'transparent',
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Place list */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Filter bar */}
        <div className="px-4 py-2 flex items-center gap-2 flex-shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
          <span className="text-xs text-text-secondary">Type:</span>
          {PLACE_TYPES.map(type => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className="px-3 py-1 text-xs rounded border transition-colors cursor-pointer capitalize"
              style={{
                backgroundColor: filterType === type ? 'var(--color-accent-dim)' : 'var(--color-bg-secondary)',
                borderColor: filterType === type ? 'var(--color-accent)' : 'var(--color-border)',
                color: filterType === type ? 'var(--color-accent)' : 'var(--color-text-secondary)',
              }}
            >
              {type}
            </button>
          ))}
          <span className="text-xs text-text-secondary ml-auto">
            {filteredPlaces.length} place{filteredPlaces.length !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Cards grid */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredPlaces.map(place => (
              <PlaceCard
                key={place.id}
                place={place}
                isSelected={selectedPlaceId === place.id}
                onClick={() => handlePlaceClick(place.id)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Detail panel */}
      {selectedPlaceId && placeDetail && (
        <div
          className="w-80 border-l overflow-y-auto flex-shrink-0"
          style={{
            borderColor: 'var(--color-border)',
            backgroundColor: 'var(--color-bg-secondary)',
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <span className="text-sm text-text-secondary">Place Detail</span>
            <button
              onClick={handleCloseDetail}
              className="text-text-secondary hover:text-text-primary text-lg leading-none cursor-pointer"
            >
              ×
            </button>
          </div>

          <div className="p-4">
            {/* Name */}
            <h2 className="text-xl font-semibold text-text-primary">{placeDetail.name_english}</h2>
            {placeDetail.name_hebrew && (
              <div className="text-2xl mt-1">
                <HebrewText text={placeDetail.name_hebrew} className="text-text-primary" />
              </div>
            )}
            {placeDetail.name_hebrew_transliterated && (
              <div className="text-sm text-text-secondary mt-0.5">
                {placeDetail.name_hebrew_transliterated}
              </div>
            )}

            {/* Type */}
            {placeDetail.place_type && (
              <div className="mt-2">
                <span
                  className="text-xs px-2 py-0.5 rounded capitalize"
                  style={{ backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-text-secondary)' }}
                >
                  {placeDetail.place_type}
                </span>
              </div>
            )}

            {/* Meaning */}
            {placeDetail.meaning && (
              <div className="mt-2 text-sm text-text-secondary italic">
                "{placeDetail.meaning}"
              </div>
            )}

            {/* Strong's */}
            {placeDetail.strongs && (
              <div className="mt-1 text-xs text-text-secondary">
                Strong's: <span className="text-accent">{placeDetail.strongs}</span>
              </div>
            )}

            {/* Notes */}
            {placeDetail.notes && (
              <div className="mt-3 text-sm text-text-secondary border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
                {placeDetail.notes}
              </div>
            )}

            {/* Scripture refs */}
            {placeDetail.scripture_refs.length > 0 && (
              <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
                <h4 className="text-xs uppercase tracking-wide text-text-secondary mb-1">References</h4>
                <div className="flex flex-wrap gap-1">
                  {placeDetail.scripture_refs.map((ref, i) => (
                    <span key={i} className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-accent)' }}>
                      {formatRef(ref)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Connected persons */}
            {placeDetail.persons.length > 0 && (
              <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
                <h4 className="text-xs uppercase tracking-wide text-text-secondary mb-1">Persons</h4>
                <div className="space-y-1.5">
                  {placeDetail.persons.map((p, i) => (
                    <div key={`${p.id}-${p.relationship}-${i}`} className="text-sm">
                      <span className="text-text-primary font-medium">{p.name_english}</span>
                      <span className="text-text-secondary text-xs ml-1.5">
                        {RELATIONSHIP_LABELS[p.relationship ?? ''] ?? p.relationship}
                      </span>
                      {p.notes && (
                        <div className="text-xs text-text-secondary mt-0.5 pl-2 border-l" style={{ borderColor: 'var(--color-border)' }}>
                          {p.notes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Connected nations */}
            {placeDetail.nations.length > 0 && (
              <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
                <h4 className="text-xs uppercase tracking-wide text-text-secondary mb-1">Nations</h4>
                <div className="flex flex-wrap gap-1.5">
                  {placeDetail.nations.map((n) => (
                    <span
                      key={n.id}
                      className="text-xs px-2 py-1 rounded"
                      style={{
                        backgroundColor: 'var(--color-bg-tertiary)',
                        color: 'var(--color-nation)',
                        border: '1px solid var(--color-nation)',
                      }}
                    >
                      {n.name_english}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
