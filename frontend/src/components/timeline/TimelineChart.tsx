import { useState, useMemo, useRef, useCallback } from 'react';
import type { ChronologyResponse, ChronologyPerson } from '../../types';

interface TimelineChartProps {
  data: ChronologyResponse;
  selectedPersonId: string | null;
  onPersonSelect: (id: string) => void;
}

const ROW_HEIGHT = 32;
const ROW_GAP = 4;
const ROW_TOTAL = ROW_HEIGHT + ROW_GAP;
const BAR_HEIGHT = 26;
const AXIS_HEIGHT = 40;
const LEFT_MARGIN = 120;
const RIGHT_MARGIN = 40;
const FLOOD_YEAR = 1656;

interface Tooltip {
  person: ChronologyPerson;
  x: number;
  y: number;
}

export default function TimelineChart({ data, selectedPersonId, onPersonSelect }: TimelineChartProps) {
  const [scale, setScale] = useState(1);
  const [tooltip, setTooltip] = useState<Tooltip | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const { min: yearMin, max: yearMax } = data.year_range;
  const yearSpan = yearMax - yearMin;

  // Base width: fit the year range into a reasonable default
  const baseWidth = 1200;
  const chartWidth = baseWidth * scale;
  const pxPerYear = chartWidth / yearSpan;

  const svgWidth = LEFT_MARGIN + chartWidth + RIGHT_MARGIN;
  const svgHeight = AXIS_HEIGHT + data.persons.length * ROW_TOTAL + 20;

  const yearToX = useCallback((year: number) => {
    return LEFT_MARGIN + (year - yearMin) * pxPerYear;
  }, [yearMin, pxPerYear]);

  // Axis ticks
  const ticks = useMemo(() => {
    const step = scale >= 2 ? 100 : 200;
    const result: number[] = [];
    const start = Math.ceil(yearMin / step) * step;
    for (let y = start; y <= yearMax; y += step) {
      result.push(y);
    }
    return result;
  }, [yearMin, yearMax, scale]);

  // Gridlines every 100 years
  const gridlines = useMemo(() => {
    const result: number[] = [];
    const start = Math.ceil(yearMin / 100) * 100;
    for (let y = start; y <= yearMax; y += 100) {
      result.push(y);
    }
    return result;
  }, [yearMin, yearMax]);

  const handleBarMouseEnter = useCallback((person: ChronologyPerson, event: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTooltip({
      person,
      x: event.clientX - rect.left,
      y: event.clientY - rect.top - 10,
    });
  }, []);

  const handleBarMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Zoom controls */}
      <div className="flex items-center gap-2 px-4 py-2 flex-shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <span className="text-xs text-text-secondary">Zoom:</span>
        <button
          onClick={() => setScale(s => Math.max(0.5, s / 1.5))}
          className="w-6 h-6 text-sm rounded border cursor-pointer flex items-center justify-center"
          style={{
            borderColor: 'var(--color-border)',
            backgroundColor: 'var(--color-bg-secondary)',
            color: 'var(--color-text-secondary)',
          }}
        >
          -
        </button>
        <span className="text-xs text-text-secondary w-10 text-center">{Math.round(scale * 100)}%</span>
        <button
          onClick={() => setScale(s => Math.min(5, s * 1.5))}
          className="w-6 h-6 text-sm rounded border cursor-pointer flex items-center justify-center"
          style={{
            borderColor: 'var(--color-border)',
            backgroundColor: 'var(--color-bg-secondary)',
            color: 'var(--color-text-secondary)',
          }}
        >
          +
        </button>
        <button
          onClick={() => setScale(1)}
          className="text-xs px-2 py-0.5 rounded border cursor-pointer"
          style={{
            borderColor: 'var(--color-border)',
            backgroundColor: 'var(--color-bg-secondary)',
            color: 'var(--color-text-secondary)',
          }}
        >
          Reset
        </button>
      </div>

      {/* Chart area */}
      <div ref={containerRef} className="flex-1 overflow-auto relative">
        <svg
          width={svgWidth}
          height={svgHeight}
          style={{ minWidth: svgWidth }}
        >
          {/* Gridlines */}
          {gridlines.map(year => (
            <line
              key={`grid-${year}`}
              x1={yearToX(year)}
              y1={AXIS_HEIGHT}
              x2={yearToX(year)}
              y2={svgHeight}
              stroke="var(--color-border)"
              strokeWidth={0.5}
              opacity={0.4}
            />
          ))}

          {/* Axis */}
          <line
            x1={LEFT_MARGIN}
            y1={AXIS_HEIGHT}
            x2={LEFT_MARGIN + chartWidth}
            y2={AXIS_HEIGHT}
            stroke="var(--color-border)"
            strokeWidth={1}
          />
          {ticks.map(year => (
            <g key={`tick-${year}`}>
              <line
                x1={yearToX(year)}
                y1={AXIS_HEIGHT - 4}
                x2={yearToX(year)}
                y2={AXIS_HEIGHT}
                stroke="var(--color-text-secondary)"
                strokeWidth={1}
              />
              <text
                x={yearToX(year)}
                y={AXIS_HEIGHT - 10}
                textAnchor="middle"
                fill="var(--color-text-secondary)"
                fontSize={10}
              >
                {year}
              </text>
            </g>
          ))}

          {/* Flood marker */}
          {FLOOD_YEAR >= yearMin && FLOOD_YEAR <= yearMax && (
            <g>
              <line
                x1={yearToX(FLOOD_YEAR)}
                y1={AXIS_HEIGHT}
                x2={yearToX(FLOOD_YEAR)}
                y2={svgHeight}
                stroke="var(--color-accent)"
                strokeWidth={1.5}
                strokeDasharray="6 3"
                opacity={0.6}
              />
              <text
                x={yearToX(FLOOD_YEAR) + 4}
                y={AXIS_HEIGHT + 14}
                fill="var(--color-accent)"
                fontSize={10}
                opacity={0.8}
              >
                The Flood
              </text>
            </g>
          )}

          {/* Lifespan bars */}
          {data.persons.map((person, i) => {
            const y = AXIS_HEIGHT + i * ROW_TOTAL + ROW_GAP;
            const x = yearToX(person.birth_year_am);
            const width = yearToX(person.death_year_am) - x;
            const isSelected = person.id === selectedPersonId;
            const isMale = person.sex === 'male';

            return (
              <g
                key={person.id}
                onClick={() => onPersonSelect(person.id)}
                onMouseEnter={(e) => handleBarMouseEnter(person, e)}
                onMouseLeave={handleBarMouseLeave}
                style={{ cursor: 'pointer' }}
              >
                {/* Name label (left margin) */}
                <text
                  x={LEFT_MARGIN - 8}
                  y={y + BAR_HEIGHT / 2 + 4}
                  textAnchor="end"
                  fill={isSelected ? 'var(--color-accent)' : 'var(--color-text-secondary)'}
                  fontSize={11}
                  fontWeight={isSelected ? 600 : 400}
                >
                  {person.name_english}
                </text>

                {/* Bar */}
                <rect
                  x={x}
                  y={y}
                  width={width}
                  height={BAR_HEIGHT}
                  rx={3}
                  fill={isMale ? 'var(--color-male)' : 'var(--color-female)'}
                  opacity={isSelected ? 1 : 0.65}
                  stroke={isSelected ? 'var(--color-accent)' : 'none'}
                  strokeWidth={2}
                />

                {/* Age label inside bar (if wide enough) */}
                {width > 50 && (
                  <text
                    x={x + 8}
                    y={y + BAR_HEIGHT / 2 + 4}
                    fill="var(--color-text-primary)"
                    fontSize={10}
                    opacity={0.9}
                  >
                    {person.age_at_death != null ? `${person.age_at_death} yrs` : ''}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Tooltip */}
        {tooltip && (
          <div
            className="absolute px-3 py-2 rounded border text-xs pointer-events-none z-50"
            style={{
              left: tooltip.x + 12,
              top: tooltip.y - 40,
              backgroundColor: 'var(--color-bg-secondary)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-primary)',
              boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            }}
          >
            <div className="font-semibold">{tooltip.person.name_english}</div>
            <div className="text-text-secondary mt-0.5">
              {tooltip.person.birth_year_am} – {tooltip.person.death_year_am} AM
            </div>
            {tooltip.person.age_at_death != null && (
              <div className="text-text-secondary">
                Lived {tooltip.person.age_at_death} years
              </div>
            )}
            <div className="text-text-secondary">
              Generation {tooltip.person.generation}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
