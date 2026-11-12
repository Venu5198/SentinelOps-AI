import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { Project, Service, Incident, Environment } from '../types';
import { 
  Server, AlertCircle, CheckCircle2, RefreshCw, Activity, 
  Layers, ShieldAlert, Cpu, HardDrive, ArrowLeft, Plus, Globe
} from 'lucide-react';

export const ProjectDashboardPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [data, setData] = useState<{
    project: Project;
    environments: Environment[];
    services: Service[];
    incidents: Incident[];
    metrics: any;
  } | null>(null);
  const [selectedEnv, setSelectedEnv] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  const fetchDashboard = async () => {
    if (!projectId) return;
    try {
      const res = await api.get(`/dashboard/project/${projectId}`);
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 8000);
    return () => clearInterval(interval);
  }, [projectId]);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 text-sky-400 animate-spin" />
      </div>
    );
  }

  const filteredServices = selectedEnv === 'all' 
    ? data.services 
    : data.services.filter(s => s.environment.toLowerCase() === selectedEnv.toLowerCase());

  const filteredIncidents = selectedEnv === 'all'
    ? data.incidents
    : data.incidents.filter(i => (i.environment || 'local').toLowerCase() === selectedEnv.toLowerCase());

  return (
    <div className="space-y-6">
      {/* Top Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2 text-xs text-slate-400 mb-1">
            <Link to="/projects" className="hover:text-sky-400 flex items-center space-x-1">
              <ArrowLeft className="w-3 h-3" />
              <span>Projects</span>
            </Link>
            <span>/</span>
            <span className="text-slate-200">{data.project.name}</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
            <span>{data.project.name}</span>
            <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold capitalize ${
              data.metrics.degraded_services === 0 ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
              'bg-rose-950 text-rose-300 border border-rose-800'
            }`}>
              {data.metrics.degraded_services === 0 ? 'Operational' : 'Degraded'}
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-mono">{data.project.slug} | {data.project.description || 'Dedicated telemetry & incident cockpit'}</p>
        </div>

        {/* Environment Filter Buttons */}
        <div className="flex items-center space-x-1.5 bg-slate-900 p-1.5 rounded-lg border border-slate-800 self-start sm:self-auto">
          <button
            onClick={() => setSelectedEnv('all')}
            className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
              selectedEnv === 'all' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            All Environments
          </button>
          {data.environments.map(env => (
            <button
              key={env.id}
              onClick={() => setSelectedEnv(env.slug)}
              className={`px-3 py-1 rounded text-xs font-semibold capitalize transition-colors ${
                selectedEnv === env.slug ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {env.name}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Services</div>
          <div className="text-3xl font-extrabold text-white mt-2">{filteredServices.length}</div>
          <div className="text-xs text-emerald-400 mt-1">{filteredServices.filter(s => s.health_status === 'healthy').length} operational</div>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Degraded Services</div>
          <div className="text-3xl font-extrabold text-white mt-2">
            {filteredServices.filter(s => ['degraded', 'unhealthy'].includes(s.health_status)).length}
          </div>
          <div className="text-xs text-rose-400 mt-1">Requires inspection</div>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Active Incidents</div>
          <div className="text-3xl font-extrabold text-white mt-2">
            {filteredIncidents.filter(i => !['RESOLVED', 'CLOSED'].includes(i.status)).length}
          </div>
          <div className="text-xs text-amber-400 mt-1">Under AI diagnosis</div>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Observability Scope</div>
          <div className="text-3xl font-extrabold text-white mt-2">Prometheus</div>
          <div className="text-xs text-sky-400 mt-1">Metrics + Loki Logs</div>
        </div>
      </div>

      {/* Services and Incidents Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Project Services */}
        <div className="lg:col-span-2 bg-slate-800/40 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center space-x-2">
              <Server className="w-4 h-4 text-sky-400" />
              <span>Project Services ({filteredServices.length})</span>
            </h2>
            <Link to="/services" className="text-xs text-sky-400 hover:text-sky-300">
              Manage in Registry &rarr;
            </Link>
          </div>

          <div className="space-y-3">
            {filteredServices.length === 0 ? (
              <div className="p-8 text-center text-slate-400 border border-dashed border-slate-800 rounded-lg">
                No services registered under this environment filter.
              </div>
            ) : (
              filteredServices.map(svc => (
                <div key={svc.id} className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg flex items-center justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-white text-sm">{svc.name}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 uppercase font-mono">
                        {svc.environment}
                      </span>
                    </div>
                    <span className="text-xs text-slate-400 font-mono mt-0.5 block">{svc.endpoint_url}</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-semibold capitalize ${
                      svc.health_status === 'healthy' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                      'bg-rose-950 text-rose-300 border border-rose-800'
                    }`}>
                      {svc.health_status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Project Incidents Feed */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-5">
          <h2 className="font-semibold text-white mb-4 flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <span>Incidents & RCA</span>
          </h2>
          <div className="space-y-3">
            {filteredIncidents.length === 0 ? (
              <div className="p-6 text-center text-slate-400 border border-dashed border-slate-800 rounded-lg text-xs">
                Zero incidents for this project. System healthy!
              </div>
            ) : (
              filteredIncidents.slice(0, 5).map(inc => (
                <Link
                  key={inc.id}
                  to={`/incidents/${inc.id}`}
                  className="block p-3 bg-slate-900/60 border border-slate-800 hover:border-slate-700 rounded-lg transition-colors"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-slate-400">{inc.id}</span>
                    <span className="text-rose-400 font-bold uppercase">{inc.severity}</span>
                  </div>
                  <div className="text-sm font-semibold text-white mt-1">{inc.title}</div>
                  <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
                    <span>{inc.service_name}</span>
                    <span className="text-sky-400">{inc.status}</span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
