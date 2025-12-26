import { FileText } from 'lucide-react';
import { LogViewer } from '../components/logs/LogViewer';

export const Logs: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <FileText className="w-7 h-7 text-gray-400" />
          Logs
        </h2>
        <p className="text-gray-400 mt-1">
          View real-time container logs with streaming updates
        </p>
      </div>

      {/* Log Viewer */}
      <LogViewer />
    </div>
  );
};
