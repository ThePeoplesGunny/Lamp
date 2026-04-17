import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchNodes } from '../../api/client';
import type { SearchResult } from '../../types';

interface SearchBarProps {
  onSelect: (id: string) => void;
}

export default function SearchBar({ onSelect }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const { data: results } = useQuery<SearchResult[]>({
    queryKey: ['search', query],
    queryFn: () => searchNodes(query),
    enabled: query.length >= 2,
    placeholderData: (prev) => prev,
  });

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as HTMLElement)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={wrapperRef} className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setIsOpen(true);
        }}
        onFocus={() => query.length >= 2 && setIsOpen(true)}
        placeholder="Search name, Hebrew, or Strong's..."
        className="w-64 px-3 py-1.5 text-sm rounded border outline-none"
        style={{
          backgroundColor: 'var(--color-bg-secondary)',
          borderColor: 'var(--color-border)',
          color: 'var(--color-text-primary)',
        }}
      />
      {isOpen && results && results.length > 0 && (
        <div
          className="absolute top-full left-0 mt-1 w-80 rounded border shadow-lg z-50 max-h-64 overflow-y-auto"
          style={{
            backgroundColor: 'var(--color-bg-secondary)',
            borderColor: 'var(--color-border)',
          }}
        >
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => {
                onSelect(r.id);
                setIsOpen(false);
                setQuery('');
              }}
              className="w-full text-left px-3 py-2 text-sm transition-colors cursor-pointer flex items-center justify-between"
              style={{ color: 'var(--color-text-primary)' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-tertiary)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <div>
                <span className="font-medium">{r.name_english}</span>
                {r.name_hebrew && (
                  <span className="ml-2 text-text-secondary" dir="rtl" lang="he" style={{ fontFamily: 'var(--font-hebrew)' }}>
                    {r.name_hebrew}
                  </span>
                )}
                {!r.name_hebrew && r.name_greek && (
                  <span className="ml-2 text-text-secondary" lang="grc">
                    {r.name_greek}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {r.strongs && <span className="text-xs text-accent">{r.strongs}</span>}
                <span className="text-xs text-text-secondary">{r.node_type}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
