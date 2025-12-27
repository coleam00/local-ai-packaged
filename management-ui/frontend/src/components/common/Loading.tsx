import React from 'react';
import { Box } from 'lucide-react';

export const Loading: React.FC<{ message?: string }> = ({
  message = 'Loading...',
}) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#121827]">
      <div className="relative">
        {/* Spinning ring */}
        <svg
          className="animate-spin h-12 w-12 text-blue-500"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        {/* Center icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <Box className="w-5 h-5 text-blue-400" />
        </div>
      </div>
      <p className="text-slate-400 mt-4 text-sm">{message}</p>
    </div>
  );
};
