import HebrewText from '../hebrew/HebrewText';
import type { PlaceSummary } from '../../types';

interface PlaceCardProps {
  place: PlaceSummary;
  isSelected: boolean;
  onClick: () => void;
}

const RELATIONSHIP_LABELS: Record<string, string> = {
  born_at: 'Born',
  died_at: 'Died',
  settled_at: 'Settled',
  migrated_to: 'Migrated',
  territory_of: 'Territory',
};

export default function PlaceCard({ place, isSelected, onClick }: PlaceCardProps) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-lg border transition-colors cursor-pointer"
      style={{
        backgroundColor: isSelected ? 'var(--color-bg-tertiary)' : 'var(--color-bg-secondary)',
        borderColor: isSelected ? 'var(--color-accent)' : 'var(--color-border)',
      }}
    >
      {/* Name */}
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-text-primary">{place.name_english}</h3>
        {place.place_type && (
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{ backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-text-secondary)' }}
          >
            {place.place_type}
          </span>
        )}
      </div>

      {/* Hebrew */}
      {place.name_hebrew && (
        <div className="text-base mt-0.5">
          <HebrewText text={place.name_hebrew} className="text-text-primary" />
        </div>
      )}

      {/* Meaning */}
      {place.meaning && (
        <div className="text-xs text-text-secondary mt-1 italic">"{place.meaning}"</div>
      )}

      {/* Connected persons */}
      {place.connected_persons.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {place.connected_persons.map((c, i) => (
            <span
              key={`${c.id}-${c.relationship}-${i}`}
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: 'var(--color-bg)',
                color: 'var(--color-text-secondary)',
                border: '1px solid var(--color-border)',
              }}
            >
              {c.name_english}
              <span className="ml-1 opacity-60">
                {RELATIONSHIP_LABELS[c.relationship ?? ''] ?? c.relationship}
              </span>
            </span>
          ))}
        </div>
      )}
    </button>
  );
}
