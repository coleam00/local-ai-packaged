import { useEffect, useRef, useState, useCallback } from 'react';
import { createLogWebSocket } from '../api/websocket';
import type { LogMessage } from '../api/websocket';

interface UseLogStreamOptions {
  serviceName: string | null;
  tail?: number;
  enabled?: boolean;
}

interface LogStreamState {
  logs: string[];
  isConnected: boolean;
  error: string | null;
}

const initialState: LogStreamState = {
  logs: [],
  isConnected: false,
  error: null,
};

export function useLogStream({ serviceName, tail = 100, enabled = true }: UseLogStreamOptions) {
  const [state, setState] = useState<LogStreamState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const connectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentServiceRef = useRef<string | null>(null);

  const clearLogs = useCallback(() => {
    setState((prev) => ({ ...prev, logs: [] }));
  }, []);

  // WebSocket connection effect
  useEffect(() => {
    // Clear any pending connection timeout
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = null;
    }

    // Close existing connection if service changed
    if (wsRef.current && currentServiceRef.current !== serviceName) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (!serviceName || !enabled) {
      setState(initialState);
      currentServiceRef.current = null;
      return;
    }

    // Reset state for new service
    if (currentServiceRef.current !== serviceName) {
      setState(initialState);
      currentServiceRef.current = serviceName;
    }

    // Debounce connection to avoid rapid reconnects
    connectTimeoutRef.current = setTimeout(() => {
      // Don't reconnect if service changed during timeout
      if (currentServiceRef.current !== serviceName) return;

      const ws = createLogWebSocket(
        serviceName,
        (msg: LogMessage) => {
          if (msg.type === 'log' && msg.content) {
            setState((prev) => ({
              ...prev,
              logs: [...prev.logs, msg.content!].slice(-5000),
            }));
          } else if (msg.type === 'error') {
            setState((prev) => ({
              ...prev,
              error: msg.message || 'Unknown error',
            }));
          }
        },
        () => {
          setState((prev) => ({
            ...prev,
            error: 'WebSocket connection error',
            isConnected: false,
          }));
        },
        () => {
          setState((prev) => ({ ...prev, isConnected: false }));
        },
        tail
      );

      if (ws) {
        wsRef.current = ws;
        ws.onopen = () => setState((prev) => ({ ...prev, isConnected: true, error: null }));
      }
    }, 100); // 100ms debounce

    return () => {
      if (connectTimeoutRef.current) {
        clearTimeout(connectTimeoutRef.current);
        connectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [serviceName, tail, enabled]);

  return { ...state, clearLogs };
}
