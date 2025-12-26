import React from 'react';
import { Card } from '../common/Card';
import { Cpu, Monitor, Zap, Globe } from 'lucide-react';

interface ProfileStepProps {
  value: string;
  onChange: (value: string) => void;
}

const profiles = [
  {
    id: 'cpu',
    name: 'CPU Only',
    description: 'Run Ollama on CPU. Works everywhere but slower inference.',
    Icon: Cpu,
    color: 'text-blue-400',
  },
  {
    id: 'gpu-nvidia',
    name: 'NVIDIA GPU',
    description: 'Use NVIDIA CUDA for fast inference. Requires NVIDIA GPU.',
    Icon: Zap,
    color: 'text-green-400',
  },
  {
    id: 'gpu-amd',
    name: 'AMD GPU',
    description: 'Use AMD ROCm for inference. Requires AMD GPU.',
    Icon: Monitor,
    color: 'text-red-400',
  },
  {
    id: 'none',
    name: 'External Ollama',
    description: 'Use an external Ollama instance. Skip local Ollama.',
    Icon: Globe,
    color: 'text-purple-400',
  },
];

export const ProfileStep: React.FC<ProfileStepProps> = ({ value, onChange }) => {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Select Hardware Profile</h3>
      <p className="text-gray-400 mb-6">
        Choose how you want to run the local AI models.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {profiles.map((profile) => {
          const Icon = profile.Icon;
          const isSelected = value === profile.id;
          return (
            <Card
              key={profile.id}
              className={`cursor-pointer transition-all ${
                isSelected
                  ? 'ring-2 ring-blue-500 border-blue-500'
                  : 'hover:border-gray-500'
              }`}
              onClick={() => onChange(profile.id)}
            >
              <div className="flex items-start gap-3">
                <Icon className={`w-6 h-6 ${profile.color} flex-shrink-0`} />
                <div>
                  <h4 className="font-medium text-white">{profile.name}</h4>
                  <p className="text-sm text-gray-400 mt-1">{profile.description}</p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
