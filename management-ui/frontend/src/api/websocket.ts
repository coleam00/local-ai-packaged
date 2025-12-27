import { getAuthToken } from './client';

export interface LogMessage {
  type: 'log' | 'error';
  service?: string;
  content?: string;
  message?: string;
}

export interface StatusMessage {
  type: 'status_update' | 'error';
  changes?: Array<{
    service: string;
    status: string;
    health: string;
  }>;
  message?: string;
}

/**
 * Get the WebSocket base URL.
 * In development with Vite proxy, use the same host.
 * In production (served by backend), use the same host.
 */
function getWsBaseUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}`;
}

export function createLogWebSocket(
  serviceName: string,
  onMessage: (msg: LogMessage) => void,
  onError?: (error: Event) => void,
  onClose?: () => void,
  tail: number = 100
): WebSocket | null {
  const token = getAuthToken();
  if (!token) return null;

  const baseUrl = getWsBaseUrl();
  const url = `${baseUrl}/api/logs/ws/${serviceName}?token=${token}&tail=${tail}`;

  console.debug('WebSocket connecting to:', url);
  const ws = new WebSocket(url);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch {
      onMessage({ type: 'log', content: event.data });
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.(error);
  };

  ws.onclose = () => {
    onClose?.();
  };

  return ws;
}

export function createStatusWebSocket(
  onMessage: (msg: StatusMessage) => void,
  onError?: (error: Event) => void
): WebSocket | null {
  const token = getAuthToken();
  if (!token) return null;

  const baseUrl = getWsBaseUrl();
  const url = `${baseUrl}/api/logs/ws/status?token=${token}`;

  console.debug('Status WebSocket connecting to:', url);
  const ws = new WebSocket(url);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse status message:', e);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.(error);
  };

  return ws;
}
