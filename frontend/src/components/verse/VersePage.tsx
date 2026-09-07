import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { fetchVerse } from '../../api/client';
import HebrewText from '../hebrew/HebrewText';
import GreekText from '../hebrew/GreekText';
import type { VerseDetail, VerseWord, VerseMention, Translation, QuoteRef } from '../../types';

/** Which text layer to display as the primary verse text. */
type HebrewLayer = 'consonantal' | 'pointed' | 'cantillated';
type GreekLayer = 'plain' | 'accented';

function VerseHeader({
  verse,
  onPrev,
  onNext,
}: {
  verse: VerseDetail;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div
      className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
      style={{ borderColor: 'var(--color-border)' }}
    >
      <div className="flex items-center gap-3">
        {/*
          The heading is the verse's address in the KJV, the base text. It used to
          be the witness's own numbering, so this page headed itself "Genesis 32:1"
          while displaying the KJV text of Genesis 31:55. Where the two differ —
          1,967 verses — the witness numbering is shown beside it rather than
          dropped, because the Hebrew apparatus below is numbered that way.
        */}
        <h2 className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          {verse.reference}
        </h2>
        {verse.kjv_reference === null ? (
          // No KJV verse here, so the heading fell back to witness numbering.
          // Say so: Heb Psalms 13:1 is the superscription, and KJV 13:1 is the
          // NEXT verse — without this the two pages would both head "Psalms 13:1".
          <span
            className="text-xs"
            style={{ color: 'var(--color-accent)' }}
            title="The KJV has no verse at this position; the heading uses the witness's own numbering"
          >
            witness numbering — no KJV verse here
          </span>
        ) : (
          verse.witness_reference !== verse.reference && (
            <span
              className="text-xs"
              style={{ color: 'var(--color-text-secondary)' }}
              title="This verse is numbered differently in the original-language witness"
            >
              witness numbering: {verse.witness_reference}
            </span>
          )
        )}
        <span
          className="text-xs px-2 py-0.5 rounded border"
          style={{
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-secondary)',
          }}
        >
          {verse.canon.toUpperCase()} · {verse.language}
        </span>
        {verse.parashah_marker && (
          <span
            className="text-xs px-2 py-0.5 rounded border"
            style={{
              borderColor: 'var(--color-accent)',
              color: 'var(--color-accent)',
            }}
            title={verse.parashah_marker === 'pe' ? 'Open parashah (petuchah)' : 'Closed parashah (setumah)'}
          >
            parashah: {verse.parashah_marker}
          </span>
        )}
        {verse.reversed_nun && (
          <span
            className="text-xs px-2 py-0.5 rounded border"
            style={{
              borderColor: 'var(--color-accent)',
              color: 'var(--color-accent)',
            }}
            title="Reversed nun (nun hafukha) — scribal bracket marking a set-apart passage"
          >
            ׆ reversed nun
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onPrev}
          disabled={!verse.prev_id}
          className="text-xs px-3 py-1 rounded border disabled:opacity-30 disabled:cursor-not-allowed"
          style={{
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-primary)',
          }}
        >
          ← prev
        </button>
        <button
          onClick={onNext}
          disabled={!verse.next_id}
          className="text-xs px-3 py-1 rounded border disabled:opacity-30 disabled:cursor-not-allowed"
          style={{
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-primary)',
          }}
        >
          next →
        </button>
      </div>
    </div>
  );
}

function LayerToggle<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string; hint?: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex gap-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          title={opt.hint}
          className="text-xs px-3 py-1 rounded border transition-colors cursor-pointer"
          style={{
            borderColor: value === opt.value ? 'var(--color-accent)' : 'var(--color-border)',
            backgroundColor:
              value === opt.value ? 'var(--color-bg-tertiary)' : 'transparent',
            color:
              value === opt.value ? 'var(--color-accent)' : 'var(--color-text-secondary)',
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function HebrewVerseBody({ verse }: { verse: VerseDetail }) {
  const [layer, setLayer] = useState<HebrewLayer>('cantillated');
  const text =
    layer === 'consonantal'
      ? verse.text_consonantal
      : layer === 'pointed'
      ? verse.text_pointed
      : verse.text_cantillated;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--color-text-secondary)' }}>
          Hebrew text — {layer}
        </span>
        <LayerToggle<HebrewLayer>
          value={layer}
          options={[
            { value: 'consonantal', label: 'consonantal', hint: 'Pre-Masoretic stratum — letters only' },
            { value: 'pointed', label: 'pointed', hint: 'With niqqud (vowel points), 7th–10th c.' },
            { value: 'cantillated', label: 'cantillated', hint: 'Full Masoretic: niqqud + te\'amim' },
          ]}
          onChange={setLayer}
        />
      </div>
      <div
        className="rounded border p-6 text-right"
        style={{
          borderColor: 'var(--color-border)',
          backgroundColor: 'var(--color-bg-tertiary)',
        }}
      >
        <HebrewText text={text} className="text-2xl leading-loose" />
      </div>
    </div>
  );
}

function GreekVerseBody({ verse }: { verse: VerseDetail }) {
  const [layer, setLayer] = useState<GreekLayer>('accented');
  const text = layer === 'plain' ? verse.text_plain : verse.text_accented;

  // The 32 KJV-only slots (verses in the Textus Receptus but absent from the
  // SBLGNT critical text, e.g. Acts 8:37, John 5:4) carry no Greek text at all.
  // Without this branch the panel renders as a labelled empty box, which reads
  // as a loading failure rather than a deliberate textual-critical absence — and
  // the plain/accented toggle offers a choice between two empty strings.
  const hasText = text.trim().length > 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--color-text-secondary)' }}>
          {hasText ? `Greek text — ${layer}` : 'Greek text — none in SBLGNT'}
        </span>
        {hasText && (
          <LayerToggle<GreekLayer>
            value={layer}
            options={[
              { value: 'plain', label: 'plain', hint: 'Lowercase, no diacritics — uncial-manuscript-style' },
              { value: 'accented', label: 'accented', hint: 'Standard published form with accents and breathings' },
            ]}
            onChange={setLayer}
          />
        )}
      </div>
      <div
        className="rounded border p-6"
        style={{
          borderColor: 'var(--color-border)',
          backgroundColor: 'var(--color-bg-tertiary)',
        }}
      >
        {hasText ? (
          <span lang="grc" style={{ fontSize: '1.375rem', lineHeight: '2' }}>
            {text}
          </span>
        ) : (
          <span className="text-sm italic" style={{ color: 'var(--color-text-secondary)' }}>
            No original-language witness — this verse is absent from the SBLGNT critical
            text. The base text above is unaffected; only the supporting apparatus is
            missing here.
          </span>
        )}
      </div>
    </div>
  );
}

function WordCard({
  word,
  language,
  onLexemeClick,
}: {
  word: VerseWord;
  language: string;
  onLexemeClick: (params: { lemma?: string; strongs?: string }) => void;
}) {
  const isHebrew = language === 'hbo';
  const displayText = word.text_canonical;

  return (
    <div
      className="rounded border p-3"
      style={{
        borderColor: 'var(--color-border)',
        backgroundColor: 'var(--color-bg-tertiary)',
      }}
    >
      <div className="flex items-baseline justify-between mb-2">
        {isHebrew ? (
          <HebrewText text={displayText} className="text-lg" />
        ) : (
          <span lang="grc" className="text-lg">
            {displayText}
          </span>
        )}
        <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
          #{word.position}
        </span>
      </div>

      {word.lemma && (
        <div className="text-xs mb-1">
          <span style={{ color: 'var(--color-text-secondary)' }}>lemma: </span>
          <button
            onClick={() => onLexemeClick({ lemma: word.lemma })}
            className="cursor-pointer hover:underline"
            style={{ color: 'var(--color-accent)' }}
            title="See every verse where this lemma appears"
          >
            {isHebrew ? <code>{word.lemma}</code> : <span lang="grc">{word.lemma}</span>}
          </button>
          {word.strongs && (
            <>
              <span style={{ color: 'var(--color-text-secondary)' }}>{' · '}</span>
              <button
                onClick={() => onLexemeClick({ strongs: word.strongs })}
                className="cursor-pointer hover:underline"
                style={{ color: 'var(--color-accent)' }}
                title="See every verse with this Strong's number"
              >
                H{word.strongs}
              </button>
            </>
          )}
        </div>
      )}

      {word.morph_code && (
        <div className="text-xs">
          <span style={{ color: 'var(--color-text-secondary)' }}>morph: </span>
          <code>{word.morph_code}</code>
        </div>
      )}

      {(word.text_ketiv || word.text_qere) && (
        <div
          className="text-xs mt-2 pt-2 border-t"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
        >
          {word.text_ketiv !== undefined && word.text_ketiv !== '' && (
            <div>ketiv (written): <HebrewText text={word.text_ketiv} /></div>
          )}
          {word.text_qere && (
            <div>qere (read): <HebrewText text={word.text_qere} /></div>
          )}
          {word.text_consonantal === '' && (
            <div className="italic">qere velo ketiv — read but not written</div>
          )}
        </div>
      )}
    </div>
  );
}

function TranslationsSection({
  translations,
  canonicalTextIsEmpty,
}: {
  translations: Translation[];
  canonicalTextIsEmpty: boolean;
}) {
  if (translations.length === 0) return null;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <h3
          className="text-xs uppercase tracking-wide"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Base text — KJV 1769
        </h3>
        <span className="text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>
          The text this project is about — original-language witnesses below support it
        </span>
      </div>
      {canonicalTextIsEmpty && (
        <div
          className="text-xs mb-2 italic"
          style={{ color: 'var(--color-accent)' }}
        >
          Note: this verse has no surviving original-language witness in the SBLGNT
          critical text. That affects the supporting apparatus only — the base text
          below is unchanged.
        </div>
      )}
      <div className="space-y-2">
        {translations.map((t) => (
          <div
            key={t.translation}
            className="rounded border p-3"
            style={{
              borderColor: 'var(--color-border)',
              backgroundColor: 'var(--color-bg-tertiary)',
            }}
          >
            <div className="flex items-baseline justify-between mb-1">
              <span
                className="text-xs font-semibold"
                style={{ color: 'var(--color-accent)' }}
              >
                {t.translation}
              </span>
              <span className="text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>
                tier {t.source_tier}
              </span>
            </div>
            <div className="text-sm leading-relaxed" style={{ color: 'var(--color-text-primary)' }}>
              {t.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


function QuotesSection({
  cites,
  citedBy,
  onNavigate,
}: {
  cites: QuoteRef[];
  citedBy: QuoteRef[];
  onNavigate: (verseId: string) => void;
}) {
  if (cites.length === 0 && citedBy.length === 0) return null;

  const renderList = (items: QuoteRef[], emptyLabel: string) => (
    <div className="space-y-1.5">
      {items.length === 0 && (
        <span className="text-xs italic" style={{ color: 'var(--color-text-secondary)' }}>
          {emptyLabel}
        </span>
      )}
      {items.map((q) => (
        <button
          key={`${q.id}-${q.notes ?? ''}`}
          onClick={() => onNavigate(q.id)}
          title={q.notes || undefined}
          className="block w-full text-left text-xs px-2.5 py-1.5 rounded border transition-colors cursor-pointer"
          style={{
            borderColor: 'var(--color-border)',
            backgroundColor: 'var(--color-bg-tertiary)',
            color: 'var(--color-text-primary)',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)'; }}
        >
          <div className="flex items-baseline gap-2">
            <span className="font-semibold">{q.reference}</span>
            {q.canon && (
              <span className="uppercase text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>
                {q.canon}
              </span>
            )}
          </div>
          {q.notes && (
            <div
              className="mt-0.5 text-[11px] leading-snug"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              {q.notes}
            </div>
          )}
        </button>
      ))}
    </div>
  );

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <h3 className="text-xs uppercase tracking-wide" style={{ color: 'var(--color-text-secondary)' }}>
          Cross-canon quotes
        </h3>
        <span className="text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>
          Curated NT↔OT citation edges — notes capture LXX↔MT, typology, attribution
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <div
            className="text-[11px] uppercase tracking-wide mb-1.5"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Cites ({cites.length})
          </div>
          {renderList(cites, 'This verse quotes no other seeded verses.')}
        </div>
        <div>
          <div
            className="text-[11px] uppercase tracking-wide mb-1.5"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Cited by ({citedBy.length})
          </div>
          {renderList(citedBy, 'No seeded verses quote this one.')}
        </div>
      </div>
    </div>
  );
}

function MentionsSection({
  mentions,
  onNavigate,
}: {
  mentions: VerseMention[];
  onNavigate: (id: string) => void;
}) {
  if (mentions.length === 0) return null;

  return (
    <div>
      <h3 className="text-xs uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-secondary)' }}>
        Mentioned in this verse
      </h3>
      <div className="flex flex-wrap gap-1.5">
        {mentions.map((m) => (
          <button
            key={m.id}
            onClick={() => onNavigate(m.id)}
            className="text-xs px-2 py-1 rounded border transition-colors cursor-pointer"
            style={{
              borderColor: 'var(--color-border)',
              backgroundColor: 'var(--color-bg-tertiary)',
              color: 'var(--color-text-primary)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)'; }}
          >
            <span className="uppercase text-[10px] mr-1" style={{ color: 'var(--color-text-secondary)' }}>
              {m.node_type}
            </span>
            {m.name_english}
            {m.name_hebrew && (
              <>
                {' '}
                <HebrewText text={m.name_hebrew} />
              </>
            )}
            {!m.name_hebrew && m.name_greek && (
              <>
                {' '}
                <GreekText text={m.name_greek} />
              </>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function VersePage() {
  const { verseRef } = useParams<{ verseRef: string }>();
  const navigate = useNavigate();

  const { data: verse, isLoading, isError, error, refetch } = useQuery<VerseDetail>({
    queryKey: ['verse', verseRef],
    queryFn: () => fetchVerse(verseRef!),
    enabled: !!verseRef,
  });

  useEffect(() => {
    if (verse) {
      document.title = `${verse.reference} — Lamp`;
    } else {
      document.title = 'Verse — Lamp';
    }
  }, [verse]);

  const handlePrev = useCallback(() => {
    if (verse?.prev_id) {
      const bare = verse.prev_id.replace(/^verse:/, '');
      navigate(`/verse/${bare}`);
    }
  }, [verse, navigate]);

  const handleNext = useCallback(() => {
    if (verse?.next_id) {
      const bare = verse.next_id.replace(/^verse:/, '');
      navigate(`/verse/${bare}`);
    }
  }, [verse, navigate]);

  const handleMentionClick = useCallback(
    (id: string) => {
      if (id.startsWith('person:')) {
        navigate(`/person/${id.replace(/^person:/, '')}`);
      } else if (id.startsWith('place:')) {
        navigate(`/places`);
      }
      // nation: no dedicated page yet; could extend later
    },
    [navigate],
  );

  const handleQuoteNavigate = useCallback(
    (verseId: string) => {
      const bare = verseId.replace(/^verse:/, '');
      navigate(`/verse/${bare}`);
    },
    [navigate],
  );

  const handleLexemeClick = useCallback(
    ({ lemma, strongs }: { lemma?: string; strongs?: string }) => {
      const q = new URLSearchParams();
      if (lemma) q.set('lemma', lemma);
      if (strongs) q.set('strongs', strongs);
      navigate(`/lexeme?${q}`);
    },
    [navigate],
  );

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--color-text-secondary)' }}>
        Loading verse…
      </div>
    );
  }

  if (isError || !verse) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3">
        <div style={{ color: 'var(--color-text-secondary)' }}>
          {error instanceof Error ? error.message : `Verse not found: ${verseRef}`}
        </div>
        <button
          onClick={() => refetch()}
          className="text-xs px-3 py-1 rounded border"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <VerseHeader verse={verse} onPrev={handlePrev} onNext={handleNext} />

      <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">
        {/*
          Base text first. Per Locked Decision 8 (2026-09-07) the KJV 1769 is the text
          this project is about, so it leads the page; the Hebrew or Greek witness that
          supports it follows. This order was reversed until that decision — the KJV sat
          below the original-language panel, under the heading "Reference layer — never
          replaces the original text".
        */}
        <TranslationsSection
          translations={verse.translations}
          canonicalTextIsEmpty={verse.text_canonical === ''}
        />

        {verse.language === 'hbo' ? (
          <HebrewVerseBody verse={verse} />
        ) : (
          <GreekVerseBody verse={verse} />
        )}

        <div>
          <h3
            className="text-xs uppercase tracking-wide mb-3"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Words ({verse.words.length})
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
            {verse.words.map((w) => (
              <WordCard
                key={w.position}
                word={w}
                language={verse.language}
                onLexemeClick={handleLexemeClick}
              />
            ))}
          </div>
        </div>

        <MentionsSection mentions={verse.mentions} onNavigate={handleMentionClick} />

        <QuotesSection
          cites={verse.cites}
          citedBy={verse.cited_by}
          onNavigate={handleQuoteNavigate}
        />

        {/*
          The notes field carries two unrelated kinds of record, so it gets two
          headings. A note like "KJV:Gen.31.55" is a versification mapping — an
          artifact of the KJV translation layer, saying nothing about the original
          text. Everything else is textual apparatus: Masoretic Ketiv/Qere and
          accent notes on Hebrew verses, SBLGNT-vs-Byzantine notes on Greek ones.

          This was previously a single heading reading "Masoretic notes", which was
          wrong for 2,059 of the 3,152 notes in the corpus — every one of the 2,027
          KJV versification markers, and all 32 notes on Greek NT verses, where
          "Masoretic" cannot apply at all.
        */}
        {(() => {
          const versification = verse.notes.filter((n) => n.startsWith('KJV:'));
          const textual = verse.notes.filter((n) => !n.startsWith('KJV:'));
          const headingClass = 'text-xs uppercase tracking-wide mb-2';
          const secondary = { color: 'var(--color-text-secondary)' };
          return (
            <>
              {textual.length > 0 && (
                <div>
                  <h3 className={headingClass} style={secondary}>
                    {verse.canon === 'tanakh' ? 'Masoretic notes' : 'Textual notes'}
                  </h3>
                  <ul className="text-sm space-y-1" style={secondary}>
                    {textual.map((n, i) => (
                      <li key={i}>• {n}</li>
                    ))}
                  </ul>
                </div>
              )}
              {versification.length > 0 && (
                <div>
                  <h3 className={headingClass} style={secondary}>
                    KJV versification
                  </h3>
                  <ul className="text-sm space-y-1" style={secondary}>
                    {versification.map((n, i) => (
                      <li key={i}>• {n}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          );
        })()}

        <div
          className="text-xs pt-4 border-t"
          style={{ color: 'var(--color-text-secondary)', borderColor: 'var(--color-border)' }}
        >
          {/*
            source/source_tier describe the original-language witness, and are null
            for the 32 verses that have none. Rendering them anyway printed
            "source:  · tier  ·" with empty gaps.
          */}
          {verse.source ? (
            <>
              source: <code>{verse.source}</code> · tier {verse.source_tier} ·{' '}
            </>
          ) : (
            <>no original-language witness · </>
          )}
          id: <code>{verse.id}</code>
        </div>
      </div>
    </div>
  );
}
