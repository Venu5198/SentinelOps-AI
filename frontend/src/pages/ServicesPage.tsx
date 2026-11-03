import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Service } from '../types';
import { Server, RefreshCw, CheckCircle2, AlertTriangle } from 'lucide-react';

export const ServicesPage: React.FC = () => {
  const [services, setServices] = useState<Service[]>([]);
  const [probing, setProbing] = useState<Record<string, boolean>>({});

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Monitored Services</h1>
        <p className="text-sm text-slate-400 mt-1">Application registry, endpoint probes, and telemetry status.</p>
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
                  <h2 className="text-base font-bold text-white">{svc.name}</h2>
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
    </div>
  );
};

