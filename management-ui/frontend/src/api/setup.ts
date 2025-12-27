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

  async complete(config: {
    profile: string;
    environment: string;
    secrets: Record<string, string>;
    enabled_services: string[];
  }): Promise<{ status: string; error?: string }> {
    const response = await apiClient.post('/setup/complete', config);
    return response.data;
  }
};
