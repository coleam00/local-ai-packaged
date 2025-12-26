import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
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

  // Create a stable key for the current connection
  const connectionKey = useMemo(() => `${serviceName}-${tail}`, [serviceName, tail]);
  const prevKeyRef = useRef<string>(connectionKey);

  const clearLogs = useCallback(() => {
    setState((prev) => ({ ...prev, logs: [] }));
  }, []);

  // WebSocket connection effect
  useEffect(() => {
    // Check if connection params changed - reset state for new connection
    const keyChanged = prevKeyRef.current !== connectionKey;
    prevKeyRef.current = connectionKey;

    if (!serviceName || !enabled) {
      if (keyChanged) {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- Intentional reset on service change
        setState(initialState);
      }
      return;
    }

    // Reset state for new connection
    if (keyChanged) {
      setState(initialState);
    }

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
      ws.onopen = () => setState((prev) => ({ ...prev, isConnected: true }));
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [serviceName, tail, enabled, connectionKey]);

  return { ...state, clearLogs };
}
