import { create } from 'zustand';
import { configApi } from '../api/config';
import type { ConfigSchema, ValidationError, BackupInfo } from '../types/config';

interface ConfigState {
  config: Record<string, string>; // Masked config for display
  rawConfig: Record<string, string>; // Raw config with actual values
  editedConfig: Record<string, string>; // Edited values (starts with raw)
  schema: ConfigSchema;
  categories: Record<string, string[]>;
  validationErrors: ValidationError[];
  backups: BackupInfo[];
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  hasChanges: boolean;
  changedFields: Set<string>; // Track which fields were actually modified

  fetchConfig: () => Promise<void>;
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
  rawConfig: {},
  editedConfig: {},
  schema: {},
  categories: {},
  validationErrors: [],
  backups: [],
  isLoading: false,
  isSaving: false,
  error: null,
  hasChanges: false,
  changedFields: new Set(),

  fetchConfig: async () => {
    set({ isLoading: true, error: null });
    try {
      // Fetch both masked and raw configs
      const [maskedResponse, rawConfig] = await Promise.all([
        configApi.get(),
        configApi.getRaw(),
      ]);

      set({
        config: maskedResponse.config,
        rawConfig: rawConfig,
        editedConfig: { ...rawConfig }, // Edit the raw values, not masked
        schema: maskedResponse.schema_info,
        categories: maskedResponse.categories,
        validationErrors: maskedResponse.validation_errors,
        isLoading: false,
        hasChanges: false,
        changedFields: new Set(),
      });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || 'Failed to fetch configuration',
        isLoading: false,
      });
    }
  },

  updateField: (key: string, value: string) => {
    const { editedConfig, rawConfig, changedFields } = get();
    const newConfig = { ...editedConfig, [key]: value };

    // Track which fields have been modified
    const newChangedFields = new Set(changedFields);
    if (value !== rawConfig[key]) {
      newChangedFields.add(key);
    } else {
      newChangedFields.delete(key);
    }

    const hasChanges = newChangedFields.size > 0;
    set({
      editedConfig: newConfig,
      hasChanges,
      changedFields: newChangedFields,
    });
  },

  saveConfig: async () => {
    const { editedConfig } = get();
    set({ isSaving: true, error: null });
    try {
      await configApi.update(editedConfig);

      // After save, update rawConfig to match editedConfig
      set({
        rawConfig: { ...editedConfig },
        config: { ...editedConfig }, // Will be refreshed on next fetch
        isSaving: false,
        hasChanges: false,
        changedFields: new Set(),
      });

      // Refresh to get properly masked display values
      get().fetchConfig();

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
    const { editedConfig, rawConfig, changedFields } = get();
    const newConfig = { ...editedConfig, ...secrets };

    // Mark all generated secrets as changed
    const newChangedFields = new Set(changedFields);
    for (const key of Object.keys(secrets)) {
      if (secrets[key] !== rawConfig[key]) {
        newChangedFields.add(key);
      }
    }

    set({
      editedConfig: newConfig,
      hasChanges: newChangedFields.size > 0,
      changedFields: newChangedFields,
    });
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
    const { rawConfig } = get();
    set({
      editedConfig: { ...rawConfig },
      hasChanges: false,
      changedFields: new Set(),
    });
  },

  clearError: () => set({ error: null }),
}));
