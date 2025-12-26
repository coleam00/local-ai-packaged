import { useEffect, useMemo } from 'react';
import { useServicesStore } from '../store/servicesStore';
import { ServiceCard, ServiceGroup } from '../components/services';
import { RefreshCw, AlertCircle, Search, Layers } from 'lucide-react';
import { Button } from '../components/common/Button';
import { useState } from 'react';

export const Services: React.FC = () => {
  const {
    services,
    groups,
    isLoading,
    error,
    actionInProgress,
    fetchServices,
    fetchGroups,
    startService,
    stopService,
    restartService,
    startGroup,
    stopGroup,
    clearError,
  } = useServicesStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grouped' | 'list'>('grouped');

  useEffect(() => {
    fetchServices();
    fetchGroups();

    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      fetchServices();
      fetchGroups();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchServices, fetchGroups]);

  // Filter services by search query
  const filteredServices = useMemo(() => {
    if (!searchQuery) return services;
    const query = searchQuery.toLowerCase();
    return services.filter(
      (service) =>
        service.name.toLowerCase().includes(query) ||
        service.image?.toLowerCase().includes(query) ||
        service.group.toLowerCase().includes(query)
    );
  }, [services, searchQuery]);

  // Group services by their group property
  const groupedServices = useMemo(() => {
    const map = new Map<string, typeof services>();
    for (const service of filteredServices) {
      const groupName = service.group || 'Other';
      if (!map.has(groupName)) {
        map.set(groupName, []);
      }
      map.get(groupName)!.push(service);
    }
    return map;
  }, [filteredServices]);

  // Find group metadata for a group ID
  const getGroupMeta = (groupId: string) => {
    return groups.find((g) => g.id === groupId);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Services</h2>
          <p className="text-gray-400 mt-1">
            Manage and monitor your Docker services
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            fetchServices();
            fetchGroups();
          }}
          disabled={isLoading}
          className="text-gray-400 hover:text-white"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span className="ml-2">Refresh</span>
        </Button>
      </div>

      {/* Search and view controls */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search services..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
          <Button
            size="sm"
            variant={viewMode === 'grouped' ? 'primary' : 'ghost'}
            onClick={() => setViewMode('grouped')}
            className={viewMode !== 'grouped' ? 'text-gray-400' : ''}
          >
            <Layers className="w-4 h-4" />
            <span className="ml-1">Grouped</span>
          </Button>
          <Button
            size="sm"
            variant={viewMode === 'list' ? 'primary' : 'ghost'}
            onClick={() => setViewMode('list')}
            className={viewMode !== 'list' ? 'text-gray-400' : ''}
          >
            <span>All</span>
          </Button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-red-400 flex-1">{error}</p>
          <Button variant="ghost" size="sm" onClick={clearError} className="text-red-400">
            Dismiss
          </Button>
        </div>
      )}

      {/* Content */}
      {filteredServices.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          {isLoading ? (
            <p>Loading services...</p>
          ) : searchQuery ? (
            <p>No services match your search</p>
          ) : (
            <p>No services found</p>
          )}
        </div>
      ) : viewMode === 'grouped' ? (
        <div className="space-y-6">
          {Array.from(groupedServices.entries()).map(([groupId, groupServices]) => {
            const groupMeta = getGroupMeta(groupId);
            const runningCount = groupServices.filter(s => s.status === 'running').length;

            const groupData = groupMeta || {
              id: groupId,
              name: groupId.charAt(0).toUpperCase() + groupId.slice(1),
              description: `${groupServices.length} services`,
              services: groupServices.map(s => s.name),
              running_count: runningCount,
              total_count: groupServices.length,
            };

            return (
              <ServiceGroup
                key={groupId}
                group={groupData}
                isActionInProgress={actionInProgress === `group:${groupId}`}
                onStartGroup={() => startGroup(groupId)}
                onStopGroup={() => stopGroup(groupId)}
              >
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
                  {groupServices
                    .sort((a, b) => {
                      if (a.status === 'running' && b.status !== 'running') return -1;
                      if (a.status !== 'running' && b.status === 'running') return 1;
                      return a.name.localeCompare(b.name);
                    })
                    .map((service) => (
                      <ServiceCard
                        key={service.name}
                        service={service}
                        isActionInProgress={actionInProgress === service.name}
                        onStart={() => startService(service.name)}
                        onStop={() => stopService(service.name)}
                        onRestart={() => restartService(service.name)}
                      />
                    ))}
                </div>
              </ServiceGroup>
            );
          })}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredServices
            .sort((a, b) => {
              if (a.status === 'running' && b.status !== 'running') return -1;
              if (a.status !== 'running' && b.status === 'running') return 1;
              return a.name.localeCompare(b.name);
            })
            .map((service) => (
              <ServiceCard
                key={service.name}
                service={service}
                isActionInProgress={actionInProgress === service.name}
                onStart={() => startService(service.name)}
                onStop={() => stopService(service.name)}
                onRestart={() => restartService(service.name)}
              />
            ))}
        </div>
      )}

      {/* Summary */}
      <div className="flex items-center justify-between text-sm text-gray-400 pt-4 border-t border-gray-700">
        <span>
          {filteredServices.filter((s) => s.status === 'running').length} of{' '}
          {filteredServices.length} services running
        </span>
        <span>{groups.length} groups</span>
      </div>
    </div>
  );
};
