import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Heart, Settings, ArrowRight, Box, RefreshCw } from 'lucide-react';
import { Card } from '../components/common/Card';
import { useServicesStore } from '../store/servicesStore';
import { ServiceCard } from '../components/services';

export const Dashboard: React.FC = () => {
  const {
    services,
    isLoading,
    actionInProgress,
    fetchServices,
    startService,
    stopService,
    restartService,
  } = useServicesStore();

  useEffect(() => {
    fetchServices();

    // Poll for updates every 5 seconds
    const interval = setInterval(fetchServices, 5000);
    return () => clearInterval(interval);
  }, [fetchServices]);

  // Calculate stats
  const runningCount = services.filter((s) => s.status === 'running').length;
  const healthyCount = services.filter((s) => s.health === 'healthy').length;
  const totalCount = services.length;

  // Get top 6 services sorted by status (running first)
  const topServices = [...services]
    .sort((a, b) => {
      if (a.status === 'running' && b.status !== 'running') return -1;
      if (a.status !== 'running' && b.status === 'running') return 1;
      return a.name.localeCompare(b.name);
    })
    .slice(0, 6);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Dashboard</h2>
        <button
          onClick={() => fetchServices()}
          disabled={isLoading}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Box className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Services</p>
              <p className="text-2xl font-bold text-white">
                {runningCount} / {totalCount}
              </p>
              <p className="text-xs text-gray-500">Running / Total</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-500/20 rounded-lg">
              <Heart className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Health</p>
              <p className="text-2xl font-bold text-white">{healthyCount}</p>
              <p className="text-xs text-gray-500">Healthy Services</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <Activity className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Status</p>
              <p className="text-2xl font-bold text-white">
                {runningCount === totalCount
                  ? 'All Running'
                  : runningCount === 0
                  ? 'All Stopped'
                  : 'Partial'}
              </p>
              <p className="text-xs text-gray-500">System Status</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Quick services */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Services</h3>
          <Link
            to="/services"
            className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            View all
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {services.length === 0 ? (
          <Card>
            <p className="text-gray-400 text-center py-4">
              {isLoading ? 'Loading services...' : 'No services found'}
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {topServices.map((service) => (
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
      </div>

      {/* Quick actions */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link to="/services">
            <Card className="hover:border-blue-500/50 transition-colors cursor-pointer">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500/20 rounded-lg">
                  <Box className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className="font-medium text-white">Manage Services</p>
                  <p className="text-sm text-gray-400">Start, stop, and restart services</p>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 ml-auto" />
              </div>
            </Card>
          </Link>

          <Link to="/settings">
            <Card className="hover:border-blue-500/50 transition-colors cursor-pointer">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-yellow-500/20 rounded-lg">
                  <Settings className="w-6 h-6 text-yellow-400" />
                </div>
                <div>
                  <p className="font-medium text-white">Settings</p>
                  <p className="text-sm text-gray-400">Configure environment variables</p>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 ml-auto" />
              </div>
            </Card>
          </Link>
        </div>
      </div>
    </div>
  );
};
