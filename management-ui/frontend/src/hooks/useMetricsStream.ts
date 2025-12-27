import { useEffect, useRef, useState, useCallback } from 'react';
import { createMetricsWebSocket } from '../api/websocket';
import type { MetricsMessage } from '../api/websocket';
import type { ContainerMetrics } from '../types/metrics';

interface UseMetricsStreamOptions {
  serviceName?: string;
  enabled?: boolean;
  interval?: number;
  historySize?: number;
}

interface MetricsStreamState {
  currentMetrics: Record<string, ContainerMetrics>;
  metricsHistory: Record<string, ContainerMetrics[]>;
  isConnected: boolean;
  error: string | null;
}

const initialState: MetricsStreamState = {
  currentMetrics: {},
  metricsHistory: {},
  isConnected: false,
  error: null,
};

export function useMetricsStream({
  serviceName,
  enabled = true,
  interval = 2,
  historySize = 60, // Keep last 60 data points (2 minutes at 2s interval)
}: UseMetricsStreamOptions = {}) {
  const [state, setState] = useState<MetricsStreamState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const connectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearHistory = useCallback(() => {
    setState((prev) => ({ ...prev, metricsHistory: {} }));
  }, []);

  useEffect(() => {
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (!enabled) {
      setState(initialState);
      return;
    }

    connectTimeoutRef.current = setTimeout(() => {
      const ws = createMetricsWebSocket(
        (msg: MetricsMessage) => {
          if (msg.type === 'metrics' && msg.data) {
            const data = msg.data;
            setState((prev) => {
              const newCurrentMetrics = { ...prev.currentMetrics };
              const newHistory = { ...prev.metricsHistory };

              // Handle single service or all services
              if (serviceName && 'service_name' in data) {
                // Single service metrics
                const metrics = data as unknown as ContainerMetrics;
                newCurrentMetrics[metrics.service_name] = metrics;

                if (!newHistory[metrics.service_name]) {
                  newHistory[metrics.service_name] = [];
                }
                newHistory[metrics.service_name] = [
                  ...newHistory[metrics.service_name].slice(-(historySize - 1)),
                  metrics,
                ];
              } else {
                // All services metrics
                const allMetrics = data as Record<string, ContainerMetrics>;
                Object.entries(allMetrics).forEach(([name, metrics]) => {
                  newCurrentMetrics[name] = metrics;

                  if (!newHistory[name]) {
                    newHistory[name] = [];
                  }
                  newHistory[name] = [
                    ...newHistory[name].slice(-(historySize - 1)),
                    metrics,
                  ];
                });
              }

              return {
                ...prev,
                currentMetrics: newCurrentMetrics,
                metricsHistory: newHistory,
              };
            });
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
        serviceName,
        interval
      );

      if (ws) {
        wsRef.current = ws;
        ws.onopen = () => setState((prev) => ({ ...prev, isConnected: true, error: null }));
      }
    }, 100);

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
  }, [serviceName, enabled, interval, historySize]);

  return { ...state, clearHistory };
}
