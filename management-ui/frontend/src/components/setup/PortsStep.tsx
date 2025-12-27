import React, { useEffect, useState } from 'react';
import { setupApi } from '../../api/setup';
import type { PortCheckResponse, ServicePortScan } from '../../api/setup';
import { CheckCircle, AlertTriangle, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '../common/Button';

interface PortsStepProps {
  enabledServices: string[];
  value: Record<string, Record<string, number>>;  // service -> port_name -> port
  onChange: (ports: Record<string, Record<string, number>>) => void;
  onReady: (ready: boolean) => void;
}

export const PortsStep: React.FC<PortsStepProps> = ({
  enabledServices,
  value,
  onChange,
  onReady
}) => {
  const [check, setCheck] = useState<PortCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<Record<string, boolean>>({});

  const runCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await setupApi.checkPorts(enabledServices);
      setCheck(result);

      // Initialize with suggested ports
      const initialPorts: Record<string, Record<string, number>> = {};
      for (const service of result.services) {
        initialPorts[service.service_name] = service.suggested_ports;
      }
      onChange(initialPorts);
      onReady(true);
    } catch (e) {
      setError('Failed to check port availability');
      onReady(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runCheck();
  }, [enabledServices.join(',')]);

  const handlePortChange = (serviceName: string, portName: string, newPort: number) => {
    onChange({
      ...value,
      [serviceName]: {
        ...(value[serviceName] || {}),
        [portName]: newPort
      }
    });
  };

  const handleAcceptSuggestions = (service: ServicePortScan) => {
    onChange({
      ...value,
      [service.service_name]: service.suggested_ports
    });
    setEditMode({ ...editMode, [service.service_name]: false });
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-blue-400 animate-spin mb-4" />
        <p className="text-gray-400">Checking port availability...</p>
      </div>
    );
  }

  const hasConflicts = check?.has_conflicts ?? false;

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Port Configuration</h3>
      <p className="text-gray-400 mb-6">
        {hasConflicts
          ? 'Some ports are in use. Review the suggestions below or specify custom ports.'
          : 'All default ports are available. You can customize them if needed.'}
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {!hasConflicts && (
        <div className="flex items-center gap-3 p-4 bg-green-900/20 border border-green-700/50 rounded-lg mb-4">
          <CheckCircle className="w-6 h-6 text-green-400" />
          <div>
            <p className="font-medium text-green-400">All ports available</p>
            <p className="text-sm text-green-400/70">
              {check?.total_ports_checked} ports checked, no conflicts found
            </p>
          </div>
        </div>
      )}

      {hasConflicts && (
        <div className="flex items-center gap-3 p-4 bg-yellow-900/20 border border-yellow-700/50 rounded-lg mb-4">
          <AlertTriangle className="w-6 h-6 text-yellow-400" />
          <div>
            <p className="font-medium text-yellow-400">Port conflicts detected</p>
            <p className="text-sm text-yellow-400/70">
              {check?.conflicts_count} port(s) need alternative configuration
            </p>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {check?.services.map((service) => (
          <div
            key={service.service_name}
            className={`p-4 rounded-lg border ${
              service.all_available
                ? 'bg-gray-800/50 border-gray-700'
                : 'bg-yellow-900/10 border-yellow-700/50'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {service.all_available ? (
                  <CheckCircle className="w-5 h-5 text-green-400" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-yellow-400" />
                )}
                <span className="font-medium text-white">{service.display_name}</span>
              </div>
              {!service.all_available && !editMode[service.service_name] && (
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => handleAcceptSuggestions(service)}
                  >
                    Accept Suggestions
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setEditMode({ ...editMode, [service.service_name]: true })}
                  >
                    Customize
                  </Button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(service.ports).map(([portName, status]) => {
                const currentPort = value[service.service_name]?.[portName] ?? status.port;
                const isEditing = editMode[service.service_name];

                return (
                  <div key={portName} className="flex items-center gap-2">
                    <span className="text-sm text-gray-400 w-20 capitalize">{portName}:</span>
                    {isEditing ? (
                      <input
                        type="number"
                        value={currentPort}
                        onChange={(e) => handlePortChange(
                          service.service_name,
                          portName,
                          parseInt(e.target.value) || 0
                        )}
                        className="w-24 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                        min="1025"
                        max="65535"
                      />
                    ) : (
                      <span className={`text-sm ${
                        status.available ? 'text-gray-300' : 'text-yellow-400'
                      }`}>
                        {status.available ? (
                          status.port
                        ) : (
                          <>
                            <span className="line-through">{status.port}</span>
                            {' -> '}
                            <span className="text-green-400">
                              {service.suggested_ports[portName]}
                            </span>
                          </>
                        )}
                      </span>
                    )}
                    {!status.available && !isEditing && (
                      <span className="text-xs text-gray-500">
                        (used by {status.used_by})
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 flex justify-end">
        <Button variant="ghost" onClick={runCheck} disabled={loading}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Re-scan
        </Button>
      </div>
    </div>
  );
};
