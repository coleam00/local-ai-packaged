import type { ServiceStatus, HealthStatus } from '../../types/service';

interface StatusBadgeProps {
  status: ServiceStatus;
  health?: HealthStatus;
  showHealth?: boolean;
}

const statusConfig: Record<
  ServiceStatus,
  { label: string; bgClass: string; textClass: string }
> = {
  running: {
    label: 'Running',
    bgClass: 'bg-[#1e40af]',
    textClass: 'text-[#dbeafe]',
  },
  stopped: {
    label: 'Stopped',
    bgClass: 'bg-slate-600',
    textClass: 'text-slate-300',
  },
  starting: {
    label: 'Starting',
    bgClass: 'bg-amber-600',
    textClass: 'text-amber-100',
  },
  stopping: {
    label: 'Stopping',
    bgClass: 'bg-amber-600',
    textClass: 'text-amber-100',
  },
  restarting: {
    label: 'Restarting',
    bgClass: 'bg-amber-600',
    textClass: 'text-amber-100',
  },
  error: {
    label: 'Error',
    bgClass: 'bg-red-900',
    textClass: 'text-red-200',
  },
  not_created: {
    label: 'Not Created',
    bgClass: 'bg-slate-700',
    textClass: 'text-slate-400',
  },
};

const healthConfig: Record<
  HealthStatus,
  { label: string; bgClass: string; textClass: string }
> = {
  healthy: {
    label: 'Healthy',
    bgClass: 'bg-[#065f46]',
    textClass: 'text-[#d1fae5]',
  },
  unhealthy: {
    label: 'Unhealthy',
    bgClass: 'bg-red-900',
    textClass: 'text-red-200',
  },
  starting: {
    label: 'Starting',
    bgClass: 'bg-amber-700',
    textClass: 'text-amber-100',
  },
  none: {
    label: 'No Check',
    bgClass: 'bg-slate-700',
    textClass: 'text-slate-400',
  },
  unknown: {
    label: 'Unknown',
    bgClass: 'bg-slate-700',
    textClass: 'text-slate-400',
  },
};

export function StatusBadge({ status, health, showHealth = true }: StatusBadgeProps) {
  const statusCfg = statusConfig[status];
  const healthCfg = health ? healthConfig[health] : null;

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusCfg.bgClass} ${statusCfg.textClass}`}
      >
        <span
          className={`w-1.5 h-1.5 mr-1.5 rounded-full ${
            status === 'running'
              ? 'animate-pulse bg-blue-300'
              : 'bg-current opacity-50'
          }`}
        />
        {statusCfg.label}
      </span>
      {showHealth && healthCfg && health !== 'none' && (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${healthCfg.bgClass} ${healthCfg.textClass}`}
        >
          {healthCfg.label}
        </span>
      )}
    </div>
  );
}
