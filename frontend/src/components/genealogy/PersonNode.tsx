import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import HebrewText from '../hebrew/HebrewText';

export interface PersonNodeData {
  name_english: string;
  name_hebrew?: string;
  meaning?: string;
  strongs?: string;
  sex?: string;
  birth_year_am?: number;
  death_year_am?: number;
  age_at_death?: number;
  [key: string]: unknown;
}

function PersonNode({ data, selected }: NodeProps) {
  const d = data as unknown as PersonNodeData;
  const isMale = d.sex === 'male';
  const borderColor = isMale ? 'var(--color-male)' : 'var(--color-female)';
  const lifespan =
    d.birth_year_am && d.death_year_am
      ? `${d.birth_year_am}–${d.death_year_am} AM`
      : d.birth_year_am
        ? `b. ${d.birth_year_am} AM`
        : null;

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-border !w-2 !h-2" />
      <div
        className="px-3 py-2 rounded-lg min-w-[140px] text-center transition-shadow"
        style={{
          backgroundColor: 'var(--color-bg-secondary)',
          border: `2px solid ${selected ? 'var(--color-accent)' : borderColor}`,
          boxShadow: selected ? '0 0 12px var(--color-accent-dim)' : 'none',
        }}
      >
        <div className="text-sm font-semibold text-text-primary">{d.name_english}</div>
        {d.name_hebrew && (
          <div className="text-base mt-0.5">
            <HebrewText text={d.name_hebrew} className="text-text-primary" />
          </div>
        )}
        {d.meaning && (
          <div className="text-xs text-text-secondary mt-0.5 italic">
            "{d.meaning}"
          </div>
        )}
        {lifespan && (
          <div className="text-xs text-text-secondary mt-1">{lifespan}</div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-border !w-2 !h-2" />
    </>
  );
}

export default memo(PersonNode);
