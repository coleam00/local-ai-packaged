export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
  last_login: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  is_admin: boolean;
}

export interface SetupRequest {
  username: string;
  password: string;
  confirm_password: string;
}

export interface SetupStatus {
  setup_required: boolean;
  has_admin: boolean;
}

export interface ApiError {
  detail: string;
}
