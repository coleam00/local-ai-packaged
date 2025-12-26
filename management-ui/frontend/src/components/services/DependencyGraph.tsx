import { useMemo, useState, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
  BackgroundVariant,
} from 'reactflow';
import type { Node, Edge } from 'reactflow';
import 'reactflow/dist/style.css';
import ServiceNode from './ServiceNode';
import type { ServiceInfo } from '../../types/service';
import { Button } from '../common/Button';

interface ApiGraphNode {
  id: string;
  data: Record<string, unknown>;
}

interface ApiGraphEdge {
  id: string;
  source: string;
  target: string;
  data: Record<string, unknown>;
}

interface DependencyGraphProps {
  graphData: {
    nodes: ApiGraphNode[];
    edges: ApiGraphEdge[];
  };
  services: ServiceInfo[];
  onServiceClick?: (serviceName: string) => void;
}

// Convert API data to typed data
function parseNodeData(data: Record<string, unknown>) {
  return {
    label: (data.label as string) || '',
    group: (data.group as string) || 'other',
    profiles: (data.profiles as string[]) || [],
    hasHealthcheck: (data.hasHealthcheck as boolean) || false,
    composeFile: (data.composeFile as string) || '',
  };
}

function parseEdgeData(data: Record<string, unknown>) {
  return {
    condition: (data.condition as string) || 'service_started',
  };
}

const nodeTypes = {
  serviceNode: ServiceNode,
};

// Layout algorithm: arrange by dependency depth
function calculateLayout(
  graphData: DependencyGraphProps['graphData'],
  services: ServiceInfo[],
  onServiceClick?: (serviceName: string) => void
): { nodes: Node[]; edges: Edge[] } {
  const serviceMap = new Map(services.map((s) => [s.name, s]));

  // Parse node data
  const parsedNodes = graphData.nodes.map((n) => ({
    id: n.id,
    data: parseNodeData(n.data),
  }));

  // Parse edge data
  const parsedEdges = graphData.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    data: parseEdgeData(e.data),
  }));

  // Calculate depth for each node (nodes with no dependencies are at depth 0)
  const depths: Record<string, number> = {};

  // Initialize all nodes at depth 0
  parsedNodes.forEach((n) => {
    depths[n.id] = 0;
  });

  // Calculate depths based on dependencies
  // A node's depth = max(depth of all sources) + 1
  let changed = true;
  let iterations = 0;
  while (changed && iterations < 20) {
    changed = false;
    iterations++;
    parsedEdges.forEach((edge) => {
      // edge.source depends on edge.target
      // So target should be above source (lower depth)
      const sourceDepth = depths[edge.source] || 0;
      const targetDepth = depths[edge.target] || 0;
      if (sourceDepth <= targetDepth) {
        depths[edge.source] = targetDepth + 1;
        changed = true;
      }
    });
  }

  // Invert depths so dependencies are at top
  const maxDepth = Math.max(...Object.values(depths), 0);
  Object.keys(depths).forEach((key) => {
    depths[key] = maxDepth - depths[key];
  });

  // Group nodes by depth
  const nodesByDepth: Record<number, string[]> = {};
  Object.entries(depths).forEach(([nodeId, depth]) => {
    if (!nodesByDepth[depth]) nodesByDepth[depth] = [];
    nodesByDepth[depth].push(nodeId);
  });

  // Sort nodes within each depth by group for better visual grouping
  Object.values(nodesByDepth).forEach((nodes) => {
    nodes.sort((a, b) => {
      const nodeA = parsedNodes.find((n) => n.id === a);
      const nodeB = parsedNodes.find((n) => n.id === b);
      return (nodeA?.data.group || '').localeCompare(nodeB?.data.group || '');
    });
  });

  // Position nodes
  const nodes: Node[] = parsedNodes.map((n) => {
    const depth = depths[n.id] || 0;
    const nodesAtDepth = nodesByDepth[depth] || [];
    const indexAtDepth = nodesAtDepth.indexOf(n.id);
    const totalAtDepth = nodesAtDepth.length;

    const service = serviceMap.get(n.id);

    return {
      id: n.id,
      type: 'serviceNode',
      position: {
        x: indexAtDepth * 220 - (totalAtDepth * 220) / 2 + 500,
        y: depth * 140 + 50,
      },
      data: {
        ...n.data,
        status: service?.status || 'not_created',
        health: service?.health || 'none',
        onClick: onServiceClick,
      },
    };
  });

  // Create edges with styling
  const flowEdges: Edge[] = parsedEdges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.data.condition === 'service_healthy' ? 'healthy' : undefined,
    labelStyle: { fill: '#9ca3af', fontSize: 10 },
    labelBgStyle: { fill: '#1f2937', fillOpacity: 0.8 },
    animated: e.data.condition === 'service_healthy',
    style: {
      stroke: e.data.condition === 'service_healthy' ? '#22c55e' : '#6b7280',
      strokeWidth: 2,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: e.data.condition === 'service_healthy' ? '#22c55e' : '#6b7280',
      width: 20,
      height: 20,
    },
  }));

  return { nodes, edges: flowEdges };
}

export const DependencyGraph: React.FC<DependencyGraphProps> = ({
  graphData,
  services,
  onServiceClick,
}) => {
  const [highlightedGroup, setHighlightedGroup] = useState<string | null>(null);

  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => calculateLayout(graphData, services, onServiceClick),
    [graphData, services, onServiceClick]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  // Get unique groups
  const groups = useMemo(() => {
    const groupSet = new Set(graphData.nodes.map((n) => parseNodeData(n.data).group));
    return Array.from(groupSet).sort();
  }, [graphData]);

  const handleGroupHighlight = useCallback((group: string | null) => {
    setHighlightedGroup(group);
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        style: {
          ...n.style,
          opacity: group === null || n.data.group === group ? 1 : 0.25,
          transition: 'opacity 0.2s',
        },
      }))
    );
  }, [setNodes]);

  return (
    <div className="h-[600px] border border-gray-700 rounded-lg bg-gray-900 overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#374151"
        />
        <Controls
          className="!bg-gray-800 !border-gray-700 !rounded-lg !shadow-lg"
          showInteractive={false}
        />
        <MiniMap
          className="!bg-gray-800 !border-gray-700 !rounded-lg"
          nodeColor={(n) => {
            const status = n.data?.status;
            if (status === 'running') return '#22c55e';
            if (status === 'error') return '#ef4444';
            if (status === 'starting' || status === 'stopping') return '#eab308';
            return '#6b7280';
          }}
          maskColor="rgba(0, 0, 0, 0.7)"
        />

        {/* Group Filter Panel */}
        <Panel position="top-right" className="bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-700">
          <div className="text-sm font-medium text-gray-300 mb-2">Filter by Group</div>
          <div className="flex flex-wrap gap-2 max-w-xs">
            <Button
              size="sm"
              variant={highlightedGroup === null ? 'primary' : 'ghost'}
              onClick={() => handleGroupHighlight(null)}
            >
              All
            </Button>
            {groups.map((group) => (
              <Button
                key={group}
                size="sm"
                variant={highlightedGroup === group ? 'primary' : 'ghost'}
                onClick={() => handleGroupHighlight(group)}
              >
                {group}
              </Button>
            ))}
          </div>
        </Panel>

        {/* Legend */}
        <Panel position="bottom-right" className="bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-700">
          <div className="text-sm font-medium text-gray-300 mb-2">Legend</div>
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-gray-300">Running</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gray-500" />
              <span className="text-gray-300">Stopped</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <span className="text-gray-300">Starting/Stopping</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-gray-300">Error</span>
            </div>
            <div className="border-t border-gray-700 my-2" />
            <div className="flex items-center gap-2">
              <div className="w-6 h-0.5 bg-green-500" />
              <span className="text-gray-300">Health dependency</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-0.5 bg-gray-500" />
              <span className="text-gray-300">Start dependency</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};
