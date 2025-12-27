/**
 * Service URL mapping - maps service names to their Caddy proxy ports
 * These are the default ports when running in "private" mode
 */

interface ServiceUrlConfig {
  port: number;
  path?: string;
  name: string;
}

const SERVICE_URL_MAP: Record<string, ServiceUrlConfig> = {
  // Main services via Caddy
  'n8n': { port: 8001, name: 'n8n' },
  'open-webui': { port: 8002, name: 'Open WebUI' },
  'flowise': { port: 8003, name: 'Flowise' },
  'ollama': { port: 8004, name: 'Ollama API' },
  'ollama-cpu': { port: 8004, name: 'Ollama API' },
  'ollama-gpu': { port: 8004, name: 'Ollama API' },
  'ollama-gpu-amd': { port: 8004, name: 'Ollama API' },
  'kong': { port: 8005, name: 'Supabase API' },
  'studio': { port: 8005, path: '/project/default', name: 'Supabase Studio' },
  'searxng': { port: 8006, name: 'SearXNG' },
  'langfuse-web': { port: 8007, name: 'Langfuse' },
  'neo4j': { port: 8008, name: 'Neo4j Browser' },

  // Direct port access (from docker-compose.override.private.yml)
  'qdrant': { port: 6333, path: '/dashboard', name: 'Qdrant Dashboard' },
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
