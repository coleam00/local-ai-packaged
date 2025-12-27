import {
  ChevronDown,
  ChevronRight,
  Play,
  Square,
  Loader2,
  Layers,
} from 'lucide-react';
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
  const someRunning =
    group.running_count > 0 && group.running_count < group.total_count;

  // Progress calculation
  const progress =
    group.total_count > 0
      ? (group.running_count / group.total_count) * 100
      : 0;

  return (
    <div className="bg-[#1e293b]/50 rounded-[12px] border border-[#374151] overflow-hidden">
      {/* Group header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-[#1e293b] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <button className="p-1 hover:bg-[#374151] rounded transition-colors">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            )}
          </button>

          <div className="p-2 bg-[#374151] rounded-lg">
            <Layers className="w-5 h-5 text-purple-400" />
          </div>

          <div>
            <h3 className="font-medium text-white">{group.name}</h3>
            <p className="text-sm text-slate-500">{group.description}</p>
          </div>
        </div>

        <div
          className="flex items-center gap-4"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Progress bar & status */}
          <div className="flex items-center gap-3">
            <div className="w-24 h-1.5 bg-[#374151] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  allRunning
                    ? 'bg-emerald-500'
                    : allStopped
                    ? 'bg-slate-600'
                    : 'bg-amber-500'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-sm text-slate-400 tabular-nums">
              {group.running_count}/{group.total_count}
            </span>
          </div>

          {/* Group actions */}
          {isActionInProgress ? (
            <div className="flex items-center gap-2 text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-xs">Processing...</span>
            </div>
          ) : (
            <div className="flex items-center gap-1">
              {!allRunning && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onStartGroup}
                  title={`Start all ${group.name} services`}
                  className="text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10"
                >
                  <Play className="w-4 h-4" />
                  <span className="ml-1.5 text-xs">Start All</span>
                </Button>
              )}
              {someRunning || allRunning ? (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onStopGroup}
                  title={`Stop all ${group.name} services`}
                  className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                >
                  <Square className="w-4 h-4" />
                  <span className="ml-1.5 text-xs">Stop All</span>
                </Button>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="p-4 pt-0 border-t border-[#374151]">{children}</div>
      )}
    </div>
  );
}
