interface LineageFilterProps {
  currentLine: string | null;
  onLineChange: (line: string | null) => void;
}

const LINES = [
  { key: null, label: 'All', desc: 'From Adam' },
  { key: 'shem', label: 'Shem', desc: 'Covenant line' },
  { key: 'ham', label: 'Ham', desc: 'Canaan, Egypt, Cush' },
  { key: 'japheth', label: 'Japheth', desc: 'Indo-European' },
] as const;

export default function LineageFilter({ currentLine, onLineChange }: LineageFilterProps) {
  return (
    <div className="flex gap-1.5">
      {LINES.map((line) => {
        const active = currentLine === line.key;
        return (
          <button
            key={line.key ?? 'all'}
            onClick={() => onLineChange(line.key)}
            className="px-3 py-1 text-xs rounded border transition-colors cursor-pointer"
            style={{
              backgroundColor: active ? 'var(--color-accent-dim)' : 'var(--color-bg-secondary)',
              borderColor: active ? 'var(--color-accent)' : 'var(--color-border)',
              color: active ? 'var(--color-accent)' : 'var(--color-text-secondary)',
            }}
            title={line.desc}
          >
            {line.label}
          </button>
        );
      })}
    </div>
  );
}
