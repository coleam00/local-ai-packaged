# Stage 04: Frontend Foundation

## Summary
Create the React/Vite frontend shell with routing, authentication pages, and API client. After this stage, users can log in and see a basic layout.

## Prerequisites
- Stage 01-03 completed (backend is functional)

## Deliverable
- Vite + React + TypeScript project
- Tailwind CSS styling
- Login page with auth flow
- Protected route wrapper
- Basic layout (header, sidebar)
- API client with Axios

---

## Files to Create

```
management-ui/frontend/
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── vite-env.d.ts
│   │
│   ├── api/
│   │   ├── client.ts
│   │   └── auth.ts
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Loading.tsx
│   │   │
│   │   └── layout/
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── MainLayout.tsx
│   │
│   ├── hooks/
│   │   └── useAuth.ts
│   │
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Setup.tsx
│   │   └── Dashboard.tsx
│   │
│   ├── store/
│   │   └── authStore.ts
│   │
│   └── types/
│       └── api.ts
│
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

---

## Task 1: Initialize Project

```bash
cd management-ui
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install axios zustand react-router-dom @tanstack/react-query
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

---

## Task 2: Configure Tailwind

**File**: `management-ui/frontend/tailwind.config.js`
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**File**: `management-ui/frontend/src/index.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-gray-50 text-gray-900;
}

.btn {
  @apply px-4 py-2 rounded-md font-medium transition-colors;
}

.btn-primary {
  @apply bg-blue-600 text-white hover:bg-blue-700;
}

.btn-secondary {
  @apply bg-gray-200 text-gray-700 hover:bg-gray-300;
}

.btn-danger {
  @apply bg-red-600 text-white hover:bg-red-700;
}

.card {
  @apply bg-white rounded-lg shadow-sm border border-gray-200 p-4;
}

.input {
  @apply w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent;
}

.label {
  @apply block text-sm font-medium text-gray-700 mb-1;
}
```

---

## Task 3: Configure Vite

**File**: `management-ui/frontend/vite.config.ts`
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:9000',
        ws: true,
      },
    },
  },
})
```

---

## Task 4: Create Types

**File**: `management-ui/frontend/src/types/api.ts`
```typescript
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
```

---

## Task 5: Create API Client

**File**: `management-ui/frontend/src/api/client.ts`
```typescript
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const setAuthToken = (token: string) => {
  localStorage.setItem('token', token);
};

export const clearAuthToken = () => {
  localStorage.removeItem('token');
};

export const getAuthToken = () => {
  return localStorage.getItem('token');
};
```

**File**: `management-ui/frontend/src/api/auth.ts`
```typescript
import { apiClient, setAuthToken, clearAuthToken } from './client';
import { LoginRequest, LoginResponse, SetupRequest, SetupStatus, User } from '../types/api';

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
```

---

## Task 6: Create Auth Store

**File**: `management-ui/frontend/src/store/authStore.ts`
```typescript
import { create } from 'zustand';
import { authApi } from '../api/auth';
import { User, LoginRequest, SetupRequest } from '../types/api';
import { getAuthToken, clearAuthToken } from '../api/client';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  setupRequired: boolean;

  checkAuth: () => Promise<void>;
  checkSetupStatus: () => Promise<boolean>;
  login: (data: LoginRequest) => Promise<void>;
  setup: (data: SetupRequest) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  setupRequired: false,

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
      set({ setupRequired: status.setup_required });
      return status.setup_required;
    } catch {
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
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Login failed',
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
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Setup failed',
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
```

---

## Task 7: Create Common Components

**File**: `management-ui/frontend/src/components/common/Button.tsx`
```typescript
import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  isLoading,
  disabled,
  className = '',
  ...props
}) => {
  const baseClass = 'btn';
  const variantClass = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    danger: 'btn-danger',
  }[variant];

  return (
    <button
      className={`${baseClass} ${variantClass} ${className} ${
        (disabled || isLoading) ? 'opacity-50 cursor-not-allowed' : ''
      }`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading...
        </span>
      ) : children}
    </button>
  );
};
```

**File**: `management-ui/frontend/src/components/common/Input.tsx`
```typescript
import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  className = '',
  ...props
}) => {
  return (
    <div className="mb-4">
      {label && <label className="label">{label}</label>}
      <input
        className={`input ${error ? 'border-red-500' : ''} ${className}`}
        {...props}
      />
      {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/common/Card.tsx`
```typescript
import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export const Card: React.FC<CardProps> = ({ children, className = '', title }) => {
  return (
    <div className={`card ${className}`}>
      {title && <h3 className="text-lg font-semibold mb-3">{title}</h3>}
      {children}
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/common/Loading.tsx`
```typescript
import React from 'react';

export const Loading: React.FC<{ message?: string }> = ({ message = 'Loading...' }) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <svg className="animate-spin h-8 w-8 text-blue-600 mb-4" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      <p className="text-gray-600">{message}</p>
    </div>
  );
};
```

---

## Task 8: Create Layout Components

**File**: `management-ui/frontend/src/components/layout/Header.tsx`
```typescript
import React from 'react';
import { useAuthStore } from '../../store/authStore';
import { Button } from '../common/Button';

export const Header: React.FC = () => {
  const { user, logout } = useAuthStore();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-bold text-gray-900">
          Stack Manager
        </h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">
            {user?.username}
          </span>
          <Button variant="secondary" onClick={logout}>
            Logout
          </Button>
        </div>
      </div>
    </header>
  );
};
```

**File**: `management-ui/frontend/src/components/layout/Sidebar.tsx`
```typescript
import React from 'react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/services', label: 'Services', icon: '🐳' },
  { path: '/config', label: 'Configuration', icon: '⚙️' },
  { path: '/logs', label: 'Logs', icon: '📜' },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-gray-800 text-white min-h-screen">
      <nav className="p-4">
        <ul className="space-y-2">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-2 rounded-md transition-colors ${
                    isActive
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  }`
                }
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
};
```

**File**: `management-ui/frontend/src/components/layout/MainLayout.tsx`
```typescript
import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Loading } from '../common/Loading';

export const MainLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return <Loading message="Checking authentication..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-6 bg-gray-50">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
```

---

## Task 9: Create Pages

**File**: `management-ui/frontend/src/pages/Login.tsx`
```typescript
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Card } from '../components/common/Card';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, isLoading, error, clearError } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    try {
      await login({ username, password });
      navigate('/');
    } catch {
      // Error is handled in store
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <Card className="w-full max-w-md">
        <h2 className="text-2xl font-bold text-center mb-6">Stack Manager</h2>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <Input
            label="Username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button type="submit" className="w-full" isLoading={isLoading}>
            Login
          </Button>
        </form>
      </Card>
    </div>
  );
};
```

**File**: `management-ui/frontend/src/pages/Setup.tsx`
```typescript
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Card } from '../components/common/Card';

export const Setup: React.FC = () => {
  const navigate = useNavigate();
  const { setup, isLoading, error, clearError } = useAuthStore();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [validationError, setValidationError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setValidationError('');

    if (password !== confirmPassword) {
      setValidationError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setValidationError('Password must be at least 8 characters');
      return;
    }

    try {
      await setup({ username, password, confirm_password: confirmPassword });
      navigate('/');
    } catch {
      // Error handled in store
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <Card className="w-full max-w-md">
        <h2 className="text-2xl font-bold text-center mb-2">Welcome!</h2>
        <p className="text-gray-600 text-center mb-6">
          Create your admin account to get started.
        </p>

        {(error || validationError) && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error || validationError}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <Input
            label="Username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={3}
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
          <Input
            label="Confirm Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
          <Button type="submit" className="w-full" isLoading={isLoading}>
            Create Account
          </Button>
        </form>
      </Card>
    </div>
  );
};
```

**File**: `management-ui/frontend/src/pages/Dashboard.tsx`
```typescript
import React from 'react';
import { Card } from '../components/common/Card';

export const Dashboard: React.FC = () => {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Services">
          <p className="text-3xl font-bold text-blue-600">--</p>
          <p className="text-gray-600">Running / Total</p>
        </Card>

        <Card title="Health">
          <p className="text-3xl font-bold text-green-600">--</p>
          <p className="text-gray-600">Healthy Services</p>
        </Card>

        <Card title="Configuration">
          <p className="text-3xl font-bold text-yellow-600">--</p>
          <p className="text-gray-600">Variables Configured</p>
        </Card>
      </div>

      <div className="mt-8">
        <Card title="Quick Actions">
          <p className="text-gray-600">
            Service management will be added in the next stage.
          </p>
        </Card>
      </div>
    </div>
  );
};
```

---

## Task 10: Create App with Routing

**File**: `management-ui/frontend/src/App.tsx`
```typescript
import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { MainLayout } from './components/layout/MainLayout';
import { Login } from './pages/Login';
import { Setup } from './pages/Setup';
import { Dashboard } from './pages/Dashboard';
import { Loading } from './components/common/Loading';

const App: React.FC = () => {
  const { checkAuth, checkSetupStatus, isLoading, setupRequired } = useAuthStore();
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    const init = async () => {
      const needsSetup = await checkSetupStatus();
      if (!needsSetup) {
        await checkAuth();
      }
      setInitializing(false);
    };
    init();
  }, [checkAuth, checkSetupStatus]);

  if (initializing || isLoading) {
    return <Loading message="Initializing..." />;
  }

  if (setupRequired) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/setup" element={<Setup />} />
          <Route path="*" element={<Navigate to="/setup" replace />} />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<MainLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/services" element={<div>Services (Stage 05)</div>} />
          <Route path="/config" element={<div>Config (Stage 06)</div>} />
          <Route path="/logs" element={<div>Logs (Stage 07)</div>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
```

**File**: `management-ui/frontend/src/main.tsx`
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

---

## Validation

### Start Both Servers
```bash
# Terminal 1: Backend
cd management-ui/backend
python -m uvicorn app.main:app --reload --port 9000

# Terminal 2: Frontend
cd management-ui/frontend
npm run dev
```

### Test in Browser
1. Open http://localhost:3000
2. Should redirect to /setup (if first time)
3. Create admin account
4. Should redirect to dashboard
5. Logout and test login flow

### Success Criteria
- [ ] Frontend loads at localhost:3000
- [ ] Setup page works for first-time users
- [ ] Login works with created credentials
- [ ] Protected routes redirect to login
- [ ] Logout clears session and redirects
- [ ] Sidebar navigation works
- [ ] Header shows username

---

## Next Stage
Proceed to `05-dashboard-services-ui.md` to add service management UI.
