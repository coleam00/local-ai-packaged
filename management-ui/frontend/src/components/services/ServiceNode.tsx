import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import type { NodeProps } from 'reactflow';
import type { ServiceStatus, HealthStatus } from '../../types/service';

interface ServiceNodeData {
  label: string;
  group: string;
  status: ServiceStatus;
  health: HealthStatus;
  profiles: string[];
  hasHealthcheck: boolean;
  composeFile: string;
  onClick?: (serviceName: string) => void;
}

const groupColors: Record<string, string> = {
  supabase: 'border-purple-500 bg-purple-500/20',
  core_ai: 'border-blue-500 bg-blue-500/20',
  workflow: 'border-orange-500 bg-orange-500/20',
  database: 'border-green-500 bg-green-500/20',
  observability: 'border-yellow-500 bg-yellow-500/20',
  infrastructure: 'border-gray-500 bg-gray-500/20',
  langfuse: 'border-pink-500 bg-pink-500/20',
  other: 'border-gray-400 bg-gray-400/20',
};

const statusIndicators: Record<ServiceStatus, string> = {
  running: 'bg-green-500',
  stopped: 'bg-gray-500',
  starting: 'bg-yellow-500 animate-pulse',
  stopping: 'bg-yellow-500',
  restarting: 'bg-blue-500 animate-pulse',
  error: 'bg-red-500',
  not_created: 'bg-gray-600',
};

const ServiceNode: React.FC<NodeProps<ServiceNodeData>> = ({ data, selected }) => {
  const groupColor = groupColors[data.group] || groupColors.other;
  const statusColor = statusIndicators[data.status] || statusIndicators.stopped;

  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 shadow-lg min-w-[150px] max-w-[200px]
        bg-gray-800 text-white
        ${groupColor}
        ${selected ? 'ring-2 ring-blue-400 ring-offset-2 ring-offset-gray-900' : ''}
        cursor-pointer hover:shadow-xl hover:scale-105 transition-all duration-200
      `}
      onClick={() => data.onClick?.(data.label)}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-gray-500 !border-gray-400 !w-3 !h-3"
      />

      <div className="flex items-center gap-2">
        <div className={`w-3 h-3 rounded-full ${statusColor} flex-shrink-0`} />
        <span className="font-medium text-sm truncate">{data.label}</span>
      </div>

      <div className="flex items-center gap-2 mt-1">
        <span className="text-xs text-gray-400 capitalize">{data.group}</span>
        {data.hasHealthcheck && (
          <span className="text-xs text-green-400" title="Has healthcheck">
            ♥
          </span>
        )}
      </div>

      {data.profiles.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {data.profiles.slice(0, 2).map((profile) => (
            <span
              key={profile}
              className="text-xs px-1.5 py-0.5 bg-gray-700 rounded text-gray-300"
            >
              {profile}
            </span>
          ))}
          {data.profiles.length > 2 && (
            <span className="text-xs text-gray-500">+{data.profiles.length - 2}</span>
          )}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-gray-500 !border-gray-400 !w-3 !h-3"
      />
    </div>
  );
};

export default memo(ServiceNode);
