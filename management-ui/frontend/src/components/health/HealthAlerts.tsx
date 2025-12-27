import { AlertTriangle, AlertCircle, Info, X, Check } from 'lucide-react';
import { Button } from '../common/Button';
import type { HealthAlert, AlertSeverity } from '../../types/metrics';

interface HealthAlertsProps {
  alerts: HealthAlert[];
  onAcknowledge: (alertId: string) => void;
  isLoading?: boolean;
}

const severityConfig: Record<
  AlertSeverity,
  { icon: typeof AlertCircle; bgClass: string; borderClass: string; textClass: string }
> = {
  critical: {
    icon: AlertCircle,
    bgClass: 'bg-red-900/20',
    borderClass: 'border-red-700/30',
    textClass: 'text-red-400',
  },
  warning: {
    icon: AlertTriangle,
    bgClass: 'bg-amber-900/20',
    borderClass: 'border-amber-700/30',
    textClass: 'text-amber-400',
  },
  info: {
    icon: Info,
    bgClass: 'bg-blue-900/20',
    borderClass: 'border-blue-700/30',
    textClass: 'text-blue-400',
  },
};

export function HealthAlerts({ alerts, onAcknowledge, isLoading }: HealthAlertsProps) {
  if (alerts.length === 0) {
    return (
      <div className="bg-[#1e293b] rounded-lg border border-[#374151] p-6 text-center">
        <Check className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
        <p className="text-slate-400">No active alerts</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {alerts.map((alert) => {
        const config = severityConfig[alert.severity];
        const Icon = config.icon;

        return (
          <div
            key={alert.id}
            className={`flex items-start gap-3 p-4 rounded-lg border ${config.bgClass} ${config.borderClass}`}
          >
            <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${config.textClass}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className={`font-medium ${config.textClass}`}>{alert.service_name}</p>
                  <p className="text-sm text-slate-300 mt-0.5">{alert.message}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {new Date(alert.timestamp).toLocaleString()}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onAcknowledge(alert.id)}
                  disabled={isLoading}
                  className={`${config.textClass} hover:opacity-80`}
                  title="Acknowledge"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
