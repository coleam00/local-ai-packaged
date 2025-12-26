import { useEffect, useRef, useMemo } from 'react';
import { Terminal } from 'lucide-react';

interface LogStreamProps {
  logs: string[];
  searchTerm: string;
  autoScroll: boolean;
}

export const LogStream: React.FC<LogStreamProps> = ({ logs, searchTerm, autoScroll }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  const filteredLogs = useMemo(() => {
    if (!searchTerm) return logs;
    const term = searchTerm.toLowerCase();
    return logs.filter((log) => log.toLowerCase().includes(term));
  }, [logs, searchTerm]);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const highlightMatch = (text: string, index: number) => {
    if (!searchTerm) return text;

    try {
      const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      const parts = text.split(regex);

      return parts.map((part, i) =>
        part.toLowerCase() === searchTerm.toLowerCase() ? (
          <mark key={`${index}-${i}`} className="bg-yellow-500/40 text-yellow-200 rounded px-0.5">
            {part}
          </mark>
        ) : (
          part
        )
      );
    } catch {
      return text;
    }
  };

  // Color log levels
  const getLogColor = (log: string) => {
    const lowerLog = log.toLowerCase();
    if (lowerLog.includes('error') || lowerLog.includes('fatal')) {
      return 'text-red-400';
    }
    if (lowerLog.includes('warn')) {
      return 'text-yellow-400';
    }
    if (lowerLog.includes('info')) {
      return 'text-blue-400';
    }
    if (lowerLog.includes('debug')) {
      return 'text-gray-500';
    }
    return 'text-gray-300';
  };

  return (
    <div
      ref={containerRef}
      className="bg-gray-950 border border-gray-800 text-gray-100 font-mono text-sm p-4 rounded-lg h-[500px] overflow-y-auto"
    >
      {filteredLogs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <Terminal className="w-12 h-12 mb-4 opacity-50" />
          <p>No logs available</p>
          {searchTerm && <p className="text-sm mt-1">Try adjusting your filter</p>}
        </div>
      ) : (
        <div className="space-y-0.5">
          {filteredLogs.map((log, index) => (
            <div
              key={index}
              className={`py-0.5 px-1 hover:bg-gray-900 rounded whitespace-pre-wrap break-all ${getLogColor(log)}`}
            >
              <span className="text-gray-600 select-none mr-2">{(index + 1).toString().padStart(4, ' ')}</span>
              {highlightMatch(log, index)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
