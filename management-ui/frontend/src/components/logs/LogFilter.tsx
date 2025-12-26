import { Search } from 'lucide-react';

interface LogFilterProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  autoScroll: boolean;
  onAutoScrollChange: (enabled: boolean) => void;
}

export const LogFilter: React.FC<LogFilterProps> = ({
  searchTerm,
  onSearchChange,
  autoScroll,
  onAutoScrollChange,
}) => {
  return (
    <div className="flex gap-4 items-center">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Filter logs..."
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
      <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
        <input
          type="checkbox"
          checked={autoScroll}
          onChange={(e) => onAutoScrollChange(e.target.checked)}
          className="w-4 h-4 rounded bg-gray-700 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
        />
        Auto-scroll
      </label>
    </div>
  );
};
