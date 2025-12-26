import { apiClient, setAuthToken, clearAuthToken } from './client';
import type { LoginRequest, LoginResponse, SetupRequest, SetupStatus, User } from '../types/api';

export const authApi = {
  async getSetupStatus(): Promise<SetupStatus> {
    const response = await apiClient.get<SetupStatus>('/auth/setup-status');
    return response.data;
  },

  async setup(data: SetupRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/setup', data);
    setAuthToken(response.data.access_token);
    return response.data;
  },

  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', data);
    setAuthToken(response.data.access_token);
    return response.data;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      clearAuthToken();
    }
  },

  async getMe(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },
};
