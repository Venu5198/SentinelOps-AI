import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Incident, Service } from '../types';
import { AlertCircle, CheckCircle2, Clock, Server, ArrowRight, ShieldAlert, Activity } from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [incRes, svcRes] = await Promise.all([
        api.get('/incidents?limit=10'),
        api.get('/services')
      ]);
      setIncidents(incRes.data);
      setServices(svcRes.data);
    } catch (e) {
      console.error('Failed to load dashboard data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 8000);
    return () => clearInterval(interval);
  }, []);

  const activeIncidents = incidents.filter(
    (i) => !['RESOLVED', 'CLOSED'].includes(i.status)
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Operations Overview</h1>
        <p className="text-sm text-slate-400 mt-1">Real-time telemetry, active incidents, and automated AI diagnostics.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Incidents</span>
            <AlertCircle className={`w-5 h-5 ${activeIncidents.length > 0 ? 'text-rose-400' : 'text-slate-500'}`} />
          </div>
          <div className="text-3xl font-extrabold text-white mt-3">{activeIncidents.length}</div>
          <div className="text-xs text-slate-400 mt-1">Requires immediate attention</div>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Monitored Services</span>
            <Server className="w-5 h-5 text-sky-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-3">{services.length}</div>
          <div className="text-xs text-emerald-400 mt-1 flex items-center space-x-1">
            <span>{services.filter(s => s.health_status === 'healthy').length} healthy</span>
          </div>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Awaiting Approval</span>
            <Clock className="w-5 h-5 text-amber-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-3">
            {incidents.filter(i => i.status === 'AWAITING_APPROVAL').length}
          </div>
          <div className="text-xs text-amber-400 mt-1">Remediations proposed by AI</div>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Resolved Today</span>
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-3">
            {incidents.filter(i => i.status === 'RESOLVED').length}
          </div>
          <div className="text-xs text-slate-400 mt-1">Recovery verified</div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Incidents Feed */}
        <div className="lg:col-span-2 bg-slate-800/40 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h2 className="font-semibold text-white flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-sky-400" />
              <span>Active Incidents</span>
            </h2>
            <Link to="/incidents" className="text-xs text-sky-400 hover:text-sky-300 flex items-center space-x-1">
              <span>View all</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="divide-y divide-slate-800/60">
            {activeIncidents.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-80" />
                <p className="text-sm font-medium">All infrastructure systems operating normally.</p>
                <p className="text-xs text-slate-500 mt-1">Zero active incidents detected.</p>
              </div>
            ) : (
              activeIncidents.map((inc) => (
                <Link
                  key={inc.id}
                  to={`/incidents/${inc.id}`}
                  className="p-4 block hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {inc.id}
                      </span>
                      <span className="text-sm font-semibold text-white">{inc.title}</span>
                    </div>
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                      inc.severity === 'critical' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                      inc.severity === 'high' ? 'bg-orange-950 text-orange-300 border border-orange-800' :
                      'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}>
                      {inc.severity.toUpperCase()}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center space-x-4 text-xs text-slate-400">
                    <span>Service: <strong className="text-slate-200">{inc.service_name}</strong></span>
                    <span>State: <strong className="text-sky-400">{inc.status}</strong></span>
                    <span>Occurrences: {inc.occurrence_count}</span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Monitored Services Quick View */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-4">
          <h2 className="font-semibold text-white mb-3 flex items-center space-x-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span>Monitored Services</span>
          </h2>
          <div className="space-y-2.5">
            {services.map((svc) => (
              <div key={svc.id} className="p-3 bg-slate-800/60 rounded-lg border border-slate-700/50 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">{svc.name}</div>
                  <div className="text-xs text-slate-400 font-mono mt-0.5">{svc.endpoint_url}</div>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className={`w-2 h-2 rounded-full ${
                    svc.health_status === 'healthy' ? 'bg-emerald-400' :
                    svc.health_status === 'degraded' ? 'bg-amber-400' : 'bg-rose-400'
                  }`}></span>
                  <span className="text-xs font-medium text-slate-300 capitalize">{svc.health_status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

