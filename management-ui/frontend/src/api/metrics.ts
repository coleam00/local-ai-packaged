import { apiClient } from './client';
import type {
  ContainerMetrics,
  AllMetricsResponse,
  MetricsHistoryResponse,
  HealthAlert,
  DiagnosticsResponse,
} from '../types/metrics';

export const metricsApi = {
  async getAll(): Promise<AllMetricsResponse> {
    const response = await apiClient.get<AllMetricsResponse>('/metrics');
    return response.data;
  },

  async getService(serviceName: string): Promise<ContainerMetrics> {
    const response = await apiClient.get<ContainerMetrics>(`/metrics/${serviceName}`);
    return response.data;
  },

  async getHistory(serviceName: string, hours: number = 24): Promise<MetricsHistoryResponse> {
    const response = await apiClient.get<MetricsHistoryResponse>(
      `/metrics/${serviceName}/history`,
      { params: { hours } }
    );
    return response.data;
  },

  async getDiagnostics(serviceName: string): Promise<DiagnosticsResponse> {
    const response = await apiClient.get<DiagnosticsResponse>(
      `/metrics/${serviceName}/diagnostics`
    );
    return response.data;
  },

  async getActiveAlerts(serviceName?: string): Promise<HealthAlert[]> {
    const response = await apiClient.get<HealthAlert[]>('/metrics/alerts/active', {
      params: serviceName ? { service_name: serviceName } : {},
    });
    return response.data;
  },

  async acknowledgeAlert(alertId: string): Promise<{ success: boolean }> {
    const response = await apiClient.post<{ success: boolean }>(
      `/metrics/alerts/${alertId}/acknowledge`
    );
    return response.data;
  },
};
