import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { fetchPerson, fetchVersesMentioning } from '../../api/client';
import HebrewText from '../hebrew/HebrewText';
import type { PersonDetail, RelatedPerson, RelatedPlace, VerseRef } from '../../types';

interface PersonDetailPanelProps {
  personId: string | null;
  onClose: () => void;
  onNavigate: (personId: string) => void;
}

function RelatedList({
  label,
  persons,
  onNavigate,
}: {
  label: string;
  persons: RelatedPerson[];
  onNavigate: (id: string) => void;
}) {
  if (persons.length === 0) return null;
  return (
    <div className="mt-3">
      <h4 className="text-xs uppercase tracking-wide text-text-secondary mb-1">{label}</h4>
      <div className="flex flex-wrap gap-1.5">
        {persons.map((p) => (
          <button
            key={p.id}
            onClick={() => onNavigate(p.id)}
            className="text-xs px-2 py-1 rounded border transition-colors cursor-pointer"
            style={{
              borderColor: 'var(--color-border)',
              backgroundColor: 'var(--color-bg-tertiary)',
              color: 'var(--color-text-primary)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--color-accent)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--color-border)';
            }}
          >
            {p.name_english}
            {p.relationship === 'concubine_of' && (
              <span className="text-text-secondary ml-1">(concubine)</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function PersonDetailPanel({ personId, onClose, onNavigate }: PersonDetailPanelProps) {
  const navigate = useNavigate();

  const { data: person, isLoading, isError, refetch } = useQuery<PersonDetail>({
    queryKey: ['person', personId],
    queryFn: () => fetchPerson(personId!),
    enabled: !!personId,
  });

  // Parallel fetch: materialized MENTIONS edges (with ranges expanded to individual verses).
  // Failure here should not block the person detail from rendering.
  const { data: mentionVerses } = useQuery<VerseRef[]>({
    queryKey: ['person-mentions', personId],
    queryFn: () => fetchVersesMentioning(personId!),
    enabled: !!personId,
  });

  const handleVerseClick = (verseId: string) => {
    navigate(`/verse/${verseId.replace(/^verse:/, '')}`);
  };

  if (!personId) return null;

  return (
    <div
      className="w-80 border-l overflow-y-auto flex-shrink-0"
      style={{
        borderColor: 'var(--color-border)',
        backgroundColor: 'var(--color-bg-secondary)',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <span className="text-sm text-text-secondary">Person Detail</span>
        <button
          onClick={onClose}
          className="text-text-secondary hover:text-text-primary text-lg leading-none cursor-pointer"
        >
          ×
        </button>
      </div>

      {isLoading && (
        <div className="p-4 text-text-secondary text-sm">Loading...</div>
      )}

      {isError && (
        <div className="p-4 text-center">
          <div className="text-text-secondary text-sm mb-2">Failed to load person</div>
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
      )}

      {person && (
        <div className="p-4">
          {/* Name block */}
          <h2 className="text-xl font-semibold text-text-primary">{person.name_english}</h2>
          {person.name_hebrew && (
            <div className="text-2xl mt-1">
              <HebrewText text={person.name_hebrew} className="text-text-primary" />
            </div>
          )}
          {person.name_hebrew_transliterated && (
            <div className="text-sm text-text-secondary mt-0.5">
              {person.name_hebrew_transliterated}
            </div>
          )}

          {/* Meaning */}
          {person.meaning && (
            <div className="mt-2 text-sm text-text-secondary italic">
              "{person.meaning}"
            </div>
          )}

          {/* Strong's */}
          {person.strongs && (
            <div className="mt-1 text-xs text-text-secondary">
              Strong's: <span className="text-accent">{person.strongs}</span>
            </div>
          )}

          {/* Chronology */}
          {(person.birth_year_am || person.age_at_death) && (
            <div className="mt-3 text-sm border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
              {person.birth_year_am && person.death_year_am && (
                <div className="text-text-secondary">
                  {person.birth_year_am} – {person.death_year_am} AM
                  {person.age_at_death && (
                    <span className="ml-1">({person.age_at_death} years)</span>
                  )}
                </div>
              )}
              {person.birth_year_am && !person.death_year_am && (
                <div className="text-text-secondary">Born: {person.birth_year_am} AM</div>
              )}
            </div>
          )}

          {/* Notes */}
          {person.notes && (
            <div className="mt-3 text-sm text-text-secondary border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
              {person.notes}
            </div>
          )}

          {/* Verses mentioning — materialized MENTIONS edges, click to open verse page */}
          {mentionVerses && mentionVerses.length > 0 && (
            <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
              <h4 className="text-xs uppercase tracking-wide text-text-secondary mb-1">
                Mentioned in {mentionVerses.length} verse{mentionVerses.length === 1 ? '' : 's'}
              </h4>
              <div className="flex flex-wrap gap-1">
                {mentionVerses.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => handleVerseClick(v.id)}
                    className="text-xs px-1.5 py-0.5 rounded border transition-colors cursor-pointer"
                    style={{
                      borderColor: 'var(--color-border)',
                      backgroundColor: 'var(--color-bg-tertiary)',
                      color: 'var(--color-accent)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-accent)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-border)';
                    }}
                    title={`Open ${v.reference}`}
                  >
                    {v.reference}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Relationships */}
          <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
            <RelatedList label="Parents" persons={person.parents} onNavigate={onNavigate} />
            <RelatedList label="Spouses" persons={person.spouses} onNavigate={onNavigate} />
            <RelatedList label="Children" persons={person.children} onNavigate={onNavigate} />
          </div>

          {/* Nations */}
          {person.nations.length > 0 && (
            <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
              <h4 className="text-xs uppercase tracking-wide text-text-secondary mb-1">Nations Founded</h4>
              <div className="flex flex-wrap gap-1.5">
                {person.nations.map((n) => (
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

          {/* Places */}
          {person.places && person.places.length > 0 && (
            <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
              <h4 className="text-xs uppercase tracking-wide text-text-secondary mb-1">Places</h4>
              <div className="space-y-1.5">
                {person.places.map((p: RelatedPlace, i: number) => (
                  <div key={`${p.id}-${p.relationship}-${i}`} className="text-sm">
                    <span className="text-text-primary">{p.name_english}</span>
                    {p.relationship && (
                      <span className="text-text-secondary text-xs ml-1.5">
                        {p.relationship.replace(/_/g, ' ')}
                      </span>
                    )}
                    {p.place_type && (
                      <span className="text-text-secondary text-xs ml-1 opacity-60">
                        ({p.place_type})
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
