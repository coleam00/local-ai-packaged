import { apiClient } from './client';
import type { ServiceInfo, ServiceDetail, ServiceGroup, ServiceActionRequest, ServiceActionResponse } from '../types/service';

export interface ServiceListResponse {
  services: ServiceInfo[];
  total: number;
}

export interface ServiceGroupsResponse {
  groups: ServiceGroup[];
}

export interface DependencyGraph {
  nodes: Array<{ id: string; data: Record<string, unknown> }>;
  edges: Array<{ id: string; source: string; target: string; data: Record<string, unknown> }>;
}

export const servicesApi = {
  async list(): Promise<ServiceListResponse> {
    const response = await apiClient.get<ServiceListResponse>('/services');
    return response.data;
  },

  async get(name: string): Promise<ServiceDetail> {
    const response = await apiClient.get<ServiceDetail>(`/services/${name}`);
    return response.data;
  },

  async getGroups(): Promise<ServiceGroupsResponse> {
    const response = await apiClient.get<ServiceGroupsResponse>('/services/groups');
    return response.data;
  },

  async getDependencies(): Promise<DependencyGraph> {
    const response = await apiClient.get<DependencyGraph>('/services/dependencies');
    return response.data;
  },

  async start(name: string, options?: ServiceActionRequest): Promise<ServiceActionResponse> {
    const response = await apiClient.post<ServiceActionResponse>(
      `/services/${name}/start`,
      options || {}
    );
    return response.data;
  },

  async stop(name: string, options?: ServiceActionRequest): Promise<ServiceActionResponse> {
    const response = await apiClient.post<ServiceActionResponse>(
      `/services/${name}/stop`,
      options || {}
    );
    return response.data;
  },

  async restart(name: string, options?: ServiceActionRequest): Promise<ServiceActionResponse> {
    const response = await apiClient.post<ServiceActionResponse>(
      `/services/${name}/restart`,
      options || {}
    );
    return response.data;
  },

  async startGroup(groupId: string, options?: ServiceActionRequest): Promise<unknown> {
    const response = await apiClient.post(`/services/groups/${groupId}/start`, options || {});
    return response.data;
  },

  async stopGroup(groupId: string, options?: ServiceActionRequest): Promise<unknown> {
    const response = await apiClient.post(`/services/groups/${groupId}/stop`, options || {});
    return response.data;
  },
};
