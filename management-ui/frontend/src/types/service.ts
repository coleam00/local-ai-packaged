export type ServiceStatus = 'running' | 'stopped' | 'starting' | 'stopping' | 'restarting' | 'error' | 'not_created';
export type HealthStatus = 'healthy' | 'unhealthy' | 'starting' | 'none' | 'unknown';

export interface ServiceInfo {
  name: string;
  status: ServiceStatus;
  health: HealthStatus;
  image: string | null;
  container_id: string | null;
  ports: string[];
  group: string;
  compose_file: string;
  profiles: string[];
  has_healthcheck: boolean;
  depends_on: Record<string, string>;
}

export interface ServiceDetail extends ServiceInfo {
  environment: Record<string, string>;
  created: string | null;
  dependents: string[];
  dependencies: string[];
}

export interface ServiceGroup {
  id: string;
  name: string;
  description: string;
  services: string[];
  running_count: number;
  total_count: number;
}

export interface ServiceActionRequest {
  profile?: string;
  environment?: string;
  force?: boolean;
}

export interface ServiceActionResponse {
  success: boolean;
  message: string;
  service: string;
  action: string;
  output?: string;
  error?: string;
}
