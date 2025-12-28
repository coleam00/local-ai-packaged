import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { PreflightStep } from './PreflightStep';
import { ProfileStep } from './ProfileStep';
import { ServicesStep } from './ServicesStep';
import { PortsStep } from './PortsStep';
import { EnvironmentStep } from './EnvironmentStep';
import { SecretsStep } from './SecretsStep';
import { ConfirmStep } from './ConfirmStep';
import { apiClient } from '../../api/client';
import { useAuthStore } from '../../store/authStore';
import { Check, ChevronLeft, ChevronRight, Rocket, AlertCircle, Loader2, Clock } from 'lucide-react';

const STEPS = ['preflight', 'profile', 'services', 'ports', 'environment', 'secrets', 'confirm'] as const;
const STEP_LABELS = ['Check', 'Profile', 'Services', 'Ports', 'Environment', 'Secrets', 'Confirm'];

interface SetupConfig {
  profile: string;
  environment: string;
  secrets: Record<string, string>;
  enabled_services: string[];
  port_overrides: Record<string, Record<string, number>>;
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
  const { checkSetupStatus } = useAuthStore();
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [setupResult, setSetupResult] = useState<SetupResult | null>(null);
  const [preflightReady, setPreflightReady] = useState(false);
  const [portsReady, setPortsReady] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [config, setConfig] = useState<SetupConfig>({
    profile: 'cpu',
    environment: 'private',
    secrets: {},
    enabled_services: [],
    port_overrides: {},
  });

  // Elapsed time counter during setup
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (isSubmitting && !setupResult) {
      setElapsedTime(0);
      interval = setInterval(() => {
        setElapsedTime(t => t + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isSubmitting, setupResult]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  const handleNext = () => {
    let nextStep = currentStep + 1;
    // Skip ports step for public environment
    if (STEPS[nextStep] === 'ports' && config.environment === 'public') {
      nextStep++;
    }
    if (nextStep < STEPS.length) {
      setCurrentStep(nextStep);
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
        // Refresh status so App knows stack is configured, then navigate
        setTimeout(async () => {
          await checkSetupStatus();
          navigate('/');
        }, 2000);
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
      case 'preflight':
        return preflightReady;
      case 'services':
        return config.enabled_services.length > 0 || true; // Allow proceeding with defaults
      case 'ports':
        return portsReady;
      case 'secrets':
        return Object.keys(config.secrets).length > 0;
      default:
        return true;
    }
  };

  const renderStep = () => {
    switch (STEPS[currentStep]) {
      case 'preflight':
        return <PreflightStep onReady={setPreflightReady} />;
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
      case 'ports':
        return (
          <PortsStep
            enabledServices={config.enabled_services}
            profile={config.profile}
            value={config.port_overrides}
            onChange={(port_overrides) => setConfig({ ...config, port_overrides })}
            onReady={setPortsReady}
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
              <h3 className="text-xl font-semibold text-white mb-2">Setting Up Your Stack...</h3>

              <div className="flex items-center justify-center gap-2 text-gray-400 mb-4">
                <Clock className="w-4 h-4" />
                <span>Elapsed: {formatTime(elapsedTime)}</span>
              </div>

              <p className="text-gray-400 mb-2">This typically takes 2-5 minutes.</p>
              <p className="text-sm text-gray-500 mb-6">
                We're downloading dependencies, configuring services, and starting containers.
              </p>

              <div className="mt-4 text-left space-y-3 max-w-md mx-auto">
                {[
                  { step: 'clone_supabase', label: 'Cloning Supabase repository', desc: 'Downloading backend services' },
                  { step: 'prepare_env', label: 'Preparing environment', desc: 'Configuring secrets and settings' },
                  { step: 'searxng_secret', label: 'Configuring SearXNG', desc: 'Setting up search engine' },
                  { step: 'start_stack', label: 'Starting services', desc: 'Launching Docker containers (this takes the longest)' },
                ].map((item, i) => {
                  const stepResult = setupResult?.steps?.find(s => s.step === item.step);
                  const isComplete = stepResult?.status === 'completed';
                  const isFailed = stepResult?.status === 'failed';
                  const isActive = !stepResult && i === (setupResult?.steps?.length || 0);

                  return (
                    <div key={item.step} className={`flex items-start gap-3 p-2 rounded ${isActive ? 'bg-blue-900/20' : ''}`}>
                      <div className="mt-0.5">
                        {isComplete ? (
                          <Check className="w-5 h-5 text-green-400" />
                        ) : isFailed ? (
                          <AlertCircle className="w-5 h-5 text-red-400" />
                        ) : isActive ? (
                          <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                        ) : (
                          <div className="w-5 h-5 rounded-full border-2 border-gray-600" />
                        )}
                      </div>
                      <div>
                        <p className={`text-sm font-medium ${isComplete ? 'text-green-400' : isFailed ? 'text-red-400' : isActive ? 'text-blue-400' : 'text-gray-500'}`}>
                          {item.label}
                        </p>
                        <p className="text-xs text-gray-500">{item.desc}</p>
                        {stepResult?.message && (
                          <p className="text-xs text-gray-400 mt-1">{stepResult.message}</p>
                        )}
                        {stepResult?.error && (
                          <p className="text-xs text-red-400 mt-1">{stepResult.error}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {elapsedTime > 300 && (
                <p className="text-yellow-400 text-sm mt-6">
                  This is taking longer than expected. Check your Docker installation and network connection.
                </p>
              )}
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
