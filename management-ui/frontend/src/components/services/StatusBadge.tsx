import type { ServiceStatus, HealthStatus } from '../../types/service';

interface StatusBadgeProps {
  status: ServiceStatus;
  health?: HealthStatus;
  showHealth?: boolean;
}

const statusConfig: Record<ServiceStatus, { label: string; color: string }> = {
  running: { label: 'Running', color: 'bg-green-500' },
  stopped: { label: 'Stopped', color: 'bg-gray-500' },
  starting: { label: 'Starting', color: 'bg-yellow-500' },
  stopping: { label: 'Stopping', color: 'bg-yellow-500' },
  restarting: { label: 'Restarting', color: 'bg-yellow-500' },
  error: { label: 'Error', color: 'bg-red-500' },
  not_created: { label: 'Not Created', color: 'bg-gray-400' },
};

const healthConfig: Record<HealthStatus, { label: string; color: string }> = {
  healthy: { label: 'Healthy', color: 'bg-green-400' },
  unhealthy: { label: 'Unhealthy', color: 'bg-red-400' },
  starting: { label: 'Starting', color: 'bg-yellow-400' },
  none: { label: 'No Check', color: 'bg-gray-400' },
  unknown: { label: 'Unknown', color: 'bg-gray-400' },
};

export function StatusBadge({ status, health, showHealth = true }: StatusBadgeProps) {
  const statusCfg = statusConfig[status];
  const healthCfg = health ? healthConfig[health] : null;

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-white ${statusCfg.color}`}
      >
        <span
          className={`w-2 h-2 mr-1.5 rounded-full ${
            status === 'running' ? 'animate-pulse bg-white' : 'bg-white/50'
          }`}
        />
        {statusCfg.label}
      </span>
      {showHealth && healthCfg && health !== 'none' && (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-white ${healthCfg.color}`}
        >
          {healthCfg.label}
        </span>
      )}
    </div>
  );
}
