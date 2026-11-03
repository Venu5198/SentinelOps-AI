import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Incident } from '../types';
import { Link } from 'react-router-dom';
import { AlertCircle, Filter } from 'lucide-react';

export const IncidentsPage: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchIncidents = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);
      if (severityFilter) params.append('severity', severityFilter);
      const res = await api.get(`/incidents?${params.toString()}`);
      setIncidents(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, [statusFilter, severityFilter]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Incidents</h1>
          <p className="text-sm text-slate-400 mt-1">Lifecycle state management, triage, and investigation tracking.</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center space-x-3 bg-slate-800/40 p-3 rounded-xl border border-slate-800">
        <Filter className="w-4 h-4 text-slate-400" />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-200 px-3 py-1.5 focus:outline-none focus:border-sky-500"
        >
          <option value="">All Statuses</option>
          <option value="DETECTED">DETECTED</option>
          <option value="INVESTIGATING">INVESTIGATING</option>
          <option value="AWAITING_APPROVAL">AWAITING_APPROVAL</option>
          <option value="REMEDIATING">REMEDIATING</option>
          <option value="RESOLVED">RESOLVED</option>
          <option value="FAILED">FAILED</option>
        </select>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-200 px-3 py-1.5 focus:outline-none focus:border-sky-500"
        >
          <option value="">All Severities</option>
          <option value="critical">CRITICAL</option>
          <option value="high">HIGH</option>
          <option value="medium">MEDIUM</option>
          <option value="low">LOW</option>
        </select>
      </div>

      {/* Incidents Table */}
      <div className="bg-slate-800/40 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-850/80 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Incident ID</th>
              <th className="py-3 px-4">Title</th>
              <th className="py-3 px-4">Service</th>
              <th className="py-3 px-4">Severity</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Occurrences</th>
              <th className="py-3 px-4">Detected At</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {incidents.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-500">
                  No incidents matching criteria.
                </td>
              </tr>
            ) : (
              incidents.map((inc) => (
                <tr key={inc.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-medium text-sky-400">{inc.id}</td>
                  <td className="py-3.5 px-4 font-medium text-white">{inc.title}</td>
                  <td className="py-3.5 px-4 font-medium text-slate-200">{inc.service_name}</td>
                  <td className="py-3.5 px-4">
                    <span className={`text-xs px-2 py-0.5 rounded font-semibold ${
                      inc.severity === 'critical' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                      inc.severity === 'high' ? 'bg-orange-950 text-orange-300 border border-orange-800' :
                      'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}>
                      {inc.severity.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-800 text-sky-400 border border-slate-700">
                      {inc.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-center">{inc.occurrence_count}</td>
                  <td className="py-3.5 px-4 text-xs text-slate-400 font-mono">
                    {new Date(inc.detected_at).toLocaleTimeString()}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      to={`/incidents/${inc.id}`}
                      className="text-xs font-semibold px-2.5 py-1 rounded bg-sky-600/20 text-sky-400 hover:bg-sky-600/30 border border-sky-500/30"
                    >
                      Investigate &rarr;
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

