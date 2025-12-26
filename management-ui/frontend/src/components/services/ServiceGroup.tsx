import { ChevronDown, ChevronRight, Play, Square, Loader2, Layers } from 'lucide-react';
import { useState } from 'react';
import { Button } from '../common/Button';
import type { ServiceGroup as ServiceGroupType } from '../../types/service';

interface ServiceGroupProps {
  group: ServiceGroupType;
  isActionInProgress: boolean;
  onStartGroup: () => void;
  onStopGroup: () => void;
  children: React.ReactNode;
}

export function ServiceGroup({
  group,
  isActionInProgress,
  onStartGroup,
  onStopGroup,
  children,
}: ServiceGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const allRunning = group.running_count === group.total_count;
  const allStopped = group.running_count === 0;
  const someRunning = group.running_count > 0 && group.running_count < group.total_count;

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700 overflow-hidden">
      {/* Group header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-800 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <button className="p-1 hover:bg-gray-700 rounded">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          <div className="p-2 bg-gray-700 rounded-lg">
            <Layers className="w-5 h-5 text-purple-400" />
          </div>

          <div>
            <h3 className="font-medium text-white">{group.name}</h3>
            <p className="text-sm text-gray-400">{group.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-4" onClick={(e) => e.stopPropagation()}>
          {/* Status indicator */}
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                allRunning
                  ? 'bg-green-500'
                  : allStopped
                  ? 'bg-gray-500'
                  : 'bg-yellow-500'
              }`}
            />
            <span className="text-sm text-gray-400">
              {group.running_count}/{group.total_count}
            </span>
          </div>

          {/* Group actions */}
          {isActionInProgress ? (
            <div className="flex items-center gap-2 text-gray-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Processing...</span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {!allRunning && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onStartGroup}
                  title={`Start all ${group.name} services`}
                  className="text-green-400 hover:text-green-300 hover:bg-green-400/10"
                >
                  <Play className="w-4 h-4" />
                  <span className="ml-1">Start All</span>
                </Button>
              )}
              {someRunning || allRunning ? (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onStopGroup}
                  title={`Stop all ${group.name} services`}
                  className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
                >
                  <Square className="w-4 h-4" />
                  <span className="ml-1">Stop All</span>
                </Button>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="p-4 pt-0 border-t border-gray-700">
          {children}
        </div>
      )}
    </div>
  );
}
