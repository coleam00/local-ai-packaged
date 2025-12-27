import React, { useEffect, useState, useMemo } from 'react';
import { setupApi } from '../../api/setup';
import type { ServiceInfo, SelectionValidation } from '../../api/setup';
import {
  Check, AlertTriangle, Info, ChevronDown, ChevronRight,
  Database, Brain, Workflow, Server, BarChart3, Layers
} from 'lucide-react';

interface ServicesStepProps {
  profile: string;
  value: string[];
  onChange: (value: string[]) => void;
}

const groupIcons: Record<string, React.ElementType> = {
  supabase: Database,
  core_ai: Brain,
  workflow: Workflow,
  database: Database,
  observability: BarChart3,
  infrastructure: Server,
};

export const ServicesStep: React.FC<ServicesStepProps> = ({ profile, value, onChange }) => {
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [validation, setValidation] = useState<SelectionValidation | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['core_ai', 'workflow']));

  // Fetch services when profile changes
  useEffect(() => {
    const fetchServices = async () => {
      setLoading(true);
      try {
        const data = await setupApi.getServices(profile);
        setServices(data);

        // Auto-select defaults if nothing selected
        if (value.length === 0) {
          const defaults = data
            .filter(s => s.default_enabled && s.available_for_profile && !s.required)
            .map(s => s.name);
          onChange(defaults);
        }
      } catch (error) {
        console.error('Failed to fetch services:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchServices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  // Validate selection when it changes
  useEffect(() => {
    const validate = async () => {
      if (value.length === 0) return;
      try {
        const result = await setupApi.validateSelection(value, profile);
        setValidation(result);
      } catch (error) {
        console.error('Validation failed:', error);
      }
    };
    validate();
  }, [value, profile]);

  // Group services
  const groupedServices = useMemo(() => {
    const groups = new Map<string, ServiceInfo[]>();
    for (const service of services) {
      if (!groups.has(service.group)) {
        groups.set(service.group, []);
      }
      groups.get(service.group)!.push(service);
    }
    return groups;
  }, [services]);

  const toggleService = (serviceName: string) => {
    const service = services.find(s => s.name === serviceName);
    if (!service || service.required) return;

    if (value.includes(serviceName)) {
      onChange(value.filter(s => s !== serviceName));
    } else {
      onChange([...value, serviceName]);
    }
  };

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  const isServiceEnabled = (service: ServiceInfo) => {
    if (service.required) return true;
    if (value.includes(service.name)) return true;
    if (validation?.auto_enabled[service.name]) return true;
    return false;
  };

  const getServiceStatus = (service: ServiceInfo) => {
    if (service.required) return 'required';
    if (validation?.auto_enabled[service.name]) return 'auto';
    if (value.includes(service.name)) return 'selected';
    return 'disabled';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">Select Services</h3>
      <p className="text-gray-400 mb-4">
        Choose which services to run. Dependencies are automatically included.
      </p>

      {/* Validation warnings */}
      {validation?.warnings && validation.warnings.length > 0 && (
        <div className="mb-4 p-3 bg-yellow-900/30 border border-yellow-700 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-400">
              {validation.warnings.map((w, i) => (
                <p key={i}>{w}</p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Auto-enabled info */}
      {validation?.auto_enabled && Object.keys(validation.auto_enabled).length > 0 && (
        <div className="mb-4 p-3 bg-blue-900/30 border border-blue-700 rounded-lg">
          <div className="flex items-start gap-2">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-300">
              <p className="font-medium mb-1">Auto-enabled dependencies:</p>
              {Object.entries(validation.auto_enabled).map(([name, info]) => (
                <p key={name} className="text-blue-400/80">
                  {services.find(s => s.name === name)?.display_name || name}: {info.reason}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Service groups */}
      <div className="space-y-4">
        {Array.from(groupedServices.entries())
          .sort((a, b) => {
            const order = ['supabase', 'core_ai', 'workflow', 'database', 'observability', 'infrastructure'];
            return order.indexOf(a[0]) - order.indexOf(b[0]);
          })
          .map(([groupId, groupServices]) => {
            const Icon = groupIcons[groupId] || Layers;
            const isExpanded = expandedGroups.has(groupId);
            const enabledCount = groupServices.filter(s => isServiceEnabled(s)).length;
            const firstService = groupServices[0];

            return (
              <div key={groupId} className="border border-gray-700 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleGroup(groupId)}
                  className="w-full flex items-center justify-between p-4 bg-gray-800 hover:bg-gray-750 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5 text-blue-400" />
                    <div className="text-left">
                      <h4 className="font-medium text-white">{firstService?.group_name || groupId}</h4>
                      <p className="text-xs text-gray-500">
                        {enabledCount} of {groupServices.length} services enabled
                      </p>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  )}
                </button>

                {isExpanded && (
                  <div className="p-4 bg-gray-900 space-y-2">
                    {groupServices
                      .filter(s => s.available_for_profile)
                      .map(service => {
                        const status = getServiceStatus(service);
                        return (
                          <div
                            key={service.name}
                            onClick={() => toggleService(service.name)}
                            className={`
                              flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors
                              ${status === 'selected' ? 'bg-blue-900/30 border border-blue-700' : ''}
                              ${status === 'auto' ? 'bg-purple-900/20 border border-purple-700/50' : ''}
                              ${status === 'required' ? 'bg-green-900/20 border border-green-700/50 cursor-not-allowed' : ''}
                              ${status === 'disabled' ? 'bg-gray-800 border border-gray-700 hover:border-gray-600' : ''}
                            `}
                          >
                            <div className={`
                              w-5 h-5 rounded flex items-center justify-center flex-shrink-0 mt-0.5
                              ${status === 'disabled' ? 'border-2 border-gray-600' : 'bg-green-600'}
                            `}>
                              {status !== 'disabled' && <Check className="w-3 h-3 text-white" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-white">
                                  {service.display_name}
                                </span>
                                {status === 'required' && (
                                  <span className="text-xs px-1.5 py-0.5 bg-green-900/50 text-green-400 rounded">
                                    Required
                                  </span>
                                )}
                                {status === 'auto' && (
                                  <span className="text-xs px-1.5 py-0.5 bg-purple-900/50 text-purple-400 rounded">
                                    Auto
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-gray-400 mt-0.5">{service.description}</p>
                              {service.dependencies.length > 0 && (
                                <p className="text-xs text-gray-500 mt-1">
                                  Requires: {service.dependency_display.join(', ')}
                                </p>
                              )}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            );
          })}
      </div>

      {/* Summary */}
      <div className="mt-6 p-4 bg-gray-800 rounded-lg">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">
            {validation?.total_services || value.length} services will be started
          </span>
          <span className="text-gray-500">
            {Object.keys(validation?.auto_enabled || {}).length} auto-enabled
          </span>
        </div>
      </div>
    </div>
  );
};
