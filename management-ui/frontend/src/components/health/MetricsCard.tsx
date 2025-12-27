import { Cpu, HardDrive, Network } from 'lucide-react';
import type { ContainerMetrics } from '../../types/metrics';

interface MetricsCardProps {
  metrics: ContainerMetrics;
  onClick?: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatRate(bytesPerSec: number): string {
  return `${formatBytes(bytesPerSec)}/s`;
}

function getColorForPercent(percent: number): string {
  if (percent >= 90) return 'text-red-400';
  if (percent >= 75) return 'text-amber-400';
  return 'text-emerald-400';
}

function ProgressBar({ value, color }: { value: number; color: string }) {
  const percent = Math.min(value, 100);
  return (
    <div className="h-1.5 bg-[#374151] rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-300 ${color}`}
        style={{ width: `${percent}%` }}
      />
    </div>
  );
}

export function MetricsCard({ metrics, onClick }: MetricsCardProps) {
  const cpuColor = metrics.cpu_percent >= 90 ? 'bg-red-500' : metrics.cpu_percent >= 75 ? 'bg-amber-500' : 'bg-emerald-500';
  const memColor = metrics.memory_percent >= 90 ? 'bg-red-500' : metrics.memory_percent >= 75 ? 'bg-amber-500' : 'bg-emerald-500';

  return (
    <div
      className={`bg-[#1e293b] rounded-[12px] p-4 border border-[#374151]
                  hover:border-[#4b5563] transition-all duration-200 ${
        onClick ? 'cursor-pointer hover:translate-y-[-2px]' : ''
      }`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-white truncate">{metrics.service_name}</h3>
        <span className="text-xs text-slate-500">
          {new Date(metrics.timestamp).toLocaleTimeString()}
        </span>
      </div>

      {/* CPU */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">CPU</span>
          </div>
          <span className={`text-sm font-medium ${getColorForPercent(metrics.cpu_percent)}`}>
            {metrics.cpu_percent.toFixed(1)}%
          </span>
        </div>
        <ProgressBar value={metrics.cpu_percent} color={cpuColor} />
      </div>

      {/* Memory */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">Memory</span>
          </div>
          <span className={`text-sm font-medium ${getColorForPercent(metrics.memory_percent)}`}>
            {formatBytes(metrics.memory_usage)} / {formatBytes(metrics.memory_limit)}
          </span>
        </div>
        <ProgressBar value={metrics.memory_percent} color={memColor} />
      </div>

      {/* Network */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-slate-400" />
          <span className="text-slate-400">Network</span>
        </div>
        <div className="flex gap-3">
          <span className="text-emerald-400" title="Download">
            ↓ {formatRate(metrics.network_rx_rate)}
          </span>
          <span className="text-blue-400" title="Upload">
            ↑ {formatRate(metrics.network_tx_rate)}
          </span>
        </div>
      </div>
    </div>
  );
}
