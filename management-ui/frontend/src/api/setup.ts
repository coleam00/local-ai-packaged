import { apiClient } from './client';

export interface ServiceInfo {
  name: string;
  display_name: string;
  group: string;
  group_name: string;
  description: string;
  required: boolean;
  dependencies: string[];
  dependency_display: string[];
  profiles: string[];
  default_enabled: boolean;
  category: string;
  available_for_profile: boolean;
}

export interface SelectionValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
  auto_enabled: Record<string, { reason: string; required_by: string[] }>;
  total_services: number;
}

export interface SetupStatus {
  setup_required: boolean;
  has_env_file: boolean;
  has_secrets: boolean;
  supabase_cloned: boolean;
  services_running: number;
  stack_running: boolean;
  stack_configured: boolean;
  missing_secrets: string[];
}

export interface StackConfig {
  profile: string;
  environment: string;
  enabled_services: string[];
  setup_completed: boolean;
}

export interface PreflightCheck {
  can_proceed: boolean;
  issues: Array<{ type: string; message: string; fix: string }>;
  warnings: Array<{ type: string; message: string; fix: string }>;
}

export interface FixResult {
  success: boolean;
  message: string;
}

export interface PortStatus {
  port: number;
  available: boolean;
  used_by: string | null;
}

export interface ServicePortScan {
  service_name: string;
  display_name: string;
  ports: Record<string, PortStatus>;
  all_available: boolean;
  suggested_ports: Record<string, number>;
}

export interface PortCheckResponse {
  has_conflicts: boolean;
  services: ServicePortScan[];
  total_ports_checked: number;
  conflicts_count: number;
}

export interface PortValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export const setupApi = {
  async getStatus(): Promise<SetupStatus> {
    const response = await apiClient.get<SetupStatus>('/setup/status');
    return response.data;
  },

  async getStackConfig(): Promise<StackConfig | null> {
    try {
      const response = await apiClient.get<StackConfig>('/setup/stack-config');
      return response.data;
    } catch {
      return null;
    }
  },

  async preflightCheck(): Promise<PreflightCheck> {
    const response = await apiClient.get<PreflightCheck>('/setup/preflight');
    return response.data;
  },

  async fixPreflightIssue(fixType: string): Promise<FixResult> {
    const response = await apiClient.post<FixResult>('/setup/preflight/fix', null, {
      params: { fix_type: fixType }
    });
    return response.data;
  },

  async getServices(profile: string): Promise<ServiceInfo[]> {
    const response = await apiClient.get<ServiceInfo[]>('/setup/services', {
      params: { profile }
    });
    return response.data;
  },

  async validateSelection(selected: string[], profile: string): Promise<SelectionValidation> {
    const response = await apiClient.post<SelectionValidation>(
      '/setup/validate-selection',
      selected,
      { params: { profile } }
    );
    return response.data;
  },

  async generateSecrets(): Promise<Record<string, string>> {
    const response = await apiClient.post<{ secrets: Record<string, string> }>('/setup/generate-secrets');
    return response.data.secrets;
  },

  async checkPorts(enabledServices?: string[], profile: string = 'cpu'): Promise<PortCheckResponse> {
    const params: Record<string, string> = { profile };
    if (enabledServices) {
      params.enabled_services = enabledServices.join(',');
    }
    const response = await apiClient.get<PortCheckResponse>('/setup/check-ports', { params });
    return response.data;
  },

  async validatePorts(portConfig: Record<string, Record<string, number>>): Promise<PortValidation> {
    const response = await apiClient.post<PortValidation>('/setup/validate-ports', portConfig);
    return response.data;
  },

  async complete(config: {
    profile: string;
    environment: string;
    secrets: Record<string, string>;
    enabled_services: string[];
    port_overrides?: Record<string, Record<string, number>>;
  }): Promise<{ status: string; error?: string }> {
    const response = await apiClient.post('/setup/complete', config);
    return response.data;
  }
};
