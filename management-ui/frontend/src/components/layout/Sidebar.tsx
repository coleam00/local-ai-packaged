import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  GitBranch,
  Settings,
  ScrollText,
  Wand2,
  Box,
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/services', label: 'Services', icon: Box },
  { path: '/dependencies', label: 'Dependencies', icon: GitBranch },
  { path: '/config', label: 'Configuration', icon: Settings },
  { path: '/logs', label: 'Logs', icon: ScrollText },
  { path: '/setup-wizard', label: 'Setup Wizard', icon: Wand2 },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-[#1e293b] border-r border-[#374151] min-h-screen">
      {/* Logo Area */}
      <div className="p-6 border-b border-[#374151]">
        <div className="flex items-center gap-3">
          <img
            src="/localai-logo-white.png"
            alt="LocalAI"
            className="w-10 h-10 object-contain"
          />
          <div>
            <h2 className="font-semibold text-white">LocalAI Stack</h2>
            <p className="text-xs text-slate-500">v1.0.0</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-blue-500/20 text-blue-400 border-l-2 border-blue-500'
                        : 'text-slate-400 hover:bg-[#374151] hover:text-white'
                    }`
                  }
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 w-64 p-4 border-t border-[#374151]">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <span>System Online</span>
        </div>
      </div>
    </aside>
  );
};
