import React from 'react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/services', label: 'Services', icon: '🐳' },
  { path: '/dependencies', label: 'Dependencies', icon: '🔗' },
  { path: '/config', label: 'Configuration', icon: '⚙️' },
  { path: '/logs', label: 'Logs', icon: '📜' },
  { path: '/setup-wizard', label: 'Setup Wizard', icon: '🧙' },
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
