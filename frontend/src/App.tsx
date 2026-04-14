import { useCallback, useEffect } from 'react';
import { Routes, Route, useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { ReactFlowProvider } from '@xyflow/react';

import AppLayout from './components/layout/AppLayout';
import GenealogyTree from './components/genealogy/GenealogyTree';
import PersonDetailPanel from './components/genealogy/PersonDetailPanel';
import LineageFilter from './components/genealogy/LineageFilter';
import TimelinePage from './components/timeline/TimelinePage';
import PlacesPage from './components/places/PlacesPage';
import VersePage from './components/verse/VersePage';
import ReadPage from './components/read/ReadPage';
import { fetchTree } from './api/client';
import type { TreeResponse } from './types';

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

  const handleNodeClick = useCallback((nodeId: string) => {
    const shortId = nodeId.replace(/^person:/, '');
    const params = currentLine ? `?line=${currentLine}` : '';
    navigate(`/person/${shortId}${params}`);
  }, [navigate, currentLine]);

  const handleNavigate = useCallback((nodeId: string) => {
    const shortId = nodeId.replace(/^person:/, '');
    navigate(`/person/${shortId}`);
  }, [navigate]);

  const handleLineChange = useCallback((line: string | null) => {
    if (line) {
      setSearchParams({ line });
    } else {
      setSearchParams({});
    }
    if (selectedPersonId) {
      navigate(line ? `/?line=${line}` : '/');
    }
  }, [setSearchParams, navigate, selectedPersonId]);

  const handleCloseDetail = useCallback(() => {
    const params = currentLine ? `?line=${currentLine}` : '';
    navigate(`/${params}`);
  }, [navigate, currentLine]);

  useEffect(() => {
    if (selectedPersonId && treeData) {
      const node = treeData.nodes.find(n => n.id === selectedPersonId);
      document.title = node ? `${node.data.name_english} — Lamp` : 'Lamp';
    } else {
      document.title = 'Lamp';
    }
  }, [selectedPersonId, treeData]);

  return (
    <>
      {/* Line filter floats in the tree area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-4 py-2 flex-shrink-0">
          <LineageFilter currentLine={currentLine} onLineChange={handleLineChange} />
        </div>
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
      </div>

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

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<GenealogyPage />} />
          <Route path="/person/:personId" element={<GenealogyPage />} />
          <Route path="/timeline" element={<TimelinePage />} />
          <Route path="/places" element={<PlacesPage />} />
          <Route path="/verse/:verseRef" element={<VersePage />} />
          <Route path="/read" element={<ReadPage />} />
          <Route path="/read/:book" element={<ReadPage />} />
          <Route path="/read/:book/:chapter" element={<ReadPage />} />
        </Route>
      </Routes>
    </QueryClientProvider>
  );
}
