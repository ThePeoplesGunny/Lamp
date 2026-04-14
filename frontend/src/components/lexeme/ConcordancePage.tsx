import { useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { fetchLexemeOccurrences } from '../../api/client';
import HebrewText from '../hebrew/HebrewText';
import type { LexemeOccurrence, LexemeOccurrenceResponse } from '../../types';

type CanonFilter = 'all' | 'tanakh' | 'nt';

function ResultRow({
  result,
  onClick,
}: {
  result: LexemeOccurrence;
  onClick: () => void;
}) {
  const isHebrew = result.language === 'hbo';
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2 rounded transition-colors cursor-pointer border"
      style={{ borderColor: 'transparent', backgroundColor: 'transparent' }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--color-bg-tertiary)';
        e.currentTarget.style.borderColor = 'var(--color-border)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'transparent';
        e.currentTarget.style.borderColor = 'transparent';
      }}
    >
      <div className="flex items-baseline gap-3">
        <span
          className="text-xs flex-shrink-0 w-32"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {result.reference}
        </span>
        {isHebrew ? (
          <HebrewText text={result.text_canonical} className="text-base leading-relaxed" />
        ) : (
          <span lang="grc" className="text-base leading-relaxed">
            {result.text_canonical}
          </span>
        )}
        {result.match_count > 1 && (
          <span
            className="text-[10px] ml-auto flex-shrink-0 px-1.5 py-0.5 rounded"
            style={{ color: 'var(--color-accent)', backgroundColor: 'var(--color-bg-tertiary)' }}
            title={`${result.match_count} occurrences in this verse`}
          >
            ×{result.match_count}
          </span>
        )}
      </div>
    </button>
  );
}

export default function ConcordancePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const lemma = searchParams.get('lemma') || undefined;
  const strongs = searchParams.get('strongs') || undefined;
  const canon = (searchParams.get('canon') as CanonFilter) || 'all';
  const hasQuery = !!lemma || !!strongs;

  const queryKey = useMemo(
    () => ['lexeme', lemma ?? null, strongs ?? null, canon],
    [lemma, strongs, canon],
  );

  const { data, isLoading, isError, error } = useQuery<LexemeOccurrenceResponse>({
    queryKey,
    queryFn: () =>
      fetchLexemeOccurrences({ lemma, strongs, canon, limit: 500 }),
    enabled: hasQuery,
  });

  useEffect(() => {
    if (lemma) document.title = `${lemma} — concordance — Lamp`;
    else if (strongs) document.title = `H${strongs} — concordance — Lamp`;
    else document.title = 'Concordance — Lamp';
  }, [lemma, strongs]);

  const handleResultClick = (verseId: string) => {
    navigate(`/verse/${verseId.replace(/^verse:/, '')}`);
  };

  const handleCanonChange = (value: CanonFilter) => {
    const p = new URLSearchParams(searchParams);
    if (value === 'all') p.delete('canon');
    else p.set('canon', value);
    setSearchParams(p);
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-6 space-y-4">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Concordance
          </h2>
          {hasQuery ? (
            <div className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              {lemma && (
                <>
                  Searching lemma: <code style={{ color: 'var(--color-accent)' }}>{lemma}</code>
                </>
              )}
              {strongs && (
                <>
                  Searching Strong's: <code style={{ color: 'var(--color-accent)' }}>H{strongs}</code>
                </>
              )}
              {data && (
                <span className="ml-2">
                  · <strong>{data.total}</strong> occurrence{data.total === 1 ? '' : 's'}
                  {data.returned < data.total && (
                    <span> (showing first {data.returned})</span>
                  )}
                </span>
              )}
            </div>
          ) : (
            <div className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              No query. Click a word from any verse page to explore its usage across scripture,
              or navigate to this page with <code>?lemma=...</code> or <code>?strongs=...</code>.
            </div>
          )}
        </div>

        {hasQuery && (
          <div className="flex gap-1">
            {(['all', 'tanakh', 'nt'] as CanonFilter[]).map((c) => (
              <button
                key={c}
                onClick={() => handleCanonChange(c)}
                className="text-xs px-3 py-1 rounded border transition-colors cursor-pointer"
                style={{
                  borderColor: c === canon ? 'var(--color-accent)' : 'var(--color-border)',
                  backgroundColor: c === canon ? 'var(--color-bg-tertiary)' : 'transparent',
                  color: c === canon ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                }}
              >
                {c === 'all' ? 'All canons' : c === 'tanakh' ? 'Tanakh only' : 'NT only'}
              </button>
            ))}
          </div>
        )}

        {isLoading && (
          <div style={{ color: 'var(--color-text-secondary)' }}>Searching…</div>
        )}
        {isError && (
          <div style={{ color: 'var(--color-text-secondary)' }}>
            {error instanceof Error ? error.message : 'Search failed.'}
          </div>
        )}

        {data && (
          <div className="border-t pt-3 space-y-0.5" style={{ borderColor: 'var(--color-border)' }}>
            {data.results.length === 0 ? (
              <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                No occurrences found
                {canon !== 'all' ? ` in the ${canon === 'tanakh' ? 'Tanakh' : 'NT'}` : ''}.
              </div>
            ) : (
              data.results.map((r) => (
                <ResultRow
                  key={r.verse_id}
                  result={r}
                  onClick={() => handleResultClick(r.verse_id)}
                />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
