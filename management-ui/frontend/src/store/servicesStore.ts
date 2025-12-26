import { create } from 'zustand';
import { servicesApi } from '../api/services';
import type { ServiceInfo, ServiceGroup, ServiceActionRequest } from '../types/service';

interface ServicesState {
  services: ServiceInfo[];
  groups: ServiceGroup[];
  isLoading: boolean;
  error: string | null;
  actionInProgress: string | null; // service name being acted upon

  fetchServices: () => Promise<void>;
  fetchGroups: () => Promise<void>;
  startService: (name: string, options?: ServiceActionRequest) => Promise<boolean>;
  stopService: (name: string, options?: ServiceActionRequest) => Promise<boolean>;
  restartService: (name: string, options?: ServiceActionRequest) => Promise<boolean>;
  startGroup: (groupId: string) => Promise<boolean>;
  stopGroup: (groupId: string) => Promise<boolean>;
  clearError: () => void;
}

export const useServicesStore = create<ServicesState>((set, get) => ({
  services: [],
  groups: [],
  isLoading: false,
  error: null,
  actionInProgress: null,

  fetchServices: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await servicesApi.list();
      set({ services: response.services, isLoading: false });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || 'Failed to fetch services',
        isLoading: false,
      });
    }
  },

  fetchGroups: async () => {
    try {
      const response = await servicesApi.getGroups();
      set({ groups: response.groups });
    } catch (error: unknown) {
      console.error('Failed to fetch groups:', error);
    }
  },

  startService: async (name: string, options?: ServiceActionRequest) => {
    set({ actionInProgress: name, error: null });
    try {
      await servicesApi.start(name, options);
      await get().fetchServices();
      set({ actionInProgress: null });
      return true;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || `Failed to start ${name}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  stopService: async (name: string, options?: ServiceActionRequest) => {
    set({ actionInProgress: name, error: null });
    try {
      await servicesApi.stop(name, options);
      await get().fetchServices();
      set({ actionInProgress: null });
      return true;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || `Failed to stop ${name}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  restartService: async (name: string, options?: ServiceActionRequest) => {
    set({ actionInProgress: name, error: null });
    try {
      await servicesApi.restart(name, options);
      await get().fetchServices();
      set({ actionInProgress: null });
      return true;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || `Failed to restart ${name}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  startGroup: async (groupId: string) => {
    set({ actionInProgress: `group:${groupId}`, error: null });
    try {
      await servicesApi.startGroup(groupId);
      await get().fetchServices();
      await get().fetchGroups();
      set({ actionInProgress: null });
      return true;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || `Failed to start group ${groupId}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  stopGroup: async (groupId: string) => {
    set({ actionInProgress: `group:${groupId}`, error: null });
    try {
      await servicesApi.stopGroup(groupId);
      await get().fetchServices();
      await get().fetchGroups();
      set({ actionInProgress: null });
      return true;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || `Failed to stop group ${groupId}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  clearError: () => set({ error: null }),
}));
