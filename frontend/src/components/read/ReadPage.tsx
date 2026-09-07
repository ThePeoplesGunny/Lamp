import { useCallback, useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { fetchBooks, fetchChapter } from '../../api/client';
import HebrewText from '../hebrew/HebrewText';
import type { BookSummary, ChapterDetail } from '../../types';

/** Group code → display name + ordered member codes. Order matters (Torah before Nevi'im, etc.). */
const TANAKH_GROUPS: { label: string; codes: string[] }[] = [
  { label: 'Torah', codes: ['GEN', 'EXO', 'LEV', 'NUM', 'DEU'] },
  { label: "Nevi'im — Former", codes: ['JOS', 'JDG', '1SA', '2SA', '1KI', '2KI'] },
  { label: "Nevi'im — Latter", codes: ['ISA', 'JER', 'EZK'] },
  {
    label: 'The Twelve',
    codes: ['HOS', 'JOL', 'AMO', 'OBA', 'JON', 'MIC', 'NAM', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL'],
  },
  {
    label: 'Ketuvim',
    codes: ['PSA', 'PRO', 'JOB', 'SNG', 'RUT', 'LAM', 'ECC', 'EST', 'DAN', 'EZR', 'NEH', '1CH', '2CH'],
  },
];

const NT_GROUPS: { label: string; codes: string[] }[] = [
  { label: 'Gospels + Acts', codes: ['MAT', 'MRK', 'LUK', 'JHN', 'ACT'] },
  {
    label: 'Pauline',
    codes: ['ROM', '1CO', '2CO', 'GAL', 'EPH', 'PHP', 'COL', '1TH', '2TH', '1TI', '2TI', 'TIT', 'PHM'],
  },
  {
    label: 'General + Revelation',
    codes: ['HEB', 'JAS', '1PE', '2PE', '1JN', '2JN', '3JN', 'JUD', 'REV'],
  },
];

function BookGroup({
  label,
  codes,
  booksByCode,
  selectedBook,
  onSelect,
}: {
  label: string;
  codes: string[];
  booksByCode: Map<string, BookSummary>;
  selectedBook: string | null;
  onSelect: (code: string) => void;
}) {
  const present = codes.filter((c) => booksByCode.has(c));
  if (present.length === 0) return null;

  return (
    <div className="mb-3">
      <h4
        className="text-[10px] uppercase tracking-wider mb-1 px-2"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        {label}
      </h4>
      <div className="space-y-0.5">
        {present.map((code) => {
          const b = booksByCode.get(code)!;
          const isSelected = b.book === selectedBook;
          return (
            <button
              key={code}
              onClick={() => onSelect(code)}
              className="w-full text-left text-sm px-2 py-1 rounded transition-colors cursor-pointer"
              style={{
                backgroundColor: isSelected ? 'var(--color-bg-tertiary)' : 'transparent',
                color: isSelected ? 'var(--color-accent)' : 'var(--color-text-primary)',
                borderLeft: isSelected ? '2px solid var(--color-accent)' : '2px solid transparent',
              }}
              onMouseEnter={(e) => {
                if (!isSelected) e.currentTarget.style.backgroundColor = 'var(--color-bg-tertiary)';
              }}
              onMouseLeave={(e) => {
                if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <span className="inline-block w-10 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                {code}
              </span>
              <span>{b.name}</span>
              <span className="text-xs ml-2" style={{ color: 'var(--color-text-secondary)' }}>
                {b.chapter_count}ch
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function BookList({
  books,
  selectedBook,
  onSelect,
}: {
  books: BookSummary[];
  selectedBook: string | null;
  onSelect: (code: string) => void;
}) {
  const byCode = useMemo(() => {
    const m = new Map<string, BookSummary>();
    books.forEach((b) => m.set(b.book, b));
    return m;
  }, [books]);

  return (
    <div
      className="w-72 border-r overflow-y-auto flex-shrink-0 py-3"
      style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }}
    >
      <div className="px-2 pb-3 border-b mb-2" style={{ borderColor: 'var(--color-border)' }}>
        <h3 className="text-xs uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-secondary)' }}>
          Tanakh (Hebrew OT)
        </h3>
        {TANAKH_GROUPS.map((g) => (
          <BookGroup
            key={g.label}
            label={g.label}
            codes={g.codes}
            booksByCode={byCode}
            selectedBook={selectedBook}
            onSelect={onSelect}
          />
        ))}
      </div>
      <div className="px-2">
        <h3 className="text-xs uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-secondary)' }}>
          New Testament (Greek)
        </h3>
        {NT_GROUPS.map((g) => (
          <BookGroup
            key={g.label}
            label={g.label}
            codes={g.codes}
            booksByCode={byCode}
            selectedBook={selectedBook}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}

function ChapterPicker({
  chapterCount,
  selectedChapter,
  onSelect,
}: {
  chapterCount: number;
  selectedChapter: number;
  onSelect: (n: number) => void;
}) {
  const chapters = Array.from({ length: chapterCount }, (_, i) => i + 1);
  return (
    <div className="flex flex-wrap gap-1">
      {chapters.map((n) => {
        const isSelected = n === selectedChapter;
        return (
          <button
            key={n}
            onClick={() => onSelect(n)}
            className="w-9 h-9 text-sm rounded border transition-colors cursor-pointer"
            style={{
              borderColor: isSelected ? 'var(--color-accent)' : 'var(--color-border)',
              backgroundColor: isSelected ? 'var(--color-bg-tertiary)' : 'transparent',
              color: isSelected ? 'var(--color-accent)' : 'var(--color-text-primary)',
            }}
          >
            {n}
          </button>
        );
      })}
    </div>
  );
}

function ChapterVerseList({
  chapter,
  language,
  onVerseClick,
}: {
  chapter: ChapterDetail;
  language: 'hbo' | 'grc' | 'arc';
  onVerseClick: (verseId: string) => void;
}) {
  const isHebrew = language === 'hbo';
  return (
    <div className="space-y-1">
      {chapter.verses.map((v) => (
        <button
          key={v.id}
          onClick={() => onVerseClick(v.id)}
          className="w-full text-left px-3 py-2 rounded transition-colors cursor-pointer border"
          style={{
            borderColor: 'transparent',
            backgroundColor: 'transparent',
          }}
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
              className="text-xs flex-shrink-0 w-10 text-right"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              {v.verse}
            </span>
            {/*
              This reader shows the original-language witness, and 32 NT verses
              have none (present in the KJV, absent from the SBLGNT). They used to
              render as a bare verse number followed by nothing, which reads as a
              rendering bug rather than a textual-critical absence. Open the verse
              to see its KJV base text.
            */}
            {v.text_canonical === '' ? (
              <span
                className="text-sm italic leading-relaxed"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                no original-language witness — open for the KJV base text
              </span>
            ) : isHebrew ? (
              <HebrewText text={v.text_canonical} className="text-lg leading-relaxed" />
            ) : (
              <span lang="grc" className="text-lg leading-relaxed">
                {v.text_canonical}
              </span>
            )}
            {v.parashah_marker && (
              <span
                className="text-[10px] ml-auto flex-shrink-0"
                style={{ color: 'var(--color-accent)' }}
                title={v.parashah_marker === 'pe' ? 'Open parashah' : 'Closed parashah'}
              >
                ¶ {v.parashah_marker}
              </span>
            )}
            {v.reversed_nun && (
              <span className="text-[10px] flex-shrink-0" style={{ color: 'var(--color-accent)' }} title="Reversed nun">
                ׆
              </span>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}

export default function ReadPage() {
  const { book, chapter } = useParams<{ book?: string; chapter?: string }>();
  const navigate = useNavigate();

  const selectedBook = book ? book.toUpperCase() : null;
  const selectedChapter = chapter ? parseInt(chapter, 10) : 1;

  const { data: books, isLoading: booksLoading, isError: booksError } = useQuery<BookSummary[]>({
    queryKey: ['books'],
    queryFn: fetchBooks,
  });

  const selectedBookSummary = useMemo(
    () => books?.find((b) => b.book === selectedBook) ?? null,
    [books, selectedBook],
  );

  const { data: chapterData, isLoading: chapterLoading, isError: chapterError } = useQuery<ChapterDetail>({
    queryKey: ['chapter', selectedBook, selectedChapter],
    queryFn: () => fetchChapter(selectedBook!, selectedChapter),
    enabled: !!selectedBook && !!selectedBookSummary,
  });

  useEffect(() => {
    if (selectedBookSummary) {
      document.title = `${selectedBookSummary.name} ${selectedChapter} — Lamp`;
    } else {
      document.title = 'Read — Lamp';
    }
  }, [selectedBookSummary, selectedChapter]);

  const handleBookSelect = useCallback(
    (code: string) => {
      navigate(`/read/${code}/1`);
    },
    [navigate],
  );

  const handleChapterSelect = useCallback(
    (n: number) => {
      if (selectedBook) navigate(`/read/${selectedBook}/${n}`);
    },
    [navigate, selectedBook],
  );

  const handleVerseClick = useCallback(
    (verseId: string) => {
      const bare = verseId.replace(/^verse:/, '');
      navigate(`/verse/${bare}`);
    },
    [navigate],
  );

  if (booksLoading) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--color-text-secondary)' }}>
        Loading books…
      </div>
    );
  }
  if (booksError || !books) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--color-text-secondary)' }}>
        Failed to load book list.
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      <BookList books={books} selectedBook={selectedBook} onSelect={handleBookSelect} />

      <div className="flex-1 overflow-y-auto">
        {!selectedBookSummary ? (
          <div
            className="h-full flex items-center justify-center text-center px-6"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <div>
              <div className="text-lg mb-1">Select a book to begin</div>
              <div className="text-sm">
                {books.length} books ingested · {books.reduce((a, b) => a + b.verse_count, 0).toLocaleString()} verses
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto px-6 py-5 space-y-5">
            <div className="flex items-baseline justify-between">
              <h2 className="text-2xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                {selectedBookSummary.name}{' '}
                <span style={{ color: 'var(--color-text-secondary)' }}>
                  {selectedChapter}
                </span>
              </h2>
              <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                {selectedBookSummary.canon.toUpperCase()} · {selectedBookSummary.language} ·{' '}
                {selectedBookSummary.chapter_count} ch · {selectedBookSummary.verse_count} verses
              </span>
            </div>

            <ChapterPicker
              chapterCount={selectedBookSummary.chapter_count}
              selectedChapter={selectedChapter}
              onSelect={handleChapterSelect}
            />

            <div className="border-t pt-4" style={{ borderColor: 'var(--color-border)' }}>
              {chapterLoading && (
                <div style={{ color: 'var(--color-text-secondary)' }}>Loading chapter…</div>
              )}
              {chapterError && (
                <div style={{ color: 'var(--color-text-secondary)' }}>Chapter not found.</div>
              )}
              {chapterData && (
                <ChapterVerseList
                  chapter={chapterData}
                  language={selectedBookSummary.language}
                  onVerseClick={handleVerseClick}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
