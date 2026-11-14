import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Service } from '../types';
import { Server, RefreshCw, Plus, X, Globe, AlertCircle, CheckCircle2 } from 'lucide-react';

export const ServicesPage: React.FC = () => {
  const [services, setServices] = useState<Service[]>([]);
  const [probing, setProbing] = useState<Record<string, boolean>>({});
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    environment: 'local',
    endpoint_url: 'http://host.docker.internal:8000',
    health_endpoint: '/health',
    monitoring_enabled: true
  });

  const fetchServices = async () => {
    try {
      const res = await api.get('/services');
      setServices(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchServices();
  }, []);

  const handleProbe = async (id: string) => {
    setProbing(prev => ({ ...prev, [id]: true }));
    try {
      await api.post(`/services/${id}/check-health`);
      await fetchServices();
    } catch (e) {
      console.error(e);
    } finally {
      setProbing(prev => ({ ...prev, [id]: false }));
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await api.post('/services', formData);
      setSuccessMsg(`Service "${formData.name}" successfully registered!`);
      await fetchServices();
      setTimeout(() => {
        setIsModalOpen(false);
        setSuccessMsg(null);
        setFormData({
          name: '',
          environment: 'local',
          endpoint_url: 'http://host.docker.internal:8000',
          health_endpoint: '/health',
          monitoring_enabled: true
        });
      }, 1000);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to register service. Check inputs.';
      setErrorMsg(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Monitored Services</h1>
          <p className="text-sm text-slate-400 mt-1">Application registry, endpoint probes, and telemetry status.</p>
        </div>
        <button
          onClick={() => {
            setErrorMsg(null);
            setSuccessMsg(null);
            setIsModalOpen(true);
          }}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm transition-colors shadow-lg shadow-sky-900/30 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Register Service</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {services.map((svc) => (
          <div key={svc.id} className="bg-slate-800/40 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-lg bg-sky-950/60 border border-sky-800 flex items-center justify-center text-sky-400">
                  <Server className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h2 className="text-base font-bold text-white">{svc.name}</h2>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono uppercase">
                      {svc.environment}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">{svc.endpoint_url}</span>
                </div>
              </div>
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold flex items-center space-x-1.5 ${
                svc.health_status === 'healthy' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                svc.health_status === 'degraded' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                'bg-rose-950 text-rose-300 border border-rose-800'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${
                  svc.health_status === 'healthy' ? 'bg-emerald-400' :
                  svc.health_status === 'degraded' ? 'bg-amber-400' : 'bg-rose-400'
                }`}></span>
                <span className="capitalize">{svc.health_status}</span>
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs bg-slate-900/60 p-3 rounded-lg border border-slate-800 font-mono">
              <div>
                <span className="text-slate-500 block">Health Path:</span>
                <span className="text-slate-300">{svc.health_endpoint}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Last Check:</span>
                <span className="text-slate-300">
                  {svc.last_check_at ? new Date(svc.last_check_at).toLocaleTimeString() : 'Never'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                onClick={() => handleProbe(svc.id)}
                disabled={probing[svc.id]}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${probing[svc.id] ? 'animate-spin' : ''}`} />
                <span>Probe Health</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Register Service Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl relative">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-sky-950 border border-sky-800 flex items-center justify-center text-sky-400">
                  <Globe className="w-4 h-4" />
                </div>
                <h3 className="text-lg font-bold text-white">Register Monitored Service</h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {errorMsg && (
              <div className="mt-4 p-3 bg-rose-950/50 border border-rose-800/80 rounded-lg text-rose-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{errorMsg}</span>
              </div>
            )}

            {successMsg && (
              <div className="mt-4 p-3 bg-emerald-950/50 border border-emerald-800/80 rounded-lg text-emerald-300 text-xs flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                <span>{successMsg}</span>
              </div>
            )}

            <form onSubmit={handleRegister} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Service Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. prd-backend or payment-service"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-sky-500 transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Environment
                  </label>
                  <select
                    value={formData.environment}
                    onChange={(e) => setFormData({ ...formData, environment: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:border-sky-500"
                  >
                    <option value="local">Local</option>
                    <option value="development">Development</option>
                    <option value="staging">Staging</option>
                    <option value="production">Production</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Health Path
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="/health"
                    value={formData.health_endpoint}
                    onChange={(e) => setFormData({ ...formData, health_endpoint: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white placeholder-slate-500 text-sm font-mono focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Endpoint URL <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="http://host.docker.internal:8000"
                  value={formData.endpoint_url}
                  onChange={(e) => setFormData({ ...formData, endpoint_url: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white placeholder-slate-500 text-sm font-mono focus:outline-none focus:border-sky-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Tip: Use <code className="text-slate-400 font-mono">http://host.docker.internal:PORT</code> to target services running on your host machine.
                </p>
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="monitoring_enabled"
                  checked={formData.monitoring_enabled}
                  onChange={(e) => setFormData({ ...formData, monitoring_enabled: e.target.checked })}
                  className="rounded bg-slate-800 border-slate-700 text-sky-600 focus:ring-0"
                />
                <label htmlFor="monitoring_enabled" className="text-xs text-slate-300 cursor-pointer">
                  Enable active probing & telemetry monitoring
                </label>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors flex items-center space-x-2"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Registering...</span>
                    </>
                  ) : (
                    <span>Register Service</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
