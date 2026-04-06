import { useState, useCallback } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { ReactFlowProvider } from '@xyflow/react';

import GenealogyTree from './components/genealogy/GenealogyTree';
import PersonDetailPanel from './components/genealogy/PersonDetailPanel';
import SearchBar from './components/common/SearchBar';
import LineageFilter from './components/genealogy/LineageFilter';
import { fetchTree, fetchStats } from './api/client';
import type { TreeResponse, GraphStats } from './types';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
});

function AppContent() {
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);
  const [currentLine, setCurrentLine] = useState<string | null>(null);
  const [treeRoot, setTreeRoot] = useState('person:adam');

  const { data: treeData, isLoading: treeLoading } = useQuery<TreeResponse>({
    queryKey: ['tree', treeRoot, currentLine],
    queryFn: () => {
      if (currentLine) {
        return fetchTree(undefined, undefined, currentLine);
      }
      return fetchTree(treeRoot);
    },
  });

  const { data: stats } = useQuery<GraphStats>({
    queryKey: ['stats'],
    queryFn: fetchStats,
  });

  const handleNodeClick = useCallback((personId: string) => {
    setSelectedPersonId(personId);
  }, []);

  const handleNavigate = useCallback((personId: string) => {
    setSelectedPersonId(personId);
    // If navigating to a person, re-root the tree on them
    setTreeRoot(personId);
    setCurrentLine(null);
  }, []);

  const handleSearchSelect = useCallback((id: string) => {
    setSelectedPersonId(id);
    if (id.startsWith('person:')) {
      setTreeRoot(id);
      setCurrentLine(null);
    }
  }, []);

  const handleLineChange = useCallback((line: string | null) => {
    setCurrentLine(line);
    if (!line) {
      setTreeRoot('person:adam');
    }
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedPersonId(null);
  }, []);

  return (
    <div className="h-screen flex flex-col" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Header */}
      <header
        className="border-b px-4 py-2.5 flex items-center justify-between flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              setTreeRoot('person:adam');
              setCurrentLine(null);
              setSelectedPersonId(null);
            }}
            className="flex items-center gap-2 cursor-pointer"
          >
            <h1 className="text-xl font-semibold" style={{ color: 'var(--color-accent)' }}>
              Lamp
            </h1>
          </button>
          <LineageFilter currentLine={currentLine} onLineChange={handleLineChange} />
        </div>

        <div className="flex items-center gap-4">
          <SearchBar onSelect={handleSearchSelect} />
          {stats && (
            <div className="text-xs text-text-secondary hidden sm:block">
              {stats.persons} persons · {stats.nations} nations · {stats.edges} links
            </div>
          )}
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        <ReactFlowProvider>
          <GenealogyTree
            treeData={treeData}
            isLoading={treeLoading}
            onNodeClick={handleNodeClick}
            selectedNodeId={selectedPersonId}
          />
        </ReactFlowProvider>

        {selectedPersonId && (
          <PersonDetailPanel
            personId={selectedPersonId}
            onClose={handleCloseDetail}
            onNavigate={handleNavigate}
          />
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
