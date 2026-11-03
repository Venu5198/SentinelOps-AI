import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, AlertTriangle, Server, FileText, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';

export const Sidebar: React.FC = () => {
  const [aiStatus, setAiStatus] = useState<any>(null);

  useEffect(() => {
    const fetchAi = async () => {
      try {
        const res = await api.get('/health/ai');
        setAiStatus(res.data);
      } catch (e) {
        // default fallback state
      }
    };
    fetchAi();
  }, []);

  const links = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
    { to: '/services', label: 'Services', icon: Server },
    { to: '/approvals', label: 'Approvals', icon: CheckCircle2 },
    { to: '/audit', label: 'Audit Logs', icon: FileText },
  ];

  return (
    <aside className="w-60 border-r border-slate-800 bg-slate-900/50 flex flex-col justify-between py-6 px-3">
      <nav className="space-y-1.5">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-sky-600/15 text-sky-400 border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{link.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="bg-slate-800/50 rounded-xl p-3.5 border border-slate-800 text-xs text-slate-400">
        <div className="font-semibold text-slate-300 mb-1">
          {aiStatus?.live_ollama ? 'Ollama AI Runtime' : 'AI Diagnostic Engine'}
        </div>
        <div className="text-[11px] text-slate-400">
          Model: {aiStatus?.configured_model || 'qwen2.5-coder:1.5b'}
        </div>
        <div className="text-[11px] mt-1 flex items-center space-x-1">
          <span className={`w-1.5 h-1.5 rounded-full ${aiStatus?.live_ollama ? 'bg-emerald-400' : 'bg-sky-400'}`}></span>
          <span className={aiStatus?.live_ollama ? 'text-emerald-400' : 'text-sky-300'}>
            {aiStatus?.live_ollama ? 'Live Inference Ready' : 'Deterministic Engine'}
          </span>
        </div>
      </div>
    </aside>
  );
};

