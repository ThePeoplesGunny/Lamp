import { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';

import TimelineChart from './TimelineChart';
import PersonDetailPanel from '../genealogy/PersonDetailPanel';
import { fetchChronology } from '../../api/client';
import type { ChronologyResponse } from '../../types';

export default function TimelinePage() {
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery<ChronologyResponse>({
    queryKey: ['chronology'],
    queryFn: fetchChronology,
  });

  const handlePersonSelect = useCallback((id: string) => {
    setSelectedPersonId(prev => prev === id ? null : id);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedPersonId(null);
  }, []);

  const handleNavigate = useCallback((id: string) => {
    setSelectedPersonId(id);
  }, []);

  useEffect(() => {
    document.title = selectedPersonId
      ? `Timeline — Lamp`
      : 'Timeline — Lamp';
  }, [selectedPersonId]);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-text-secondary">Loading chronology...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-text-secondary mb-2">Failed to load chronology data</div>
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
      </div>
    );
  }

  if (!data || data.persons.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-text-secondary">No chronology data available</div>
      </div>
    );
  }

  return (
    <>
      <TimelineChart
        data={data}
        selectedPersonId={selectedPersonId}
        onPersonSelect={handlePersonSelect}
      />

      {selectedPersonId && (
        <PersonDetailPanel
          personId={selectedPersonId}
          onClose={handleCloseDetail}
          onNavigate={handleNavigate}
        />
      )}
    </>
  );
}
