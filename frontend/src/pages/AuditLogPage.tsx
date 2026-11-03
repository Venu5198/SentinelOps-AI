import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { AuditLog } from '../types';
import { Shield, FileText } from 'lucide-react';

export const AuditLogPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await api.get('/audit?limit=100');
        setLogs(res.data);
      } catch (e) {
        console.error(e);
      }
    };
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Audit Trail & Compliance</h1>
        <p className="text-sm text-slate-400 mt-1">Immutable journal of security events, approvals, and remediation actions.</p>
      </div>

      <div className="bg-slate-800/40 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-850/80 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4">Action</th>
              <th className="py-3 px-4">Actor</th>
              <th className="py-3 px-4">Resource</th>
              <th className="py-3 px-4">Result</th>
              <th className="py-3 px-4">Correlation ID</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-slate-800/30">
                <td className="py-3 px-4 text-slate-400">{new Date(log.timestamp).toLocaleString()}</td>
                <td className="py-3 px-4 font-bold text-sky-400">{log.action}</td>
                <td className="py-3 px-4 text-slate-200">
                  {log.actor_id} <span className="text-slate-500 font-normal">({log.actor_role})</span>
                </td>
                <td className="py-3 px-4 text-slate-300">{log.resource_type}/{log.resource_id}</td>
                <td className="py-3 px-4">
                  <span className={`px-2 py-0.5 rounded uppercase font-semibold ${
                    log.result === 'success' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-rose-950 text-rose-400 border border-rose-800'
                  }`}>
                    {log.result}
                  </span>
                </td>
                <td className="py-3 px-4 text-slate-500">{log.correlation_id || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

