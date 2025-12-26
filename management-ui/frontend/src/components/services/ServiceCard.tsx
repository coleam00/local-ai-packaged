import { ExternalLink, Box } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { ServiceActions } from './ServiceActions';
import type { ServiceInfo } from '../../types/service';

interface ServiceCardProps {
  service: ServiceInfo;
  isActionInProgress: boolean;
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
  onClick?: () => void;
}

export function ServiceCard({
  service,
  isActionInProgress,
  onStart,
  onStop,
  onRestart,
  onClick,
}: ServiceCardProps) {
  const hasPorts = service.ports && service.ports.length > 0;

  return (
    <div
      className={`bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors ${
        onClick ? 'cursor-pointer' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gray-700 rounded-lg">
            <Box className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="font-medium text-white">{service.name}</h3>
            {service.image && (
              <p className="text-xs text-gray-400 truncate max-w-[200px]" title={service.image}>
                {service.image}
              </p>
            )}
          </div>
        </div>
        <div onClick={(e) => e.stopPropagation()}>
          <ServiceActions
            serviceName={service.name}
            status={service.status}
            isLoading={isActionInProgress}
            onStart={onStart}
            onStop={onStop}
            onRestart={onRestart}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <StatusBadge status={service.status} health={service.health} />

        {hasPorts && (
          <div className="flex items-center gap-1">
            {service.ports.slice(0, 2).map((port, idx) => {
              const hostPort = port.split(':')[0];
              const url = `http://localhost:${hostPort}`;
              return (
                <a
                  key={idx}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded text-gray-300 hover:text-white transition-colors"
                  title={`Open port ${hostPort}`}
                >
                  :{hostPort}
                  <ExternalLink className="w-3 h-3" />
                </a>
              );
            })}
            {service.ports.length > 2 && (
              <span className="text-xs text-gray-500">+{service.ports.length - 2}</span>
            )}
          </div>
        )}
      </div>

      {service.profiles && service.profiles.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {service.profiles.map((profile) => (
            <span
              key={profile}
              className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-300 rounded"
            >
              {profile}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
