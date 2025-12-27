import { create } from 'zustand';
import { metricsApi } from '../api/metrics';
import type {
  ContainerMetrics,
  HealthAlert,
  DiagnosticsResponse,
  MetricsHistoryResponse,
} from '../types/metrics';

interface MetricsState {
  currentMetrics: Record<string, ContainerMetrics>;
  alerts: HealthAlert[];
  diagnostics: Record<string, DiagnosticsResponse>;
  history: Record<string, MetricsHistoryResponse>;
  isLoading: boolean;
  error: string | null;

  fetchCurrentMetrics: () => Promise<void>;
  fetchAlerts: (serviceName?: string) => Promise<void>;
  fetchDiagnostics: (serviceName: string) => Promise<void>;
  fetchHistory: (serviceName: string, hours?: number) => Promise<void>;
  acknowledgeAlert: (alertId: string) => Promise<boolean>;
  updateMetricsFromStream: (metrics: Record<string, ContainerMetrics>) => void;
  clearError: () => void;
}

export const useMetricsStore = create<MetricsState>((set, get) => ({
  currentMetrics: {},
  alerts: [],
  diagnostics: {},
  history: {},
  isLoading: false,
  error: null,

  fetchCurrentMetrics: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await metricsApi.getAll();
      const metricsMap: Record<string, ContainerMetrics> = {};
      response.metrics.forEach((m) => {
        metricsMap[m.service_name] = m;
      });
      set({ currentMetrics: metricsMap, isLoading: false });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || 'Failed to fetch metrics',
        isLoading: false,
      });
    }
  },

  fetchAlerts: async (serviceName?: string) => {
    try {
      const alerts = await metricsApi.getActiveAlerts(serviceName);
      set({ alerts });
    } catch (error: unknown) {
      console.error('Failed to fetch alerts:', error);
    }
  },

  fetchDiagnostics: async (serviceName: string) => {
    try {
      const diagnostics = await metricsApi.getDiagnostics(serviceName);
      set((state) => ({
        diagnostics: {
          ...state.diagnostics,
          [serviceName]: diagnostics,
        },
      }));
    } catch (error: unknown) {
      console.error('Failed to fetch diagnostics:', error);
    }
  },

  fetchHistory: async (serviceName: string, hours: number = 24) => {
    try {
      const history = await metricsApi.getHistory(serviceName, hours);
      set((state) => ({
        history: {
          ...state.history,
          [serviceName]: history,
        },
      }));
    } catch (error: unknown) {
      console.error('Failed to fetch history:', error);
    }
  },

  acknowledgeAlert: async (alertId: string) => {
    try {
      await metricsApi.acknowledgeAlert(alertId);
      // Refresh alerts
      await get().fetchAlerts();
      return true;
    } catch (error: unknown) {
      console.error('Failed to acknowledge alert:', error);
      return false;
    }
  },

  updateMetricsFromStream: (metrics: Record<string, ContainerMetrics>) => {
    set({ currentMetrics: metrics });
  },

  clearError: () => set({ error: null }),
}));
