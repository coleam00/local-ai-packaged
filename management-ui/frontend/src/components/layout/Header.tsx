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
