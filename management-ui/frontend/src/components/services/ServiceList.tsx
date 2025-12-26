import { useEffect, useState } from 'react';
import { RefreshCw, AlertCircle, Search } from 'lucide-react';
import { useServicesStore } from '../../store/servicesStore';
import { ServiceCard } from './ServiceCard';
import { Button } from '../common/Button';

interface ServiceListProps {
  filterGroup?: string;
  showSearch?: boolean;
}

export function ServiceList({ filterGroup, showSearch = true }: ServiceListProps) {
  const {
    services,
    isLoading,
    error,
    actionInProgress,
    fetchServices,
    startService,
    stopService,
    restartService,
    clearError,
  } = useServicesStore();

  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchServices();

    // Poll for updates every 5 seconds
    const interval = setInterval(fetchServices, 5000);
    return () => clearInterval(interval);
  }, [fetchServices]);

  const filteredServices = services.filter((service) => {
    const matchesGroup = !filterGroup || service.group === filterGroup;
    const matchesSearch =
      !searchQuery ||
      service.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      service.image?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesGroup && matchesSearch;
  });

  const sortedServices = [...filteredServices].sort((a, b) => {
    // Sort by status: running first, then by name
    if (a.status === 'running' && b.status !== 'running') return -1;
    if (a.status !== 'running' && b.status === 'running') return 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="space-y-4">
      {/* Header with search and refresh */}
      <div className="flex items-center justify-between gap-4">
        {showSearch && (
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
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => fetchServices()}
          disabled={isLoading}
          className="text-gray-400 hover:text-white"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span className="ml-2">Refresh</span>
        </Button>
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

      {/* Services grid */}
      {sortedServices.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          {isLoading ? (
            <p>Loading services...</p>
          ) : searchQuery ? (
            <p>No services match your search</p>
          ) : (
            <p>No services found</p>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedServices.map((service) => (
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
      <div className="flex items-center justify-between text-sm text-gray-400 pt-2 border-t border-gray-700">
        <span>
          {filteredServices.filter((s) => s.status === 'running').length} of{' '}
          {filteredServices.length} services running
        </span>
        {filterGroup && <span>Filtered by: {filterGroup}</span>}
      </div>
    </div>
  );
}
