import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { MainLayout } from './components/layout/MainLayout';
import { Login } from './pages/Login';
import { Setup } from './pages/Setup';
import { Dashboard } from './pages/Dashboard';
import { Services } from './pages/Services';
import { Dependencies } from './pages/Dependencies';
import { Configuration } from './pages/Configuration';
import { Logs } from './pages/Logs';
import { Health } from './pages/Health';
import { SetupWizardPage } from './pages/SetupWizardPage';
import { Loading } from './components/common/Loading';

const App: React.FC = () => {
  const { checkAuth, checkSetupStatus, isLoading, setupRequired, stackConfigured } = useAuthStore();
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    const init = async () => {
      await checkSetupStatus();
      await checkAuth();
      setInitializing(false);
    };
    init();
  }, [checkAuth, checkSetupStatus]);

  if (initializing || isLoading) {
    return <Loading message="Initializing..." />;
  }

  // Show setup page if no admin exists
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

  // Show setup wizard if admin exists but stack not configured
  if (!stackConfigured) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/setup-wizard" element={<SetupWizardPage />} />
          <Route path="*" element={<Navigate to="/setup-wizard" replace />} />
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
          <Route path="/services" element={<Services />} />
          <Route path="/dependencies" element={<Dependencies />} />
          <Route path="/config" element={<Configuration />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/health" element={<Health />} />
          <Route path="/setup-wizard" element={<SetupWizardPage />} />
          <Route path="/settings" element={<div className="text-gray-400">Settings (Coming Soon)</div>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
