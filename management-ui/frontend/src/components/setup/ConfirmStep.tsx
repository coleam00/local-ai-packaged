import React from 'react';
import { Card } from '../common/Card';
import { Settings, Globe, Key, Layers, AlertTriangle, Terminal } from 'lucide-react';

interface ConfirmStepProps {
  config: {
    profile: string;
    environment: string;
    secrets: Record<string, string>;
    enabled_services: string[];
  };
}

const profileLabels: Record<string, string> = {
  cpu: 'CPU Only',
  'gpu-nvidia': 'NVIDIA GPU',
  'gpu-amd': 'AMD GPU',
  none: 'External Ollama',
};

const environmentLabels: Record<string, string> = {
  private: 'Private (localhost)',
  public: 'Public (HTTPS)',
};

export const ConfirmStep: React.FC<ConfirmStepProps> = ({ config }) => {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Confirm Setup</h3>
      <p className="text-gray-400 mb-6">
        Review your configuration before starting the stack.
      </p>

      <Card className="space-y-4">
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5 text-blue-400" />
          <div>
            <span className="text-gray-400 text-sm">Profile:</span>
            <span className="ml-2 font-medium text-white">
              {profileLabels[config.profile] || config.profile}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Globe className="w-5 h-5 text-green-400" />
          <div>
            <span className="text-gray-400 text-sm">Environment:</span>
            <span className="ml-2 font-medium text-white">
              {environmentLabels[config.environment] || config.environment}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Key className="w-5 h-5 text-purple-400" />
          <div>
            <span className="text-gray-400 text-sm">Secrets:</span>
            <span className="ml-2 font-medium text-white">
              {Object.keys(config.secrets).length} configured
            </span>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <Layers className="w-5 h-5 text-cyan-400" />
          <div>
            <span className="text-gray-400 text-sm">Services:</span>
            <span className="ml-2 font-medium text-white">
              {config.enabled_services.length} selected
            </span>
            {config.enabled_services.length > 0 && (
              <p className="text-xs text-gray-500 mt-1">
                {config.enabled_services.slice(0, 5).join(', ')}
                {config.enabled_services.length > 5 && ` +${config.enabled_services.length - 5} more`}
              </p>
            )}
          </div>
        </div>
      </Card>

      {/* CLI Requirement Info */}
      <div className="mt-6 bg-blue-900/30 border border-blue-700 rounded-lg p-4 flex items-start gap-3">
        <Terminal className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-blue-300 font-medium">Terminal required to start services</p>
          <p className="text-sm text-blue-400/80 mt-1">
            After saving configuration, you'll need to run a command in your terminal
            to start the services. This ensures proper file mounting and database initialization.
          </p>
        </div>
      </div>

      <div className="mt-4 bg-yellow-900/30 border border-yellow-700 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-yellow-300 font-medium">Before starting</p>
          <p className="text-sm text-yellow-400/80 mt-1">
            Make sure Docker is running and you have enough disk space and memory available.
          </p>
        </div>
      </div>
    </div>
  );
};
