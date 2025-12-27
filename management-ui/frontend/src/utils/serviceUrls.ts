/**
 * Service URL mapping - maps service names to their exposed ports
 * These are the ports from docker-compose.override.private.yml
 */

interface ServiceUrlConfig {
  port: number;
  path?: string;
  name: string;
}

const SERVICE_URL_MAP: Record<string, ServiceUrlConfig> = {
  // Direct port access (from docker-compose.override.private.yml)
  'n8n': { port: 5678, name: 'n8n' },
  'open-webui': { port: 8080, name: 'Open WebUI' },
  'flowise': { port: 3001, name: 'Flowise' },
  'langfuse-web': { port: 3000, name: 'Langfuse' },
  'neo4j': { port: 7474, name: 'Neo4j Browser' },
  'searxng': { port: 8081, name: 'SearXNG' },
  'qdrant': { port: 6333, path: '/dashboard', name: 'Qdrant Dashboard' },
  'minio': { port: 9011, name: 'MinIO Console' },
  'clickhouse': { port: 8123, name: 'ClickHouse HTTP' },

  // Supabase services (from supabase/docker/docker-compose.yml)
  'kong': { port: 8000, name: 'Supabase API' },
  'studio': { port: 8000, path: '/project/default', name: 'Supabase Studio' },
  'analytics': { port: 4000, name: 'Supabase Analytics' },
  'supabase-analytics': { port: 4000, name: 'Supabase Analytics' },
};

/**
 * Get the URL for a service
 */
export function getServiceUrl(serviceName: string): string | null {
  const config = SERVICE_URL_MAP[serviceName];
  if (!config) return null;

  const path = config.path || '';
  return `http://localhost:${config.port}${path}`;
}

/**
 * Get display info for a service URL
 */
export function getServiceUrlInfo(serviceName: string): { url: string; label: string } | null {
  const config = SERVICE_URL_MAP[serviceName];
  if (!config) return null;

  const path = config.path || '';
  return {
    url: `http://localhost:${config.port}${path}`,
    label: `:${config.port}`,
  };
}

/**
 * Check if a service has a web UI
 */
export function serviceHasWebUI(serviceName: string): boolean {
  return serviceName in SERVICE_URL_MAP;
}
