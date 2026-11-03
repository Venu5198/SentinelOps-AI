import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Incident, Evidence, Investigation, Approval } from '../types';
import { 
  AlertTriangle, BrainCircuit, CheckCircle2, ShieldCheck, 
  XCircle, Clock, FileText, ArrowLeft, RefreshCw, Zap
} from 'lucide-react';

export const IncidentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [remediating, setRemediating] = useState(false);

  const fetchDetails = async () => {
    if (!id) return;
    try {
      const [incRes, eviRes, invRes, appRes] = await Promise.allSettled([
        api.get(`/incidents/${id}`),
        api.get(`/incidents/${id}/evidence`),
        api.get(`/incidents/${id}/investigations/latest`),
        api.get(`/approvals?incident_id=${id}`)
      ]);

      if (incRes.status === 'fulfilled') setIncident(incRes.value.data);
      if (eviRes.status === 'fulfilled') setEvidence(eviRes.value.data);
      if (invRes.status === 'fulfilled') setInvestigation(invRes.value.data);
      if (appRes.status === 'fulfilled') setApprovals(appRes.value.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
    const interval = setInterval(fetchDetails, 5000);
    return () => clearInterval(interval);
  }, [id]);

  const handleTriggerInvestigation = async () => {
    setInvestigating(true);
    try {
      await api.post(`/incidents/${id}/investigations`);
      await fetchDetails();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Investigation failed');
    } finally {
      setInvestigating(false);
    }
  };

  const handleApprove = async (approvalId: string) => {
    try {
      await api.post(`/approvals/${approvalId}/decide`, {
        decision: 'APPROVED',
        reason: 'Authorized operator approved remediation via Web UI'
      });
      await fetchDetails();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Approval failed');
    }
  };

  const handleReject = async (approvalId: string) => {
    const reason = prompt('Please enter rejection reason:');
    if (!reason) return;
    try {
      await api.post(`/approvals/${approvalId}/decide`, {
        decision: 'REJECTED',
        reason: reason
      });
      await fetchDetails();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Rejection failed');
    }
  };

  const handleExecute = async (approvalId: string) => {
    setRemediating(true);
    try {
      await api.post('/remediations/execute', {
        incident_id: id,
        approval_id: approvalId
      });
      alert('Remediation action executed. Recovery verification is running.');
      await fetchDetails();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Execution failed');
    } finally {
      setRemediating(false);
    }
  };

  if (loading || !incident) {
    return <div className="p-8 text-center text-slate-400">Loading incident context...</div>;
  }

  const latestApproval = approvals.length > 0 ? approvals[0] : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <button
          onClick={() => navigate('/incidents')}
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">{incident.title}</h1>
            <span className="font-mono text-xs px-2.5 py-0.5 rounded bg-slate-800 text-sky-400 border border-slate-700">
              {incident.id}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Service: <strong className="text-slate-200">{incident.service_name}</strong> &bull; Fingerprint: <span className="font-mono">{incident.fingerprint}</span>
          </p>
        </div>
      </div>

      {/* Status Bar */}
      <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-6 text-sm">
          <div>
            <span className="text-xs text-slate-400 block">Severity</span>
            <span className="font-bold uppercase text-rose-400">{incident.severity}</span>
          </div>
          <div>
            <span className="text-xs text-slate-400 block">Current Lifecycle</span>
            <span className="font-bold text-sky-400">{incident.status}</span>
          </div>
          <div>
            <span className="text-xs text-slate-400 block">Detected</span>
            <span className="text-slate-300 font-mono text-xs">{new Date(incident.detected_at).toLocaleString()}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleTriggerInvestigation}
            disabled={investigating}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-md shadow-sky-600/30 transition-colors disabled:opacity-50"
          >
            <BrainCircuit className="w-4 h-4" />
            <span>{investigating ? 'Investigating...' : 'Run AI Investigation'}</span>
          </button>
        </div>
      </div>

      {/* AI Diagnostic Investigation Report */}
      {investigation && (
        <div className="bg-slate-800/40 border border-sky-500/30 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between pb-3 border-b border-slate-700/60 mb-4">
            <div className="flex items-center space-x-2.5">
              <BrainCircuit className="w-5 h-5 text-sky-400" />
              <h2 className="text-base font-bold text-white">AI Diagnostic Report</h2>
              <span className="text-xs font-mono text-slate-400">({investigation.model_name})</span>
            </div>
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-slate-400">Confidence Score:</span>
              <span className="px-2 py-0.5 rounded font-bold bg-sky-950 text-sky-300 border border-sky-800">
                {(investigation.report.confidence_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Executive Summary</h3>
              <p className="text-sm text-slate-200">{investigation.report.incident_summary}</p>
            </div>

            <div>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Probable Root Cause Hypotheses</h3>
              <div className="space-y-2">
                {investigation.report.probable_root_causes.map((rc, idx) => (
                  <div key={idx} className="p-3 bg-slate-850 rounded-lg border border-slate-700/60 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white">{rc.hypothesis}</span>
                      <span className="text-xs px-2 py-0.5 rounded uppercase font-semibold bg-rose-950 text-rose-300 border border-rose-800">
                        {rc.likelihood} likelihood
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1">{rc.explanation}</p>
                    <div className="mt-2 text-xs text-sky-400">
                      Cited Evidence IDs: {rc.cited_evidence_ids.join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Proposed Remediation & Approval Gate */}
            {latestApproval && (
              <div className="mt-5 p-4 rounded-xl bg-slate-900 border border-amber-500/40">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="w-5 h-5 text-amber-400" />
                    <span className="text-sm font-bold text-white">Human Approval Gate</span>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded font-bold uppercase ${
                    latestApproval.status === 'APPROVED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                    latestApproval.status === 'REJECTED' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                    'bg-amber-950 text-amber-300 border border-amber-800 animate-pulse'
                  }`}>
                    {latestApproval.status}
                  </span>
                </div>

                <div className="text-xs text-slate-300 space-y-1">
                  <div>Action: <strong className="font-mono text-white">{latestApproval.action_id}</strong> on <strong>{latestApproval.target_service}</strong></div>
                  <div>Rationale: {latestApproval.rationale}</div>
                  <div>Risk: <span className="font-semibold text-amber-400">{latestApproval.risk_level}</span></div>
                  <div className="text-[11px] text-slate-500 font-mono">Signature: {latestApproval.action_signature}</div>
                </div>

                {latestApproval.status === 'PENDING' && (
                  <div className="mt-3 flex items-center space-x-3">
                    <button
                      onClick={() => handleApprove(latestApproval.id)}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center space-x-1"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Approve Remediation</span>
                    </button>
                    <button
                      onClick={() => handleReject(latestApproval.id)}
                      className="px-3 py-1.5 rounded-lg bg-rose-600/30 hover:bg-rose-600/50 text-rose-300 border border-rose-600/50 text-xs font-semibold flex items-center space-x-1"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>
                )}

                {latestApproval.status === 'APPROVED' && incident.status !== 'RESOLVED' && (
                  <div className="mt-3">
                    <button
                      onClick={() => handleExecute(latestApproval.id)}
                      disabled={remediating}
                      className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-md shadow-sky-600/30"
                    >
                      <Zap className="w-3.5 h-3.5" />
                      <span>{remediating ? 'Executing...' : 'Execute Restricted Remediation'}</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Evidence Artifacts */}
      <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-5">
        <h2 className="text-base font-bold text-white mb-3 flex items-center space-x-2">
          <FileText className="w-4 h-4 text-sky-400" />
          <span>Diagnostic Evidence ({evidence.length})</span>
        </h2>
        <div className="space-y-3">
          {evidence.map((ev) => (
            <div key={ev.id} className="p-3 bg-slate-850 rounded-lg border border-slate-700/60 text-xs">
              <div className="flex items-center justify-between font-mono mb-1">
                <span className="text-sky-400 font-bold">[{ev.source.toUpperCase()}] {ev.name}</span>
                <span className="text-slate-500">{new Date(ev.observed_at).toLocaleTimeString()}</span>
              </div>
              <p className="text-slate-300 mb-2">{ev.summary}</p>
              <pre className="bg-slate-900 p-2 rounded text-[11px] font-mono text-slate-400 overflow-x-auto">
                {JSON.stringify(ev.payload, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

