import { AlertTriangle, AlertCircle, Info, RefreshCw, Clock, Wrench } from 'lucide-react';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import type { DiagnosticsResponse, DiagnosticResult, AlertSeverity } from '../../types/metrics';

interface DiagnosticsPanelProps {
  diagnostics: DiagnosticsResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
  onRestart: () => void;
  isRestartInProgress?: boolean;
}

const severityConfig: Record<AlertSeverity, { icon: typeof AlertCircle; className: string }> = {
  critical: { icon: AlertCircle, className: 'text-red-400' },
  warning: { icon: AlertTriangle, className: 'text-amber-400' },
  info: { icon: Info, className: 'text-blue-400' },
};

function formatUptime(seconds: number | null): string {
  if (seconds === null) return 'Unknown';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

function IssueItem({ issue }: { issue: DiagnosticResult }) {
  const config = severityConfig[issue.severity];
  const Icon = config.icon;

  return (
    <div className="p-3 bg-[#374151]/50 rounded-lg">
      <div className="flex items-start gap-2">
        <Icon className={`w-4 h-4 mt-0.5 ${config.className}`} />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-white text-sm">{issue.issue}</p>
          <p className="text-xs text-slate-400 mt-0.5">{issue.description}</p>
          <div className="flex items-start gap-2 mt-2 p-2 bg-[#1e293b] rounded">
            <Wrench className="w-3 h-3 text-blue-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-blue-300">{issue.recommendation}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export function DiagnosticsPanel({
  diagnostics,
  isLoading,
  onRefresh,
  onRestart,
  isRestartInProgress,
}: DiagnosticsPanelProps) {
  if (isLoading && !diagnostics) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-5 h-5 text-slate-400 animate-spin" />
          <span className="ml-2 text-slate-400">Running diagnostics...</span>
        </div>
      </Card>
    );
  }

  if (!diagnostics) {
    return (
      <Card>
        <div className="text-center py-8">
          <p className="text-slate-400">Select a service to run diagnostics</p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Diagnostics</h3>
        <Button variant="ghost" size="sm" onClick={onRefresh} disabled={isLoading}>
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Uptime info */}
      <div className="flex items-center gap-4 mb-4 p-3 bg-[#374151]/30 rounded-lg">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-slate-400" />
          <span className="text-sm text-slate-400">Uptime:</span>
          <span className="text-sm text-white font-medium">
            {formatUptime(diagnostics.uptime_seconds)}
          </span>
        </div>
        {diagnostics.last_restart && (
          <div className="text-sm text-slate-500">
            Last restart: {new Date(diagnostics.last_restart).toLocaleString()}
          </div>
        )}
      </div>

      {/* Issues */}
      {diagnostics.issues.length === 0 ? (
        <div className="text-center py-6 text-emerald-400">
          <Info className="w-6 h-6 mx-auto mb-2" />
          <p>No issues detected</p>
        </div>
      ) : (
        <div className="space-y-2 mb-4">
          {diagnostics.issues.map((issue, idx) => (
            <IssueItem key={idx} issue={issue} />
          ))}
        </div>
      )}

      {/* Restart recommendation */}
      {diagnostics.restart_recommended && (
        <div className="flex items-center justify-between p-3 bg-amber-900/20 border border-amber-700/30 rounded-lg mt-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span className="text-sm text-amber-400">Restart recommended</span>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={onRestart}
            disabled={isRestartInProgress}
          >
            {isRestartInProgress ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin mr-1" />
                Restarting...
              </>
            ) : (
              'Restart Service'
            )}
          </Button>
        </div>
      )}
    </Card>
  );
}
