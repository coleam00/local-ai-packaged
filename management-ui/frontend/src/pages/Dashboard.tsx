import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Box, Heart, Activity, ArrowRight, Settings, RefreshCw } from 'lucide-react';
import { Card } from '../components/common/Card';
import { useServicesStore } from '../store/servicesStore';
import { ServiceCard } from '../components/services';

// Progress Bar Component
interface ProgressBarProps {
  value: number;
  max: number;
  color: 'blue' | 'green' | 'purple';
}

const ProgressBar: React.FC<ProgressBarProps> = ({ value, max, color }) => {
  const percentage = max > 0 ? (value / max) * 100 : 0;
  const colorClass = {
    blue: 'bg-blue-500',
    green: 'bg-emerald-500',
    purple: 'bg-purple-500',
  }[color];

  return (
    <div className="h-2 bg-[#374151] rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ease-out ${colorClass}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
};

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
        <div>
          <h2 className="text-2xl font-bold text-white">Dashboard</h2>
          <p className="text-sm text-slate-400 mt-1">
            Monitor and manage your LocalAI stack
          </p>
        </div>
        <button
          onClick={() => fetchServices()}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400
                     hover:text-white hover:bg-[#1e293b] rounded-lg transition-colors
                     border border-[#374151] hover:border-[#4b5563]"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Services Card */}
        <Card variant="blue">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Box className="w-6 h-6 text-blue-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-slate-400">Services</p>
              <p className="text-2xl font-bold text-white">
                {runningCount} / {totalCount}
              </p>
            </div>
          </div>
          <ProgressBar value={runningCount} max={totalCount} color="blue" />
          <p className="text-xs text-slate-500 mt-2">Running / Total</p>
        </Card>

        {/* Health Card */}
        <Card variant="green">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-emerald-500/20 rounded-lg">
              <Heart className="w-6 h-6 text-emerald-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-slate-400">Health</p>
              <p className="text-2xl font-bold text-white">{healthyCount}</p>
            </div>
          </div>
          <ProgressBar value={healthyCount} max={runningCount || 1} color="green" />
          <p className="text-xs text-slate-500 mt-2">Healthy Services</p>
        </Card>

        {/* System Status Card */}
        <Card variant="purple">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <Activity className="w-6 h-6 text-purple-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-slate-400">System Status</p>
              <p className="text-2xl font-bold text-white">
                {runningCount === totalCount
                  ? 'All Running'
                  : runningCount === 0
                  ? 'All Stopped'
                  : 'Partial'}
              </p>
            </div>
          </div>
          <ProgressBar
            value={runningCount}
            max={totalCount}
            color="purple"
          />
          <p className="text-xs text-slate-500 mt-2">
            {totalCount > 0
              ? `${Math.round((runningCount / totalCount) * 100)}% operational`
              : 'No services configured'}
          </p>
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
            <p className="text-slate-400 text-center py-8">
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Loading services...
                </span>
              ) : (
                'No services found'
              )}
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
            <Card className="hover:border-blue-500/50 transition-all hover:translate-y-[-2px]">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500/20 rounded-lg">
                  <Box className="w-6 h-6 text-blue-400" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-white">Manage Services</p>
                  <p className="text-sm text-slate-400">
                    Start, stop, and restart services
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-slate-500" />
              </div>
            </Card>
          </Link>

          <Link to="/config">
            <Card className="hover:border-amber-500/50 transition-all hover:translate-y-[-2px]">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-amber-500/20 rounded-lg">
                  <Settings className="w-6 h-6 text-amber-400" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-white">Configuration</p>
                  <p className="text-sm text-slate-400">
                    Configure environment variables
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-slate-500" />
              </div>
            </Card>
          </Link>
        </div>
      </div>
    </div>
  );
};
