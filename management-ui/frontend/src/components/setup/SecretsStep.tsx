import React, { useState } from 'react';
import { Button } from '../common/Button';
import { apiClient } from '../../api/client';
import { Key, Check, AlertCircle } from 'lucide-react';

interface SecretsStepProps {
  secrets: Record<string, string>;
  onChange: (secrets: Record<string, string>) => void;
}

export const SecretsStep: React.FC<SecretsStepProps> = ({ secrets, onChange }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generated, setGenerated] = useState(Object.keys(secrets).length > 0);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const response = await apiClient.post('/setup/generate-secrets');
      onChange(response.data.secrets);
      setGenerated(true);
    } catch (e) {
      console.error('Failed to generate secrets:', e);
      setError('Failed to generate secrets. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const secretCount = Object.keys(secrets).length;

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Generate Secrets</h3>
      <p className="text-gray-400 mb-6">
        Secure secrets are required for encryption and authentication.
        We'll generate cryptographically secure values for you.
      </p>

      <div className="bg-gray-800 rounded-lg p-6 text-center border border-gray-700">
        {!generated ? (
          <>
            <Key className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-300 mb-4">Click to generate all required secrets:</p>
            <Button onClick={handleGenerate} isLoading={isGenerating}>
              Generate Secrets
            </Button>
            {error && (
              <div className="flex items-center gap-2 text-red-400 mt-4 justify-center">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">{error}</span>
              </div>
            )}
          </>
        ) : (
          <>
            <Check className="w-12 h-12 text-green-400 mx-auto mb-4" />
            <p className="text-green-400 font-medium mb-2">
              {secretCount} secrets generated successfully!
            </p>
            <p className="text-sm text-gray-400">
              These will be saved to your .env file.
            </p>

            <div className="mt-4 text-left bg-gray-900 rounded p-3 max-h-40 overflow-y-auto border border-gray-700">
              {Object.keys(secrets).slice(0, 5).map((key) => (
                <div key={key} className="text-xs font-mono text-gray-400 py-0.5">
                  {key}: ****{secrets[key].slice(-8)}
                </div>
              ))}
              {secretCount > 5 && (
                <div className="text-xs text-gray-500 mt-1 pt-1 border-t border-gray-700">
                  ...and {secretCount - 5} more
                </div>
              )}
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleGenerate}
              isLoading={isGenerating}
              className="mt-4"
            >
              Regenerate
            </Button>
          </>
        )}
      </div>
    </div>
  );
};
