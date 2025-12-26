# Stage 05: Dashboard & Service Control UI

## Summary
Build the main service management interface with live status, start/stop/restart controls, and group management. After this stage, users can manage services through the UI.

## Prerequisites
- Stage 01-04 completed

## Deliverable
- Dashboard with service statistics
- Service list with status indicators
- Start/stop/restart buttons
- Service group cards
- Real-time status updates (polling)

---

## Files to Create/Modify

```
management-ui/frontend/src/
├── api/
│   └── services.ts              # NEW
├── store/
│   └── servicesStore.ts         # NEW
├── components/
│   └── services/
│       ├── ServiceCard.tsx      # NEW
│       ├── ServiceList.tsx      # NEW
│       ├── ServiceGroup.tsx     # NEW
│       ├── StatusBadge.tsx      # NEW
│       └── ServiceActions.tsx   # NEW
├── pages/
│   ├── Dashboard.tsx            # UPDATE
│   └── Services.tsx             # NEW
└── types/
    └── service.ts               # NEW
```

---

## Task 1: Create Service Types

**File**: `management-ui/frontend/src/types/service.ts`

```typescript
export type ServiceStatus = 'running' | 'stopped' | 'starting' | 'stopping' | 'restarting' | 'error' | 'not_created';
export type HealthStatus = 'healthy' | 'unhealthy' | 'starting' | 'none' | 'unknown';

export interface ServiceInfo {
  name: string;
  status: ServiceStatus;
  health: HealthStatus;
  image: string | null;
  container_id: string | null;
  ports: string[];
  group: string;
  compose_file: string;
  profiles: string[];
  has_healthcheck: boolean;
  depends_on: Record<string, string>;
}

export interface ServiceDetail extends ServiceInfo {
  environment: Record<string, string>;
  created: string | null;
  dependents: string[];
  dependencies: string[];
}

export interface ServiceGroup {
  id: string;
  name: string;
  description: string;
  services: string[];
  running_count: number;
  total_count: number;
}

export interface ServiceActionRequest {
  profile?: string;
  environment?: string;
  force?: boolean;
}

export interface ServiceActionResponse {
  success: boolean;
  message: string;
  service: string;
  action: string;
  output?: string;
  error?: string;
}
```

---

## Task 2: Create Services API

**File**: `management-ui/frontend/src/api/services.ts`

```typescript
import { apiClient } from './client';
import { ServiceInfo, ServiceDetail, ServiceGroup, ServiceActionRequest, ServiceActionResponse } from '../types/service';

export interface ServiceListResponse {
  services: ServiceInfo[];
  total: number;
}

export interface ServiceGroupsResponse {
  groups: ServiceGroup[];
}

export interface DependencyGraph {
  nodes: Array<{ id: string; data: Record<string, any> }>;
  edges: Array<{ id: string; source: string; target: string; data: Record<string, any> }>;
}

export const servicesApi = {
  async list(): Promise<ServiceListResponse> {
    const response = await apiClient.get<ServiceListResponse>('/services');
    return response.data;
  },

  async get(name: string): Promise<ServiceDetail> {
    const response = await apiClient.get<ServiceDetail>(`/services/${name}`);
    return response.data;
  },

  async getGroups(): Promise<ServiceGroupsResponse> {
    const response = await apiClient.get<ServiceGroupsResponse>('/services/groups');
    return response.data;
  },

  async getDependencies(): Promise<DependencyGraph> {
    const response = await apiClient.get<DependencyGraph>('/services/dependencies');
    return response.data;
  },

  async start(name: string, options?: ServiceActionRequest): Promise<ServiceActionResponse> {
    const response = await apiClient.post<ServiceActionResponse>(
      `/services/${name}/start`,
      options || {}
    );
    return response.data;
  },

  async stop(name: string, options?: ServiceActionRequest): Promise<ServiceActionResponse> {
    const response = await apiClient.post<ServiceActionResponse>(
      `/services/${name}/stop`,
      options || {}
    );
    return response.data;
  },

  async restart(name: string, options?: ServiceActionRequest): Promise<ServiceActionResponse> {
    const response = await apiClient.post<ServiceActionResponse>(
      `/services/${name}/restart`,
      options || {}
    );
    return response.data;
  },

  async startGroup(groupId: string, options?: ServiceActionRequest): Promise<any> {
    const response = await apiClient.post(`/services/groups/${groupId}/start`, options || {});
    return response.data;
  },

  async stopGroup(groupId: string, options?: ServiceActionRequest): Promise<any> {
    const response = await apiClient.post(`/services/groups/${groupId}/stop`, options || {});
    return response.data;
  },
};
```

---

## Task 3: Create Services Store

**File**: `management-ui/frontend/src/store/servicesStore.ts`

```typescript
import { create } from 'zustand';
import { servicesApi } from '../api/services';
import { ServiceInfo, ServiceGroup, ServiceActionRequest } from '../types/service';

interface ServicesState {
  services: ServiceInfo[];
  groups: ServiceGroup[];
  isLoading: boolean;
  error: string | null;
  actionInProgress: string | null; // service name being acted upon

  fetchServices: () => Promise<void>;
  fetchGroups: () => Promise<void>;
  startService: (name: string, options?: ServiceActionRequest) => Promise<boolean>;
  stopService: (name: string, options?: ServiceActionRequest) => Promise<boolean>;
  restartService: (name: string, options?: ServiceActionRequest) => Promise<boolean>;
  startGroup: (groupId: string) => Promise<boolean>;
  stopGroup: (groupId: string) => Promise<boolean>;
  clearError: () => void;
}

export const useServicesStore = create<ServicesState>((set, get) => ({
  services: [],
  groups: [],
  isLoading: false,
  error: null,
  actionInProgress: null,

  fetchServices: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await servicesApi.list();
      set({ services: response.services, isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch services',
        isLoading: false,
      });
    }
  },

  fetchGroups: async () => {
    try {
      const response = await servicesApi.getGroups();
      set({ groups: response.groups });
    } catch (error: any) {
      console.error('Failed to fetch groups:', error);
    }
  },

  startService: async (name: string, options?: ServiceActionRequest) => {
    set({ actionInProgress: name, error: null });
    try {
      await servicesApi.start(name, options);
      await get().fetchServices();
      set({ actionInProgress: null });
      return true;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || `Failed to start ${name}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  stopService: async (name: string, options?: ServiceActionRequest) => {
    set({ actionInProgress: name, error: null });
    try {
      await servicesApi.stop(name, options);
      await get().fetchServices();
      set({ actionInProgress: null });
      return true;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || `Failed to stop ${name}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  restartService: async (name: string, options?: ServiceActionRequest) => {
    set({ actionInProgress: name, error: null });
    try {
      await servicesApi.restart(name, options);
      await get().fetchServices();
      set({ actionInProgress: null });
      return true;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || `Failed to restart ${name}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  startGroup: async (groupId: string) => {
    set({ actionInProgress: `group:${groupId}`, error: null });
    try {
      await servicesApi.startGroup(groupId);
      await get().fetchServices();
      await get().fetchGroups();
      set({ actionInProgress: null });
      return true;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || `Failed to start group ${groupId}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  stopGroup: async (groupId: string) => {
    set({ actionInProgress: `group:${groupId}`, error: null });
    try {
      await servicesApi.stopGroup(groupId);
      await get().fetchServices();
      await get().fetchGroups();
      set({ actionInProgress: null });
      return true;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || `Failed to stop group ${groupId}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  clearError: () => set({ error: null }),
}));
```

---

## Task 4: Create Service Components

**File**: `management-ui/frontend/src/components/services/StatusBadge.tsx`

```typescript
import React from 'react';
import { ServiceStatus, HealthStatus } from '../../types/service';

interface StatusBadgeProps {
  status: ServiceStatus;
  health?: HealthStatus;
  size?: 'sm' | 'md';
}

const statusColors: Record<ServiceStatus, string> = {
  running: 'bg-green-100 text-green-800',
  stopped: 'bg-gray-100 text-gray-800',
  starting: 'bg-yellow-100 text-yellow-800',
  stopping: 'bg-yellow-100 text-yellow-800',
  restarting: 'bg-blue-100 text-blue-800',
  error: 'bg-red-100 text-red-800',
  not_created: 'bg-gray-100 text-gray-500',
};

const healthColors: Record<HealthStatus, string> = {
  healthy: 'bg-green-500',
  unhealthy: 'bg-red-500',
  starting: 'bg-yellow-500',
  none: 'bg-gray-300',
  unknown: 'bg-gray-300',
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, health, size = 'md' }) => {
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1';

  return (
    <div className="flex items-center gap-2">
      <span className={`inline-flex items-center rounded-full font-medium ${sizeClass} ${statusColors[status]}`}>
        {status.replace('_', ' ')}
      </span>
      {health && health !== 'none' && (
        <span
          className={`w-2 h-2 rounded-full ${healthColors[health]}`}
          title={`Health: ${health}`}
        />
      )}
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/services/ServiceActions.tsx`

```typescript
import React from 'react';
import { Button } from '../common/Button';
import { ServiceStatus } from '../../types/service';

interface ServiceActionsProps {
  serviceName: string;
  status: ServiceStatus;
  isLoading: boolean;
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
}

export const ServiceActions: React.FC<ServiceActionsProps> = ({
  serviceName,
  status,
  isLoading,
  onStart,
  onStop,
  onRestart,
}) => {
  const canStart = status === 'stopped' || status === 'not_created' || status === 'error';
  const canStop = status === 'running';
  const canRestart = status === 'running';

  return (
    <div className="flex gap-2">
      {canStart && (
        <Button
          variant="primary"
          onClick={onStart}
          isLoading={isLoading}
          className="text-sm px-3 py-1"
        >
          Start
        </Button>
      )}
      {canStop && (
        <Button
          variant="danger"
          onClick={onStop}
          isLoading={isLoading}
          className="text-sm px-3 py-1"
        >
          Stop
        </Button>
      )}
      {canRestart && (
        <Button
          variant="secondary"
          onClick={onRestart}
          isLoading={isLoading}
          className="text-sm px-3 py-1"
        >
          Restart
        </Button>
      )}
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/services/ServiceCard.tsx`

```typescript
import React from 'react';
import { ServiceInfo } from '../../types/service';
import { Card } from '../common/Card';
import { StatusBadge } from './StatusBadge';
import { ServiceActions } from './ServiceActions';
import { useServicesStore } from '../../store/servicesStore';

interface ServiceCardProps {
  service: ServiceInfo;
}

export const ServiceCard: React.FC<ServiceCardProps> = ({ service }) => {
  const { startService, stopService, restartService, actionInProgress } = useServicesStore();
  const isLoading = actionInProgress === service.name;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-lg">{service.name}</h3>
          <p className="text-sm text-gray-500">{service.image || 'No image'}</p>
        </div>
        <StatusBadge status={service.status} health={service.health} />
      </div>

      {service.ports.length > 0 && (
        <div className="mt-2 text-sm text-gray-600">
          Ports: {service.ports.join(', ')}
        </div>
      )}

      {service.profiles.length > 0 && (
        <div className="mt-1 text-xs text-gray-500">
          Profile: {service.profiles.join(', ')}
        </div>
      )}

      <div className="mt-4 flex justify-end">
        <ServiceActions
          serviceName={service.name}
          status={service.status}
          isLoading={isLoading}
          onStart={() => startService(service.name)}
          onStop={() => stopService(service.name)}
          onRestart={() => restartService(service.name)}
        />
      </div>
    </Card>
  );
};
```

**File**: `management-ui/frontend/src/components/services/ServiceList.tsx`

```typescript
import React from 'react';
import { ServiceInfo } from '../../types/service';
import { ServiceCard } from './ServiceCard';

interface ServiceListProps {
  services: ServiceInfo[];
  groupBy?: 'group' | 'status' | 'none';
}

export const ServiceList: React.FC<ServiceListProps> = ({ services, groupBy = 'group' }) => {
  if (groupBy === 'none') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {services.map((service) => (
          <ServiceCard key={service.name} service={service} />
        ))}
      </div>
    );
  }

  // Group services
  const grouped = services.reduce((acc, service) => {
    const key = groupBy === 'group' ? service.group : service.status;
    if (!acc[key]) acc[key] = [];
    acc[key].push(service);
    return acc;
  }, {} as Record<string, ServiceInfo[]>);

  return (
    <div className="space-y-8">
      {Object.entries(grouped).map(([group, groupServices]) => (
        <div key={group}>
          <h3 className="text-lg font-semibold mb-4 capitalize">{group.replace('_', ' ')}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {groupServices.map((service) => (
              <ServiceCard key={service.name} service={service} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/services/ServiceGroup.tsx`

```typescript
import React from 'react';
import { ServiceGroup as ServiceGroupType } from '../../types/service';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { useServicesStore } from '../../store/servicesStore';

interface ServiceGroupCardProps {
  group: ServiceGroupType;
}

export const ServiceGroupCard: React.FC<ServiceGroupCardProps> = ({ group }) => {
  const { startGroup, stopGroup, actionInProgress } = useServicesStore();
  const isLoading = actionInProgress === `group:${group.id}`;

  const allRunning = group.running_count === group.total_count;
  const allStopped = group.running_count === 0;

  return (
    <Card>
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold">{group.name}</h3>
          <p className="text-sm text-gray-500">{group.description}</p>
        </div>
        <div className="text-right">
          <span className={`text-2xl font-bold ${allRunning ? 'text-green-600' : allStopped ? 'text-gray-400' : 'text-yellow-600'}`}>
            {group.running_count}/{group.total_count}
          </span>
          <p className="text-xs text-gray-500">running</p>
        </div>
      </div>

      <div className="mt-4 flex gap-2 justify-end">
        {!allRunning && (
          <Button
            variant="primary"
            onClick={() => startGroup(group.id)}
            isLoading={isLoading}
            className="text-sm"
          >
            Start All
          </Button>
        )}
        {!allStopped && (
          <Button
            variant="danger"
            onClick={() => stopGroup(group.id)}
            isLoading={isLoading}
            className="text-sm"
          >
            Stop All
          </Button>
        )}
      </div>
    </Card>
  );
};
```

---

## Task 5: Create Services Page

**File**: `management-ui/frontend/src/pages/Services.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { useServicesStore } from '../store/servicesStore';
import { ServiceList } from '../components/services/ServiceList';
import { ServiceGroupCard } from '../components/services/ServiceGroup';
import { Loading } from '../components/common/Loading';
import { Button } from '../components/common/Button';

type ViewMode = 'list' | 'groups';
type GroupBy = 'group' | 'status' | 'none';

export const Services: React.FC = () => {
  const { services, groups, isLoading, error, fetchServices, fetchGroups, clearError } = useServicesStore();
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [groupBy, setGroupBy] = useState<GroupBy>('group');

  useEffect(() => {
    fetchServices();
    fetchGroups();

    // Poll every 5 seconds
    const interval = setInterval(() => {
      fetchServices();
      fetchGroups();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchServices, fetchGroups]);

  if (isLoading && services.length === 0) {
    return <Loading message="Loading services..." />;
  }

  const runningCount = services.filter((s) => s.status === 'running').length;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">Services</h2>
          <p className="text-gray-600">
            {runningCount} of {services.length} services running
          </p>
        </div>

        <div className="flex gap-4">
          <select
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value as ViewMode)}
            className="input w-auto"
          >
            <option value="list">List View</option>
            <option value="groups">Groups View</option>
          </select>

          {viewMode === 'list' && (
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as GroupBy)}
              className="input w-auto"
            >
              <option value="group">Group by Type</option>
              <option value="status">Group by Status</option>
              <option value="none">No Grouping</option>
            </select>
          )}

          <Button variant="secondary" onClick={() => { fetchServices(); fetchGroups(); }}>
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 flex justify-between">
          <span>{error}</span>
          <button onClick={clearError} className="font-bold">&times;</button>
        </div>
      )}

      {viewMode === 'groups' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {groups.map((group) => (
            <ServiceGroupCard key={group.id} group={group} />
          ))}
        </div>
      ) : (
        <ServiceList services={services} groupBy={groupBy} />
      )}
    </div>
  );
};
```

---

## Task 6: Update Dashboard

**File**: `management-ui/frontend/src/pages/Dashboard.tsx` (update)

```typescript
import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useServicesStore } from '../store/servicesStore';
import { Card } from '../components/common/Card';
import { ServiceGroupCard } from '../components/services/ServiceGroup';

export const Dashboard: React.FC = () => {
  const { services, groups, fetchServices, fetchGroups } = useServicesStore();

  useEffect(() => {
    fetchServices();
    fetchGroups();

    const interval = setInterval(() => {
      fetchServices();
      fetchGroups();
    }, 10000);

    return () => clearInterval(interval);
  }, [fetchServices, fetchGroups]);

  const runningCount = services.filter((s) => s.status === 'running').length;
  const healthyCount = services.filter((s) => s.health === 'healthy').length;
  const errorCount = services.filter((s) => s.status === 'error' || s.health === 'unhealthy').length;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card>
          <p className="text-gray-500 text-sm">Services Running</p>
          <p className="text-3xl font-bold text-green-600">
            {runningCount}/{services.length}
          </p>
        </Card>

        <Card>
          <p className="text-gray-500 text-sm">Healthy</p>
          <p className="text-3xl font-bold text-blue-600">{healthyCount}</p>
        </Card>

        <Card>
          <p className="text-gray-500 text-sm">Issues</p>
          <p className={`text-3xl font-bold ${errorCount > 0 ? 'text-red-600' : 'text-gray-400'}`}>
            {errorCount}
          </p>
        </Card>

        <Card>
          <p className="text-gray-500 text-sm">Groups</p>
          <p className="text-3xl font-bold text-purple-600">{groups.length}</p>
        </Card>
      </div>

      {/* Service Groups */}
      <div className="mb-8">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Service Groups</h3>
          <Link to="/services" className="text-blue-600 hover:underline text-sm">
            View all services →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {groups.slice(0, 6).map((group) => (
            <ServiceGroupCard key={group.id} group={group} />
          ))}
        </div>
      </div>

      {/* Quick Links */}
      <Card title="Quick Actions">
        <div className="flex gap-4">
          <Link to="/services" className="btn btn-primary">
            Manage Services
          </Link>
          <Link to="/config" className="btn btn-secondary">
            Configuration
          </Link>
          <Link to="/logs" className="btn btn-secondary">
            View Logs
          </Link>
        </div>
      </Card>
    </div>
  );
};
```

---

## Task 7: Update App Routes

**File**: `management-ui/frontend/src/App.tsx` (update routes)

```typescript
// Update the routes section:
<Route element={<MainLayout />}>
  <Route path="/" element={<Dashboard />} />
  <Route path="/services" element={<Services />} />
  <Route path="/config" element={<div>Config (Stage 06)</div>} />
  <Route path="/logs" element={<div>Logs (Stage 07)</div>} />
</Route>

// Add import at top:
import { Services } from './pages/Services';
```

---

## Validation

### Test UI
1. Start backend and frontend
2. Login to dashboard
3. View service statistics
4. Navigate to Services page
5. Test start/stop/restart on individual services
6. Test group start/stop
7. Verify status updates after actions

### Success Criteria
- [ ] Dashboard shows running/total services count
- [ ] Dashboard shows healthy count and error count
- [ ] Service groups display with running counts
- [ ] Services page lists all services with status
- [ ] Start button works for stopped services
- [ ] Stop button works for running services
- [ ] Restart button works for running services
- [ ] Group start/stop works
- [ ] Status refreshes automatically every 5 seconds
- [ ] Error messages display properly

---

## Next Stage
Proceed to `06-configuration-management.md` to add .env editing capabilities.
