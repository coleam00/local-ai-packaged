import { Play, Square, RotateCw, Loader2 } from 'lucide-react';
import { Button } from '../common/Button';
import type { ServiceStatus } from '../../types/service';

interface ServiceActionsProps {
  serviceName: string;
  status: ServiceStatus;
  isLoading: boolean;
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
}

export function ServiceActions({
  serviceName,
  status,
  isLoading,
  onStart,
  onStop,
  onRestart,
}: ServiceActionsProps) {
  const canStart = status === 'stopped' || status === 'not_created' || status === 'error';
  const canStop = status === 'running';
  const canRestart = status === 'running';
  const isTransitioning = status === 'starting' || status === 'stopping' || status === 'restarting';

  if (isLoading || isTransitioning) {
    return (
      <div className="flex items-center gap-2 text-gray-400">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm">
          {isLoading ? 'Processing...' : status === 'starting' ? 'Starting...' : status === 'stopping' ? 'Stopping...' : 'Restarting...'}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {canStart && (
        <Button
          size="sm"
          variant="ghost"
          onClick={onStart}
          title={`Start ${serviceName}`}
          className="text-green-400 hover:text-green-300 hover:bg-green-400/10"
        >
          <Play className="w-4 h-4" />
        </Button>
      )}
      {canStop && (
        <Button
          size="sm"
          variant="ghost"
          onClick={onStop}
          title={`Stop ${serviceName}`}
          className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
        >
          <Square className="w-4 h-4" />
        </Button>
      )}
      {canRestart && (
        <Button
          size="sm"
          variant="ghost"
          onClick={onRestart}
          title={`Restart ${serviceName}`}
          className="text-yellow-400 hover:text-yellow-300 hover:bg-yellow-400/10"
        >
          <RotateCw className="w-4 h-4" />
        </Button>
      )}
    </div>
  );
}
