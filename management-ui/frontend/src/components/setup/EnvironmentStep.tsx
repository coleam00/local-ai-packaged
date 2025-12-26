import React from 'react';
import { Card } from '../common/Card';
import { Home, Globe } from 'lucide-react';

interface EnvironmentStepProps {
  value: string;
  onChange: (value: string) => void;
}

export const EnvironmentStep: React.FC<EnvironmentStepProps> = ({ value, onChange }) => {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Select Environment</h3>
      <p className="text-gray-400 mb-6">
        Choose how services will be accessible.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card
          className={`cursor-pointer transition-all ${
            value === 'private' ? 'ring-2 ring-blue-500 border-blue-500' : 'hover:border-gray-500'
          }`}
          onClick={() => onChange('private')}
        >
          <div className="flex items-start gap-3">
            <Home className="w-6 h-6 text-green-400 flex-shrink-0" />
            <div>
              <h4 className="font-medium text-white">Private (Recommended)</h4>
              <p className="text-sm text-gray-400 mt-1">
                Services bind to localhost only. Access via local ports.
                Best for development and personal use.
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Access: http://localhost:8001, :8002, etc.
              </p>
            </div>
          </div>
        </Card>

        <Card
          className={`cursor-pointer transition-all ${
            value === 'public' ? 'ring-2 ring-blue-500 border-blue-500' : 'hover:border-gray-500'
          }`}
          onClick={() => onChange('public')}
        >
          <div className="flex items-start gap-3">
            <Globe className="w-6 h-6 text-orange-400 flex-shrink-0" />
            <div>
              <h4 className="font-medium text-white">Public</h4>
              <p className="text-sm text-gray-400 mt-1">
                Services behind Caddy reverse proxy with HTTPS.
                Requires domain names and opens ports 80/443.
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Access: https://n8n.yourdomain.com, etc.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
