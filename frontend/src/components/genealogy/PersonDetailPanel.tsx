import { useQuery } from '@tanstack/react-query';
import { fetchPerson } from '../../api/client';
import HebrewText from '../hebrew/HebrewText';
import type { PersonDetail, ScriptureRef, RelatedPerson } from '../../types';

interface PersonDetailPanelProps {
  personId: string | null;
  onClose: () => void;
  onNavigate: (personId: string) => void;
}

function formatRef(ref: ScriptureRef): string {
  const base = `${ref.book} ${ref.chapter}:${ref.verse}`;
  return ref.verse_end ? `${base}–${ref.verse_end}` : base;
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
  const { data: person, isLoading } = useQuery<PersonDetail>({
    queryKey: ['person', personId],
    queryFn: () => fetchPerson(personId!),
    enabled: !!personId,
  });

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

          {/* Scripture refs */}
          {person.scripture_refs.length > 0 && (
            <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
              <h4 className="text-xs uppercase tracking-wide text-text-secondary mb-1">References</h4>
              <div className="flex flex-wrap gap-1">
                {person.scripture_refs.map((ref, i) => (
                  <span key={i} className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-accent)' }}>
                    {formatRef(ref)}
                  </span>
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
        </div>
      )}
    </div>
  );
}
