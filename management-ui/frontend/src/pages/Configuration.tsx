import { useEffect } from 'react';
import { Settings, AlertCircle, RefreshCw } from 'lucide-react';
import { useConfigStore } from '../store/configStore';
import { ConfigEditor } from '../components/config/ConfigEditor';
import { Loading } from '../components/common/Loading';
import { Button } from '../components/common/Button';

export const Configuration: React.FC = () => {
  const {
    fetchConfig,
    fetchBackups,
    isLoading,
    error,
    clearError,
  } = useConfigStore();

  useEffect(() => {
    // fetchConfig now fetches both masked and raw values
    const loadConfig = async () => {
      await fetchConfig();
      await fetchBackups();
    };
    loadConfig();
  }, [fetchConfig, fetchBackups]);

  if (isLoading) {
    return <Loading message="Loading configuration..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Settings className="w-7 h-7 text-slate-400" />
            Configuration
          </h2>
          <p className="text-slate-400 mt-1">
            Manage environment variables and secrets for your AI stack
          </p>
        </div>
        <button
          onClick={() => {
            fetchConfig();
            fetchBackups();
          }}
          className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400
                     hover:text-white hover:bg-[#1e293b] rounded-lg transition-colors
                     border border-[#374151] hover:border-[#4b5563]"
        >
          <RefreshCw className="w-4 h-4" />
          Reload
        </button>
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center justify-between p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <span className="text-red-400">{error}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearError}
            className="text-red-400 hover:text-red-300"
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Config Editor */}
      <ConfigEditor />
    </div>
  );
};
