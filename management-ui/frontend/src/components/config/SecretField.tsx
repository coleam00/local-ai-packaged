import { useState } from 'react';
import { Eye, EyeOff, Edit2, Check } from 'lucide-react';

interface SecretFieldProps {
  name: string;
  value: string;
  maskedValue: string;
  onChange: (value: string) => void;
  error?: string;
  description?: string;
}

export const SecretField: React.FC<SecretFieldProps> = ({
  name,
  value,
  maskedValue,
  onChange,
  error,
  description,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [showValue, setShowValue] = useState(false);

  const displayValue = isEditing ? value : maskedValue;

  return (
    <div className="mb-4">
      <label className="flex justify-between items-center mb-1">
        <span className="text-sm font-medium text-gray-300">{name}</span>
        {!isEditing && (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="flex items-center gap-1 text-blue-400 text-sm hover:text-blue-300"
          >
            <Edit2 className="w-3 h-3" />
            Edit
          </button>
        )}
      </label>

      {description && (
        <p className="text-xs text-gray-500 mb-2">{description}</p>
      )}

      <div className="relative">
        <input
          type={showValue ? 'text' : 'password'}
          value={displayValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={!isEditing}
          className={`w-full px-3 py-2 pr-24 bg-gray-800 border rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            error ? 'border-red-500' : 'border-gray-700'
          } ${!isEditing ? 'bg-gray-900 text-gray-400' : ''}`}
        />

        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
          {isEditing && (
            <>
              <button
                type="button"
                onClick={() => setShowValue(!showValue)}
                className="p-1 text-gray-400 hover:text-gray-300"
                title={showValue ? 'Hide value' : 'Show value'}
              >
                {showValue ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="p-1 text-green-400 hover:text-green-300"
                title="Done editing"
              >
                <Check className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {error && <p className="text-red-400 text-sm mt-1">{error}</p>}
    </div>
  );
};
