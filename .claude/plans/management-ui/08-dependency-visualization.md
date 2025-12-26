# Stage 08: Dependency Graph Visualization

## Summary
Add an interactive dependency graph visualization using React Flow. Users can see service relationships and click nodes to manage services.

## Prerequisites
- Stage 01-07 completed

## Deliverable
- Interactive dependency graph with React Flow
- Color-coded nodes by status
- Click-to-manage functionality
- Group highlighting
- Zoom and pan controls

---

## Files to Create/Modify

```
management-ui/frontend/
├── package.json                 # Add reactflow dependency
└── src/
    ├── components/
    │   └── services/
    │       ├── DependencyGraph.tsx    # NEW
    │       └── ServiceNode.tsx        # NEW: Custom node component
    └── pages/
        └── Dependencies.tsx           # NEW
```

---

## Task 1: Install React Flow

```bash
cd management-ui/frontend
npm install reactflow
```

---

## Task 2: Create Custom Service Node

**File**: `management-ui/frontend/src/components/services/ServiceNode.tsx`

```typescript
import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { ServiceStatus, HealthStatus } from '../../types/service';

interface ServiceNodeData {
  label: string;
  group: string;
  status: ServiceStatus;
  health: HealthStatus;
  profiles: string[];
  hasHealthcheck: boolean;
  composeFile: string;
  onClick?: (serviceName: string) => void;
}

const groupColors: Record<string, string> = {
  supabase: 'border-purple-500 bg-purple-50',
  core_ai: 'border-blue-500 bg-blue-50',
  workflow: 'border-orange-500 bg-orange-50',
  database: 'border-green-500 bg-green-50',
  observability: 'border-yellow-500 bg-yellow-50',
  infrastructure: 'border-gray-500 bg-gray-50',
  other: 'border-gray-400 bg-gray-50',
};

const statusIndicators: Record<ServiceStatus, string> = {
  running: 'bg-green-500',
  stopped: 'bg-gray-400',
  starting: 'bg-yellow-500 animate-pulse',
  stopping: 'bg-yellow-500',
  restarting: 'bg-blue-500 animate-pulse',
  error: 'bg-red-500',
  not_created: 'bg-gray-300',
};

const ServiceNode: React.FC<NodeProps<ServiceNodeData>> = ({ data, selected }) => {
  const groupColor = groupColors[data.group] || groupColors.other;
  const statusColor = statusIndicators[data.status] || statusIndicators.stopped;

  return (
    <div
      className={`
        px-4 py-2 rounded-lg border-2 shadow-sm min-w-[140px]
        ${groupColor}
        ${selected ? 'ring-2 ring-blue-400' : ''}
        cursor-pointer hover:shadow-md transition-shadow
      `}
      onClick={() => data.onClick?.(data.label)}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />

      <div className="flex items-center gap-2">
        <div className={`w-2.5 h-2.5 rounded-full ${statusColor}`} />
        <span className="font-medium text-sm truncate">{data.label}</span>
      </div>

      {data.profiles.length > 0 && (
        <div className="text-xs text-gray-500 mt-1">
          {data.profiles.join(', ')}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
};

export default memo(ServiceNode);
```

---

## Task 3: Create Dependency Graph Component

**File**: `management-ui/frontend/src/components/services/DependencyGraph.tsx`

```typescript
import React, { useCallback, useMemo, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import ServiceNode from './ServiceNode';
import { ServiceInfo } from '../../types/service';
import { Button } from '../common/Button';

interface DependencyGraphProps {
  graphData: {
    nodes: Array<{
      id: string;
      data: {
        label: string;
        group: string;
        profiles: string[];
        hasHealthcheck: boolean;
        composeFile: string;
      };
    }>;
    edges: Array<{
      id: string;
      source: string;
      target: string;
      data: { condition: string };
    }>;
  };
  services: ServiceInfo[];
  onServiceClick?: (serviceName: string) => void;
}

const nodeTypes = {
  serviceNode: ServiceNode,
};

// Layout algorithm: arrange by dependency depth
function calculateLayout(
  graphData: DependencyGraphProps['graphData'],
  services: ServiceInfo[]
): { nodes: Node[]; edges: Edge[] } {
  const serviceMap = new Map(services.map((s) => [s.name, s]));

  // Calculate depth for each node
  const depths: Record<string, number> = {};
  const edges = graphData.edges;

  // Initialize all nodes at depth 0
  graphData.nodes.forEach((n) => {
    depths[n.id] = 0;
  });

  // Calculate depths based on dependencies
  let changed = true;
  let iterations = 0;
  while (changed && iterations < 20) {
    changed = false;
    iterations++;
    edges.forEach((edge) => {
      const targetDepth = depths[edge.target] || 0;
      const sourceDepth = depths[edge.source] || 0;
      if (targetDepth <= sourceDepth) {
        depths[edge.target] = sourceDepth + 1;
        changed = true;
      }
    });
  }

  // Group nodes by depth
  const nodesByDepth: Record<number, string[]> = {};
  Object.entries(depths).forEach(([nodeId, depth]) => {
    if (!nodesByDepth[depth]) nodesByDepth[depth] = [];
    nodesByDepth[depth].push(nodeId);
  });

  // Position nodes
  const nodes: Node[] = graphData.nodes.map((n) => {
    const depth = depths[n.id] || 0;
    const nodesAtDepth = nodesByDepth[depth] || [];
    const indexAtDepth = nodesAtDepth.indexOf(n.id);
    const totalAtDepth = nodesAtDepth.length;

    const service = serviceMap.get(n.id);

    return {
      id: n.id,
      type: 'serviceNode',
      position: {
        x: indexAtDepth * 180 - (totalAtDepth * 180) / 2 + 400,
        y: depth * 120 + 50,
      },
      data: {
        ...n.data,
        status: service?.status || 'not_created',
        health: service?.health || 'none',
      },
    };
  });

  // Create edges with styling
  const flowEdges: Edge[] = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.data.condition === 'service_healthy' ? 'healthy' : undefined,
    animated: e.data.condition === 'service_healthy',
    style: {
      stroke: e.data.condition === 'service_healthy' ? '#22c55e' : '#9ca3af',
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: e.data.condition === 'service_healthy' ? '#22c55e' : '#9ca3af',
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

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const { nodes, edges } = calculateLayout(graphData, services);

    // Add onClick handler to node data
    return {
      nodes: nodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          onClick: onServiceClick,
        },
      })),
      edges,
    };
  }, [graphData, services, onServiceClick]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Get unique groups
  const groups = useMemo(() => {
    const groupSet = new Set(graphData.nodes.map((n) => n.data.group));
    return Array.from(groupSet);
  }, [graphData]);

  const handleGroupHighlight = (group: string | null) => {
    setHighlightedGroup(group);
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        style: {
          ...n.style,
          opacity: group === null || n.data.group === group ? 1 : 0.3,
        },
      }))
    );
  };

  const handleFitView = useCallback(() => {
    // React Flow's Controls component handles this
  }, []);

  return (
    <div className="h-[700px] border rounded-lg bg-gray-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            const status = n.data?.status;
            if (status === 'running') return '#22c55e';
            if (status === 'error') return '#ef4444';
            return '#9ca3af';
          }}
        />

        {/* Group Filter Panel */}
        <Panel position="top-right" className="bg-white p-3 rounded-lg shadow-md">
          <div className="text-sm font-medium mb-2">Filter by Group</div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={highlightedGroup === null ? 'primary' : 'secondary'}
              onClick={() => handleGroupHighlight(null)}
              className="text-xs px-2 py-1"
            >
              All
            </Button>
            {groups.map((group) => (
              <Button
                key={group}
                variant={highlightedGroup === group ? 'primary' : 'secondary'}
                onClick={() => handleGroupHighlight(group)}
                className="text-xs px-2 py-1"
              >
                {group}
              </Button>
            ))}
          </div>
        </Panel>

        {/* Legend */}
        <Panel position="bottom-right" className="bg-white p-3 rounded-lg shadow-md">
          <div className="text-sm font-medium mb-2">Legend</div>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span>Running</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gray-400" />
              <span>Stopped</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span>Error</span>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <div className="w-6 border-t-2 border-green-500" />
              <span>Healthy dep</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 border-t-2 border-gray-400" />
              <span>Started dep</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};
```

---

## Task 4: Create Dependencies Page

**File**: `management-ui/frontend/src/pages/Dependencies.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DependencyGraph } from '../components/services/DependencyGraph';
import { useServicesStore } from '../store/servicesStore';
import { servicesApi, DependencyGraph as DependencyGraphData } from '../api/services';
import { Loading } from '../components/common/Loading';
import { Card } from '../components/common/Card';

export const Dependencies: React.FC = () => {
  const navigate = useNavigate();
  const { services, fetchServices } = useServicesStore();
  const [graphData, setGraphData] = useState<DependencyGraphData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const [graph] = await Promise.all([
          servicesApi.getDependencies(),
          fetchServices(),
        ]);
        setGraphData(graph);
      } catch (e: any) {
        setError(e.message || 'Failed to load dependency graph');
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, [fetchServices]);

  const handleServiceClick = (serviceName: string) => {
    navigate(`/services?selected=${serviceName}`);
  };

  if (isLoading) {
    return <Loading message="Loading dependency graph..." />;
  }

  if (error) {
    return (
      <Card>
        <p className="text-red-600">{error}</p>
      </Card>
    );
  }

  if (!graphData) {
    return (
      <Card>
        <p>No dependency data available</p>
      </Card>
    );
  }

  const stats = {
    total: graphData.nodes.length,
    running: services.filter((s) => s.status === 'running').length,
    dependencies: graphData.edges.length,
    healthyDeps: graphData.edges.filter((e) => e.data.condition === 'service_healthy').length,
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Service Dependencies</h2>
        <p className="text-gray-600">
          Interactive visualization of service relationships
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card>
          <p className="text-gray-500 text-sm">Total Services</p>
          <p className="text-2xl font-bold">{stats.total}</p>
        </Card>
        <Card>
          <p className="text-gray-500 text-sm">Running</p>
          <p className="text-2xl font-bold text-green-600">{stats.running}</p>
        </Card>
        <Card>
          <p className="text-gray-500 text-sm">Dependencies</p>
          <p className="text-2xl font-bold">{stats.dependencies}</p>
        </Card>
        <Card>
          <p className="text-gray-500 text-sm">Health Checks</p>
          <p className="text-2xl font-bold text-blue-600">{stats.healthyDeps}</p>
        </Card>
      </div>

      {/* Graph */}
      <DependencyGraph
        graphData={graphData}
        services={services}
        onServiceClick={handleServiceClick}
      />

      {/* Help Text */}
      <div className="mt-4 text-sm text-gray-500">
        <p>
          <strong>Tip:</strong> Click on a service node to manage it. Use the filter
          buttons to highlight specific groups. Scroll to zoom, drag to pan.
        </p>
      </div>
    </div>
  );
};
```

---

## Task 5: Add to Sidebar and Routes

Update `src/components/layout/Sidebar.tsx`:
```typescript
const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/services', label: 'Services', icon: '🐳' },
  { path: '/dependencies', label: 'Dependencies', icon: '🔗' },  // NEW
  { path: '/config', label: 'Configuration', icon: '⚙️' },
  { path: '/logs', label: 'Logs', icon: '📜' },
];
```

Update `src/App.tsx`:
```typescript
import { Dependencies } from './pages/Dependencies';

// In routes:
<Route path="/dependencies" element={<Dependencies />} />
```

---

## Validation

### Test UI
1. Navigate to Dependencies page
2. See graph render with all services
3. Nodes colored by status
4. Edges show dependency direction
5. Click a node to go to services page
6. Use group filter buttons
7. Test zoom and pan
8. Check mini-map works

### Success Criteria
- [ ] Graph renders with all services
- [ ] Nodes positioned by dependency depth
- [ ] Status colors match running/stopped/error
- [ ] Edges show arrows to dependents
- [ ] Healthy dependencies are animated/green
- [ ] Group filter highlights services
- [ ] Mini-map shows overview
- [ ] Click navigates to service

---

## Next Stage
Proceed to `09-setup-wizard.md` to add first-run setup flow.
