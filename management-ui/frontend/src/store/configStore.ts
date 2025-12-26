import { create } from 'zustand';
import { configApi } from '../api/config';
import type { ConfigSchema, ValidationError, BackupInfo } from '../types/config';

interface ConfigState {
  config: Record<string, string>;
  editedConfig: Record<string, string>;
  schema: ConfigSchema;
  categories: Record<string, string[]>;
  validationErrors: ValidationError[];
  backups: BackupInfo[];
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  hasChanges: boolean;

  fetchConfig: () => Promise<void>;
  fetchRawConfig: () => Promise<void>;
  updateField: (key: string, value: string) => void;
  saveConfig: () => Promise<boolean>;
  validateConfig: () => Promise<boolean>;
  generateSecrets: (onlyMissing?: boolean) => Promise<{ secrets: Record<string, string>; generated_count: number } | undefined>;
  applyGeneratedSecrets: (secrets: Record<string, string>) => void;
  fetchBackups: () => Promise<void>;
  restoreBackup: (filename: string) => Promise<boolean>;
  resetChanges: () => void;
  clearError: () => void;
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  config: {},
  editedConfig: {},
  schema: {},
  categories: {},
  validationErrors: [],
  backups: [],
  isLoading: false,
  isSaving: false,
  error: null,
  hasChanges: false,

  fetchConfig: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await configApi.get();
      set({
        config: response.config,
        editedConfig: { ...response.config },
        schema: response.schema_info,
        categories: response.categories,
        validationErrors: response.validation_errors,
        isLoading: false,
        hasChanges: false,
      });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || 'Failed to fetch configuration',
        isLoading: false,
      });
    }
  },

  fetchRawConfig: async () => {
    try {
      const rawConfig = await configApi.getRaw();
      set({
        config: rawConfig,
        editedConfig: { ...rawConfig },
        hasChanges: false,
      });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({ error: err.response?.data?.detail || 'Failed to fetch raw configuration' });
    }
  },

  updateField: (key: string, value: string) => {
    const { editedConfig, config } = get();
    const newConfig = { ...editedConfig, [key]: value };
    const hasChanges = JSON.stringify(newConfig) !== JSON.stringify(config);
    set({ editedConfig: newConfig, hasChanges });
  },

  saveConfig: async () => {
    const { editedConfig } = get();
    set({ isSaving: true, error: null });
    try {
      await configApi.update(editedConfig);
      set({
        config: { ...editedConfig },
        isSaving: false,
        hasChanges: false,
      });
      return true;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || 'Failed to save configuration',
        isSaving: false,
      });
      return false;
    }
  },

  validateConfig: async () => {
    const { editedConfig } = get();
    try {
      const result = await configApi.validate(editedConfig);
      set({ validationErrors: result.errors });
      return result.valid;
    } catch {
      return false;
    }
  },

  generateSecrets: async (onlyMissing = true) => {
    try {
      const result = await configApi.generateSecrets(onlyMissing);
      return result;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({ error: err.response?.data?.detail || 'Failed to generate secrets' });
      return undefined;
    }
  },

  applyGeneratedSecrets: (secrets: Record<string, string>) => {
    const { editedConfig } = get();
    const newConfig = { ...editedConfig, ...secrets };
    set({ editedConfig: newConfig, hasChanges: true });
  },

  fetchBackups: async () => {
    try {
      const response = await configApi.listBackups();
      set({ backups: response.backups });
    } catch (error: unknown) {
      console.error('Failed to fetch backups:', error);
    }
  },

  restoreBackup: async (filename: string) => {
    try {
      await configApi.restoreBackup(filename);
      await get().fetchConfig();
      return true;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({ error: err.response?.data?.detail || 'Failed to restore backup' });
      return false;
    }
  },

  resetChanges: () => {
    const { config } = get();
    set({ editedConfig: { ...config }, hasChanges: false });
  },

  clearError: () => set({ error: null }),
}));
