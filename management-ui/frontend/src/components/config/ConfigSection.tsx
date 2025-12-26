import { ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { Card } from '../common/Card';
import { SecretField } from './SecretField';
import type { ConfigSchema, ValidationError } from '../../types/config';

interface ConfigSectionProps {
  title: string;
  variables: string[];
  config: Record<string, string>;
  maskedConfig: Record<string, string>;
  schema: ConfigSchema;
  errors: ValidationError[];
  onChange: (key: string, value: string) => void;
}

export const ConfigSection: React.FC<ConfigSectionProps> = ({
  title,
  variables,
  config,
  maskedConfig,
  schema,
  errors,
  onChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const getError = (varName: string) => {
    const error = errors.find((e) => e.variable === varName);
    return error?.message;
  };

  const sectionErrors = variables.filter((v) => getError(v)).length;

  return (
    <Card className="mb-4">
      <div
        className="flex items-center justify-between cursor-pointer -m-4 p-4 hover:bg-gray-700/50 rounded-t-lg"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
          <h3 className="font-semibold text-white">{title}</h3>
          <span className="text-sm text-gray-500">({variables.length} variables)</span>
        </div>
        {sectionErrors > 0 && (
          <span className="px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded">
            {sectionErrors} error{sectionErrors > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          {variables.map((varName) => {
            const schemaInfo = schema[varName] || {};
            const isSecret = schemaInfo.is_secret;
            const value = config[varName] || '';
            const maskedValue = maskedConfig[varName] || '';
            const error = getError(varName);

            if (isSecret) {
              return (
                <SecretField
                  key={varName}
                  name={varName}
                  value={value}
                  maskedValue={maskedValue}
                  onChange={(v) => onChange(varName, v)}
                  error={error}
                  description={schemaInfo.description}
                />
              );
            }

            return (
              <div key={varName} className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  {varName}
                  {schemaInfo.is_required && (
                    <span className="text-red-400 ml-1">*</span>
                  )}
                </label>
                {schemaInfo.description && (
                  <p className="text-xs text-gray-500 mb-2">{schemaInfo.description}</p>
                )}
                <input
                  type="text"
                  value={value}
                  onChange={(e) => onChange(varName, e.target.value)}
                  className={`w-full px-3 py-2 bg-gray-800 border rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    error ? 'border-red-500' : 'border-gray-700'
                  }`}
                />
                {error && <p className="text-red-400 text-sm mt-1">{error}</p>}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
