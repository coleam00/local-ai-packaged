import { apiClient } from './client';
import type { ConfigSchema, ValidationError, BackupInfo } from '../types/config';

export interface ConfigResponse {
  config: Record<string, string>;
  schema_info: ConfigSchema;
  categories: Record<string, string[]>;
  validation_errors: ValidationError[];
}

export const configApi = {
  async get(): Promise<ConfigResponse> {
    const response = await apiClient.get<ConfigResponse>('/config');
    return response.data;
  },

  async getRaw(): Promise<Record<string, string>> {
    const response = await apiClient.get<Record<string, string>>('/config/raw');
    return response.data;
  },

  async update(config: Record<string, string>): Promise<{ message: string; backup_path?: string }> {
    const response = await apiClient.put('/config', { config });
    return response.data;
  },

  async validate(config: Record<string, string>): Promise<{ valid: boolean; errors: ValidationError[] }> {
    const response = await apiClient.post('/config/validate', { config });
    return response.data;
  },

  async generateSecrets(onlyMissing: boolean = true): Promise<{ secrets: Record<string, string>; generated_count: number }> {
    const response = await apiClient.post(`/config/generate-secrets?only_missing=${onlyMissing}`);
    return response.data;
  },

  async listBackups(): Promise<{ backups: BackupInfo[] }> {
    const response = await apiClient.get('/config/backups');
    return response.data;
  },

  async restoreBackup(filename: string): Promise<{ message: string }> {
    const response = await apiClient.post('/config/restore', { filename });
    return response.data;
  },

  getDownloadUrl(): string {
    return '/api/config/download';
  },
};
