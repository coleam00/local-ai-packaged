import { useEffect } from 'react';
import { Settings, AlertCircle, RefreshCw } from 'lucide-react';
import { useConfigStore } from '../store/configStore';
import { ConfigEditor } from '../components/config/ConfigEditor';
import { Loading } from '../components/common/Loading';
import { Button } from '../components/common/Button';

export const Configuration: React.FC = () => {
  const {
    fetchConfig,
    fetchRawConfig,
    fetchBackups,
    isLoading,
    error,
    clearError,
  } = useConfigStore();

  useEffect(() => {
    // First fetch masked config, then get raw values
    const loadConfig = async () => {
      await fetchConfig();
      await fetchRawConfig();
      await fetchBackups();
    };
    loadConfig();
  }, [fetchConfig, fetchRawConfig, fetchBackups]);

  if (isLoading) {
    return <Loading message="Loading configuration..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Settings className="w-7 h-7 text-gray-400" />
            Configuration
          </h2>
          <p className="text-gray-400 mt-1">
            Manage environment variables and secrets for your AI stack
          </p>
        </div>
        <Button
          variant="ghost"
          onClick={() => {
            fetchConfig();
            fetchRawConfig();
            fetchBackups();
          }}
          className="text-gray-400 hover:text-white"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Reload
        </Button>
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center justify-between p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <span className="text-red-400">{error}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={clearError} className="text-red-400">
            Dismiss
          </Button>
        </div>
      )}

      {/* Config Editor */}
      <ConfigEditor />
    </div>
  );
};
