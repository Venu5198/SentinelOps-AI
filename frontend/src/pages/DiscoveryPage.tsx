import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { DiscoveredService, Project } from '../types';
import { Scan, RefreshCw, CheckCircle2, Server, ArrowRight, ShieldCheck, X } from 'lucide-react';

export const DiscoveryPage: React.FC = () => {
  const [discovered, setDiscovered] = useState<DiscoveredService[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [scanning, setScanning] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<string>('proj_sentinelops_default');

  const fetchDiscovered = async () => {
    try {
      const [discRes, projRes] = await Promise.all([
        api.get('/discovery'),
        api.get('/projects')
      ]);
      setDiscovered(discRes.data);
      setProjects(projRes.data);
      if (projRes.data.length > 0) {
        setSelectedProject(projRes.data[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchDiscovered();
  }, []);

  const handleScanDocker = async () => {
    setScanning(true);
    try {
      const res = await api.post('/discovery/scan-docker');
      setDiscovered(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setScanning(false);
    }
  };

  const handleApprove = async (item: DiscoveredService) => {
    setApprovingId(item.id);
    try {
      await api.post(`/discovery/${item.id}/approve`, {
        project_id: selectedProject,
        environment: 'local',
        health_endpoint: item.detected_health_path || '/health',
        endpoint_url: item.detected_endpoints[0] || 'http://host.docker.internal:8000'
      });
      await fetchDiscovered();
    } catch (e) {
      console.error(e);
    } finally {
      setApprovingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Automated Service Discovery</h1>
          <p className="text-sm text-slate-400 mt-1">Scan Docker daemon & Kubernetes workloads, inspect open ports, and onboard to projects.</p>
        </div>
        <button
          onClick={handleScanDocker}
          disabled={scanning}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-medium text-sm transition-colors shadow-lg shadow-sky-900/30"
        >
          <Scan className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
          <span>{scanning ? 'Scanning Docker Socket...' : 'Scan Local Docker'}</span>
        </button>
      </div>

      <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <span className="text-xs font-semibold text-slate-300">Assign Approved Services to Project:</span>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-white text-xs font-medium focus:outline-none focus:border-sky-500"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name} ({p.slug})</option>
            ))}
          </select>
        </div>
        <div className="text-xs text-slate-400">
          Discovered: <strong className="text-white">{discovered.length}</strong>
        </div>
      </div>

      {/* Discovery Items List */}
      <div className="space-y-3">
        {discovered.length === 0 ? (
          <div className="p-12 text-center text-slate-400 border border-dashed border-slate-800 rounded-xl bg-slate-800/20">
            <Scan className="w-10 h-10 text-slate-500 mx-auto mb-3" />
            <p className="text-sm font-semibold text-white">No external containers discovered yet</p>
            <p className="text-xs text-slate-400 mt-1">Click "Scan Local Docker" above to inspect all running containers on your host machine.</p>
          </div>
        ) : (
          discovered.map((item) => (
            <div key={item.id} className="p-5 bg-slate-800/40 border border-slate-800 rounded-xl flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <h3 className="text-base font-bold text-white">{item.name}</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800 uppercase font-mono">
                    {item.source}
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-mono ${
                    item.status === 'approved' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                    'bg-slate-800 text-slate-400 border border-slate-700'
                  }`}>
                    {item.status}
                  </span>
                </div>
                <div className="text-xs text-slate-400 font-mono flex items-center space-x-4">
                  <span>Image: <strong className="text-slate-300">{item.image}</strong></span>
                  {item.detected_endpoints.length > 0 && (
                    <span>Endpoints: <strong className="text-sky-300">{item.detected_endpoints.join(', ')}</strong></span>
                  )}
                </div>
              </div>

              <div>
                {item.status === 'approved' ? (
                  <span className="inline-flex items-center space-x-1.5 text-xs text-emerald-400 font-medium">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Registered in Service Fleet</span>
                  </span>
                ) : (
                  <button
                    onClick={() => handleApprove(item)}
                    disabled={approvingId === item.id}
                    className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors"
                  >
                    {approvingId === item.id ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                    <span>Approve & Onboard</span>
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
