import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeMouseHandler,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from '@dagrejs/dagre';

import PersonNode from './PersonNode';
import type { TreeResponse } from '../../types';

interface GenealogyTreeProps {
  treeData: TreeResponse | undefined;
  isLoading: boolean;
  onNodeClick?: (personId: string) => void;
  selectedNodeId?: string | null;
}

const nodeTypes = { person: PersonNode };

const NODE_WIDTH = 160;
const NODE_HEIGHT = 100;

function applyDagreLayout(treeData: TreeResponse) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 100 });

  for (const node of treeData.nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of treeData.edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  const nodes: Node[] = treeData.nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      id: n.id,
      type: 'person',
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
      data: n.data,
    };
  });

  const edges: Edge[] = treeData.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    style: { stroke: 'var(--color-border)', strokeWidth: 1.5 },
    animated: false,
  }));

  return { nodes, edges };
}

export default function GenealogyTree({
  treeData,
  isLoading,
  onNodeClick,
  selectedNodeId,
}: GenealogyTreeProps) {
  const { layoutNodes, layoutEdges } = useMemo(() => {
    if (!treeData || treeData.nodes.length === 0) {
      return { layoutNodes: [], layoutEdges: [] };
    }
    const { nodes, edges } = applyDagreLayout(treeData);
    return { layoutNodes: nodes, layoutEdges: edges };
  }, [treeData]);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    // Apply selection styling
    const withSelection = layoutNodes.map((n) => ({
      ...n,
      selected: n.id === selectedNodeId,
    }));
    setNodes(withSelection);
    setEdges(layoutEdges);
  }, [layoutNodes, layoutEdges, selectedNodeId, setNodes, setEdges]);

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick],
  );

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-text-secondary">Loading genealogy...</div>
      </div>
    );
  }

  if (!treeData || treeData.nodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-text-secondary">No data</div>
      </div>
    );
  }

  return (
    <div className="flex-1">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} color="var(--color-border)" gap={20} size={1} />
        <Controls
          showInteractive={false}
          style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border)' }}
        />
        <MiniMap
          style={{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
          nodeColor={(n) => {
            const sex = (n.data as Record<string, unknown>)?.sex;
            return sex === 'male' ? 'var(--color-male)' : 'var(--color-female)';
          }}
          maskColor="rgba(0,0,0,0.4)"
        />
      </ReactFlow>
    </div>
  );
}
