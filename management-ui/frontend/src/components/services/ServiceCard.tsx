import { ExternalLink, Box, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';
import { StatusBadge } from './StatusBadge';
import { ServiceActions } from './ServiceActions';
import type { ServiceInfo } from '../../types/service';
import { getServiceUrlInfo } from '../../utils/serviceUrls';

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
  // Get the service URL from our mapping (Caddy proxy ports)
  const urlInfo = getServiceUrlInfo(service.name);

  return (
    <div
      className={`bg-[#1e293b] rounded-[12px] p-4 border border-[#374151]
                  hover:border-[#4b5563] transition-all duration-200 ${
        onClick ? 'cursor-pointer hover:translate-y-[-2px]' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-[#374151] rounded-lg">
            <Box className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="font-medium text-white">{service.name}</h3>
            {service.image && (
              <p
                className="text-xs text-slate-500 truncate max-w-[180px]"
                title={service.image}
              >
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

        <div className="flex items-center gap-2">
          {service.status === 'running' && (
            <Link
              to={`/logs?service=${service.name}`}
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs
                         bg-[#374151] hover:bg-[#4b5563] rounded
                         text-slate-400 hover:text-white transition-colors"
              title={`View logs for ${service.name}`}
            >
              <FileText className="w-3 h-3" />
            </Link>
          )}
          {urlInfo && service.status === 'running' && (
            <a
              href={urlInfo.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs
                         bg-[#374151] hover:bg-[#4b5563] rounded
                         text-slate-400 hover:text-white transition-colors"
              title={`Open ${service.name}`}
            >
              {urlInfo.label}
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
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
