import React from 'react';
import { Shield, Bell, User as UserIcon, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const userJson = localStorage.getItem('sentinelops_user');
  const user = userJson ? JSON.parse(userJson) : null;

  const handleLogout = () => {
    localStorage.removeItem('sentinelops_token');
    localStorage.removeItem('sentinelops_user');
    navigate('/login');
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-lg bg-sky-600 flex items-center justify-center text-white shadow-lg shadow-sky-600/30">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-lg tracking-tight text-white">SentinelOps <span className="text-sky-400">AI</span></span>
          <span className="ml-2.5 text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono">v1.0.0</span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-full border border-slate-700 text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="text-slate-300 font-medium">Local Fleet Online</span>
        </div>

        {user && (
          <div className="flex items-center space-x-3 pl-3 border-l border-slate-800">
            <div className="flex items-center space-x-2 text-sm text-slate-300">
              <UserIcon className="w-4 h-4 text-sky-400" />
              <span>{user.email}</span>
              <span className="text-xs uppercase px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800 font-semibold">{user.role}</span>
            </div>
            <button
              onClick={handleLogout}
              className="text-slate-400 hover:text-rose-400 transition-colors p-1.5 rounded hover:bg-slate-800"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

