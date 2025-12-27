import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  hint,
  className = '',
  ...props
}) => {
  return (
    <div className="mb-4">
      {label && (
        <label className="block text-sm font-medium text-slate-400 mb-1.5">
          {label}
        </label>
      )}
      <input
        className={`w-full px-3 py-2.5 bg-[#2d3748] border rounded-md
                   text-white placeholder-slate-500 text-sm
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   transition-colors
                   ${error ? 'border-red-500' : 'border-[#374151]'}
                   ${className}`}
        {...props}
      />
      {hint && !error && (
        <p className="text-slate-500 text-xs mt-1.5">{hint}</p>
      )}
      {error && <p className="text-red-400 text-xs mt-1.5">{error}</p>}
    </div>
  );
};
