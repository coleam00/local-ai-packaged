export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertType = 'high_cpu' | 'high_memory' | 'container_restart' | 'health_check_failed' | 'oom_killed' | 'network_error';

export interface ContainerMetrics {
  service_name: string;
  container_id: string;
  timestamp: string;
  cpu_percent: number;
  memory_usage: number;
  memory_limit: number;
  memory_percent: number;
  network_rx_bytes: number;
  network_tx_bytes: number;
  network_rx_rate: number;
  network_tx_rate: number;
  block_read_bytes?: number;
  block_write_bytes?: number;
}

export interface MetricsSnapshot {
  service_name: string;
  timestamp: string;
  cpu_avg: number;
  cpu_max: number;
  memory_avg: number;
  memory_max: number;
  network_rx_rate_avg: number;
  network_tx_rate_avg: number;
}

export interface MetricsHistoryResponse {
  service_name: string;
  start_time: string;
  end_time: string;
  data_points: MetricsSnapshot[];
  granularity_seconds: number;
}

export interface HealthAlert {
  id: string;
  service_name: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  details?: Record<string, unknown>;
}

export interface DiagnosticResult {
  service_name: string;
  issue: string;
  description: string;
  severity: AlertSeverity;
  recommendation: string;
  auto_fixable: boolean;
}

export interface DiagnosticsResponse {
  service_name: string;
  issues: DiagnosticResult[];
  restart_recommended: boolean;
  last_restart: string | null;
  uptime_seconds: number | null;
}

export interface AllMetricsResponse {
  metrics: ContainerMetrics[];
  timestamp: string;
}

export interface MetricsWebSocketMessage {
  type: 'metrics' | 'error';
  timestamp?: string;
  data?: ContainerMetrics | Record<string, ContainerMetrics>;
  message?: string;
}
