import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Integration, Project } from '../types';
import { Activity, Plus, CheckCircle2, AlertTriangle, RefreshCw, X, ShieldAlert, Cpu } from 'lucide-react';

export const IntegrationsPage: React.FC = () => {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    integration_type: 'prometheus',
    endpoint_url: 'http://prometheus:9090',
    project_id: ''
  });

  const fetchData = async () => {
    try {
      const [integRes, projRes] = await Promise.all([
        api.get('/integrations'),
        api.get('/projects')
      ]);
      setIntegrations(integRes.data);
      setProjects(projRes.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      await api.post(`/integrations/${id}/test`);
      await fetchData();
    } catch (e) {
      console.error(e);
    } finally {
      setTestingId(null);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await api.post('/integrations', {
        ...formData,
        project_id: formData.project_id || null
      });
      await fetchData();
      setIsModalOpen(false);
      setFormData({ name: '', integration_type: 'prometheus', endpoint_url: 'http://prometheus:9090', project_id: '' });
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to connect integration');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Telemetry Integrations</h1>
          <p className="text-sm text-slate-400 mt-1">Connect Prometheus, Loki, Alertmanager, OpenTelemetry, Tempo, and Docker daemons.</p>
        </div>
        <button
          onClick={() => {
            setErrorMsg(null);
            setIsModalOpen(true);
          }}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm transition-colors shadow-lg shadow-sky-900/30"
        >
          <Plus className="w-4 h-4" />
          <span>Connect Integration</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {integrations.map((item) => (
          <div key={item.id} className="p-5 bg-slate-800/40 border border-slate-800 rounded-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-lg bg-sky-950/70 border border-sky-800 flex items-center justify-center text-sky-400">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">{item.name}</h3>
                  <span className="text-xs text-slate-400 font-mono">{item.endpoint_url}</span>
                </div>
              </div>
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold capitalize flex items-center space-x-1.5 ${
                item.status === 'connected' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                item.status === 'degraded' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                'bg-slate-800 text-slate-400 border border-slate-700'
              }`}>
                <span>{item.status}</span>
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs bg-slate-900/60 p-3 rounded-lg border border-slate-800 font-mono">
              <div>
                <span className="text-slate-500 block">Type:</span>
                <span className="text-slate-200 uppercase">{item.integration_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Scope:</span>
                <span className="text-slate-200">{item.project_id ? 'Project-Specific' : 'Global / Org'}</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-[11px] text-slate-500">
                {item.last_checked_at ? `Checked ${new Date(item.last_checked_at).toLocaleTimeString()}` : 'Not tested'}
              </span>
              <button
                onClick={() => handleTest(item.id)}
                disabled={testingId === item.id}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testingId === item.id ? 'animate-spin' : ''}`} />
                <span>Test Connection</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Connect Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl relative">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white">Connect Telemetry Source</h3>
              <button onClick={() => setIsModalOpen(false)} className="p-1.5 rounded-lg text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {errorMsg && (
              <div className="mt-4 p-3 bg-rose-950/50 border border-rose-800 rounded-lg text-rose-300 text-xs">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleCreate} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Integration Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Cluster Prometheus or Loki Prod"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">Telemetry Type</label>
                  <select
                    value={formData.integration_type}
                    onChange={(e) => setFormData({ ...formData, integration_type: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:border-sky-500"
                  >
                    <option value="prometheus">Prometheus (Metrics)</option>
                    <option value="loki">Grafana Loki (Logs)</option>
                    <option value="alertmanager">Alertmanager (Alerts)</option>
                    <option value="tempo">Grafana Tempo (Traces)</option>
                    <option value="docker">Docker Daemon</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">Project Scope</label>
                  <select
                    value={formData.project_id}
                    onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:border-sky-500"
                  >
                    <option value="">Global (All Projects)</option>
                    {projects.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Endpoint URL *</label>
                <input
                  type="text"
                  required
                  placeholder="http://prometheus:9090 or http://loki:3100"
                  value={formData.endpoint_url}
                  onChange={(e) => setFormData({ ...formData, endpoint_url: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm font-mono focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold"
                >
                  Save Integration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
