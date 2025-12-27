import { create } from 'zustand';
import { authApi } from '../api/auth';
import { setupApi } from '../api/setup';
import type { User, LoginRequest, SetupRequest } from '../types/api';
import { getAuthToken, clearAuthToken } from '../api/client';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  setupRequired: boolean;
  stackRunning: boolean;

  checkAuth: () => Promise<void>;
  checkSetupStatus: () => Promise<boolean>;
  login: (data: LoginRequest) => Promise<void>;
  setup: (data: SetupRequest) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  setupRequired: false,
  stackRunning: false,

  checkAuth: async () => {
    const token = getAuthToken();
    if (!token) {
      set({ isAuthenticated: false, isLoading: false });
      return;
    }

    try {
      const user = await authApi.getMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      clearAuthToken();
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  checkSetupStatus: async () => {
    try {
      const status = await authApi.getSetupStatus();
      // Also check stack status
      let stackRunning = false;
      try {
        const stackStatus = await setupApi.getStatus();
        stackRunning = stackStatus.stack_running;
      } catch {
        // Ignore errors - stack might not be reachable
      }

      set({
        setupRequired: status.setup_required,
        stackRunning,
        isLoading: false
      });
      return status.setup_required;
    } catch {
      set({ isLoading: false });
      return false;
    }
  },

  login: async (data: LoginRequest) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.login(data);
      set({
        user: {
          id: 0,
          username: response.username,
          is_admin: response.is_admin,
          created_at: '',
          last_login: null,
        },
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };
      let errorMessage = 'Login failed';
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        errorMessage = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errorMessage = detail.map((e) => e.msg).join(', ');
      }
      set({
        error: errorMessage,
        isLoading: false,
      });
      throw error;
    }
  },

  setup: async (data: SetupRequest) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.setup(data);
      set({
        user: {
          id: 0,
          username: response.username,
          is_admin: response.is_admin,
          created_at: '',
          last_login: null,
        },
        isAuthenticated: true,
        isLoading: false,
        setupRequired: false,
      });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };
      let errorMessage = 'Setup failed';
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        errorMessage = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errorMessage = detail.map((e) => e.msg).join(', ');
      }
      set({
        error: errorMessage,
        isLoading: false,
      });
      throw error;
    }
  },

  logout: async () => {
    await authApi.logout();
    set({ user: null, isAuthenticated: false });
  },

  clearError: () => set({ error: null }),
}));
