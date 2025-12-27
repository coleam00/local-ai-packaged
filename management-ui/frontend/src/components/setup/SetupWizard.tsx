import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { ProfileStep } from './ProfileStep';
import { ServicesStep } from './ServicesStep';
import { EnvironmentStep } from './EnvironmentStep';
import { SecretsStep } from './SecretsStep';
import { ConfirmStep } from './ConfirmStep';
import { apiClient } from '../../api/client';
import { Check, ChevronLeft, ChevronRight, Rocket, AlertCircle, Loader2 } from 'lucide-react';

const STEPS = ['profile', 'services', 'environment', 'secrets', 'confirm'] as const;
const STEP_LABELS = ['Profile', 'Services', 'Environment', 'Secrets', 'Confirm'];

interface SetupConfig {
  profile: string;
  environment: string;
  secrets: Record<string, string>;
  enabled_services: string[];
}

interface SetupResult {
  status: string;
  current_step: string;
  steps: Array<{
    step: string;
    status: string;
    message?: string;
    error?: string;
  }>;
  message?: string;
  error?: string;
}

export const SetupWizard: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [setupResult, setSetupResult] = useState<SetupResult | null>(null);
  const [config, setConfig] = useState<SetupConfig>({
    profile: 'cpu',
    environment: 'private',
    secrets: {},
    enabled_services: [],
  });

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await apiClient.post<SetupResult>('/setup/complete', config);
      setSetupResult(response.data);

      if (response.data.status === 'completed') {
        // Wait a moment then navigate
        setTimeout(() => navigate('/'), 2000);
      } else {
        setError(response.data.error || 'Setup failed');
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail || 'Setup failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const canProceed = () => {
    switch (STEPS[currentStep]) {
      case 'services':
        return config.enabled_services.length > 0 || true; // Allow proceeding with defaults
      case 'secrets':
        return Object.keys(config.secrets).length > 0;
      default:
        return true;
    }
  };

  const renderStep = () => {
    switch (STEPS[currentStep]) {
      case 'profile':
        return (
          <ProfileStep
            value={config.profile}
            onChange={(profile) => setConfig({ ...config, profile })}
          />
        );
      case 'services':
        return (
          <ServicesStep
            profile={config.profile}
            value={config.enabled_services}
            onChange={(enabled_services) => setConfig({ ...config, enabled_services })}
          />
        );
      case 'environment':
        return (
          <EnvironmentStep
            value={config.environment}
            onChange={(environment) => setConfig({ ...config, environment })}
          />
        );
      case 'secrets':
        return (
          <SecretsStep
            secrets={config.secrets}
            onChange={(secrets) => setConfig({ ...config, secrets })}
          />
        );
      case 'confirm':
        return <ConfirmStep config={config} />;
      default:
        return null;
    }
  };

  // Show progress during setup
  if (isSubmitting || setupResult) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="text-center py-8">
          {setupResult?.status === 'completed' ? (
            <>
              <Check className="w-16 h-16 text-green-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">Setup Complete!</h3>
              <p className="text-gray-400">
                {setupResult.message || 'Your stack is now starting...'}
              </p>
              <p className="text-sm text-gray-500 mt-4">Redirecting to dashboard...</p>
            </>
          ) : setupResult?.status === 'failed' ? (
            <>
              <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">Setup Failed</h3>
              <p className="text-red-400 mb-4">{setupResult.error}</p>
              <Button variant="secondary" onClick={() => setSetupResult(null)}>
                Try Again
              </Button>
            </>
          ) : (
            <>
              <Loader2 className="w-16 h-16 text-blue-400 mx-auto mb-4 animate-spin" />
              <h3 className="text-xl font-semibold text-white mb-2">Setting Up...</h3>
              <p className="text-gray-400">This may take a few minutes.</p>
              <div className="mt-6 text-left space-y-2">
                {['Cloning Supabase repository...', 'Preparing environment...', 'Generating secrets...', 'Starting services...'].map((step, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-gray-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress Indicator */}
      <div className="flex justify-center mb-8">
        {STEPS.map((step, index) => (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                  index < currentStep
                    ? 'bg-green-600 text-white'
                    : index === currentStep
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                {index < currentStep ? (
                  <Check className="w-5 h-5" />
                ) : (
                  index + 1
                )}
              </div>
              <span className={`text-xs mt-1 ${
                index === currentStep ? 'text-white' : 'text-gray-500'
              }`}>
                {STEP_LABELS[index]}
              </span>
            </div>
            {index < STEPS.length - 1 && (
              <div
                className={`w-12 md:w-20 h-0.5 mx-2 transition-colors ${
                  index < currentStep ? 'bg-green-600' : 'bg-gray-700'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <Card className="mb-6">{renderStep()}</Card>

      {/* Error Display */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-400 px-4 py-3 rounded-lg mb-4 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Navigation Actions */}
      <div className="flex justify-between">
        <Button
          variant="ghost"
          onClick={handleBack}
          disabled={currentStep === 0 || isSubmitting}
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Back
        </Button>

        {currentStep < STEPS.length - 1 ? (
          <Button onClick={handleNext} disabled={!canProceed()}>
            Next
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        ) : (
          <Button onClick={handleComplete} isLoading={isSubmitting} disabled={!canProceed()}>
            <Rocket className="w-4 h-4 mr-2" />
            Start Stack
          </Button>
        )}
      </div>
    </div>
  );
};
