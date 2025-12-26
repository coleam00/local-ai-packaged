import { RefreshCw, RotateCcw, Clock } from 'lucide-react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import type { BackupInfo } from '../../types/config';

interface BackupManagerProps {
  backups: BackupInfo[];
  onRestore: (filename: string) => void;
  onRefresh: () => void;
  isRestoring?: boolean;
}

export const BackupManager: React.FC<BackupManagerProps> = ({
  backups,
  onRestore,
  onRefresh,
  isRestoring = false,
}) => {
  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold text-white flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400" />
          Backups
        </h4>
        <Button
          variant="ghost"
          size="sm"
          onClick={onRefresh}
          className="text-gray-400 hover:text-white"
        >
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      <p className="text-sm text-gray-400 mb-4">
        {backups.length} backup{backups.length !== 1 ? 's' : ''} available
      </p>

      {backups.length === 0 ? (
        <p className="text-gray-500 text-sm text-center py-4">No backups yet</p>
      ) : (
        <ul className="space-y-2 max-h-60 overflow-y-auto">
          {backups.map((backup) => (
            <li
              key={backup.filename}
              className="flex justify-between items-center p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <div>
                <p className="text-sm font-medium text-white">{backup.filename}</p>
                <p className="text-xs text-gray-500">{formatDate(backup.created)}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onRestore(backup.filename)}
                disabled={isRestoring}
                className="text-blue-400 hover:text-blue-300"
                title="Restore this backup"
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
};
