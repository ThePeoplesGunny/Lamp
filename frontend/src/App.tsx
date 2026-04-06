import { useCallback, useEffect } from 'react';
import { Routes, Route, useParams, useNavigate, useSearchParams } from 'react-router-dom';
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

function GenealogyPage() {
  const { personId } = useParams<{ personId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const selectedPersonId = personId ? `person:${personId}` : null;
  const currentLine = searchParams.get('line');

  // Derive tree root: if a line filter is active, the line endpoint handles rooting.
  // Otherwise root on the selected person, or adam by default.
  const treeRoot = selectedPersonId ?? 'person:adam';

  const { data: treeData, isLoading: treeLoading, isError: treeError, refetch: retryTree } = useQuery<TreeResponse>({
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

  const handleNodeClick = useCallback((nodeId: string) => {
    const shortId = nodeId.replace(/^person:/, '');
    const params = currentLine ? `?line=${currentLine}` : '';
    navigate(`/person/${shortId}${params}`);
  }, [navigate, currentLine]);

  const handleNavigate = useCallback((nodeId: string) => {
    const shortId = nodeId.replace(/^person:/, '');
    // Navigating to a person clears the line filter — we're re-rooting on them
    navigate(`/person/${shortId}`);
  }, [navigate]);

  const handleSearchSelect = useCallback((id: string) => {
    if (id.startsWith('person:')) {
      const shortId = id.replace(/^person:/, '');
      navigate(`/person/${shortId}`);
    }
  }, [navigate]);

  const handleLineChange = useCallback((line: string | null) => {
    if (line) {
      setSearchParams({ line });
    } else {
      setSearchParams({});
    }
    // When changing line filter, go back to root view
    if (selectedPersonId) {
      navigate(line ? `/?line=${line}` : '/');
    }
  }, [setSearchParams, navigate, selectedPersonId]);

  const handleCloseDetail = useCallback(() => {
    const params = currentLine ? `?line=${currentLine}` : '';
    navigate(`/${params}`);
  }, [navigate, currentLine]);

  const handleHomeClick = useCallback(() => {
    navigate('/');
  }, [navigate]);

  // Sync document title
  useEffect(() => {
    if (selectedPersonId && treeData) {
      const node = treeData.nodes.find(n => n.id === selectedPersonId);
      document.title = node ? `${node.data.name_english} — Lamp` : 'Lamp';
    } else {
      document.title = 'Lamp';
    }
  }, [selectedPersonId, treeData]);

  return (
    <div className="h-screen flex flex-col" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Header */}
      <header
        className="border-b px-4 py-2.5 flex items-center justify-between flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <div className="flex items-center gap-4">
          <button
            onClick={handleHomeClick}
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
            isError={treeError}
            onRetry={() => retryTree()}
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
      <Routes>
        <Route path="/" element={<GenealogyPage />} />
        <Route path="/person/:personId" element={<GenealogyPage />} />
      </Routes>
    </QueryClientProvider>
  );
}
