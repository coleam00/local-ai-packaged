import React from 'react';
import { SetupWizard } from '../components/setup/SetupWizard';
import { Box } from 'lucide-react';

export const SetupWizardPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-900 py-12 px-4">
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Box className="w-10 h-10 text-blue-400" />
          <h1 className="text-3xl font-bold text-white">Stack Setup</h1>
        </div>
        <p className="text-gray-400">
          Configure and start your local AI stack
        </p>
      </div>

      <SetupWizard />
    </div>
  );
};
