import React, { useEffect, useState } from 'react';
import { setupApi } from '../../api/setup';
import type { PreflightCheck } from '../../api/setup';
import { CheckCircle, AlertTriangle, XCircle, Loader2, Wrench } from 'lucide-react';
import { Button } from '../common/Button';

interface PreflightStepProps {
  onReady: (ready: boolean) => void;
}

export const PreflightStep: React.FC<PreflightStepProps> = ({ onReady }) => {
  const [check, setCheck] = useState<PreflightCheck | null>(null);
  const [loading, setLoading] = useState(true);
  const [fixing, setFixing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await setupApi.preflightCheck();
      setCheck(result);
      onReady(result.can_proceed && result.issues.length === 0);
    } catch (e) {
      setError('Failed to run preflight check');
      onReady(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runCheck();
  }, []);

  const handleFix = async (fixType: string) => {
    setFixing(fixType);
    try {
      const result = await setupApi.fixPreflightIssue(fixType);
      if (result.success) {
        // Re-run check after fix
        await runCheck();
      } else {
        setError(result.message);
      }
    } catch (e) {
      setError('Failed to apply fix');
    } finally {
      setFixing(null);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-blue-400 animate-spin mb-4" />
        <p className="text-gray-400">Checking environment...</p>
      </div>
    );
  }

  const hasIssues = check && check.issues.length > 0;
  const hasWarnings = check && check.warnings.length > 0;
  const allClear = check && !hasIssues && !hasWarnings;

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Environment Check</h3>
      <p className="text-gray-400 mb-6">
        Checking your system before setup...
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {allClear && (
        <div className="flex items-center gap-3 p-4 bg-green-900/20 border border-green-700/50 rounded-lg mb-4">
          <CheckCircle className="w-6 h-6 text-green-400" />
          <div>
            <p className="font-medium text-green-400">All checks passed</p>
            <p className="text-sm text-green-400/70">Your environment is ready for setup</p>
          </div>
        </div>
      )}

      {hasIssues && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-red-400 mb-2 flex items-center gap-2">
            <XCircle className="w-4 h-4" />
            Issues (must fix before proceeding)
          </h4>
          <div className="space-y-2">
            {check.issues.map((issue, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 bg-red-900/20 border border-red-700/50 rounded-lg"
              >
                <span className="text-red-300">{issue.message}</span>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleFix(issue.fix)}
                  isLoading={fixing === issue.fix}
                  disabled={fixing !== null}
                >
                  <Wrench className="w-4 h-4 mr-1" />
                  Fix
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasWarnings && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-yellow-400 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Warnings (optional to fix)
          </h4>
          <div className="space-y-2">
            {check.warnings.map((warning, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 bg-yellow-900/20 border border-yellow-700/50 rounded-lg"
              >
                <span className="text-yellow-300">{warning.message}</span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleFix(warning.fix)}
                  isLoading={fixing === warning.fix}
                  disabled={fixing !== null}
                >
                  <Wrench className="w-4 h-4 mr-1" />
                  Fix
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-6 flex justify-end">
        <Button variant="ghost" onClick={runCheck} disabled={loading}>
          Re-check
        </Button>
      </div>
    </div>
  );
};
