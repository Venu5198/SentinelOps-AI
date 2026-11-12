import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Terminal, Search, RefreshCw, Filter, Layers } from 'lucide-react';

export const TelemetryExplorerPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'metrics' | 'logs' | 'traces'>('logs');
  const [query, setQuery] = useState('{job="sentinelops"}');
  const [logResults, setLogResults] = useState<any[]>([]);
  const [metricResults, setMetricResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleQuery = async () => {
    setLoading(true);
    try {
      if (activeTab === 'logs') {
        const res = await api.get('/telemetry/logs', { params: { query } });
        setLogResults(res.data?.result || []);
      } else if (activeTab === 'metrics') {
        const res = await api.get('/telemetry/metrics', { params: { query: query.startsWith('{') ? 'up' : query } });
        setMetricResults(res.data?.result || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleQuery();
  }, [activeTab]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Telemetry & Observability Explorer</h1>
          <p className="text-sm text-slate-400 mt-1">Direct PromQL and LogQL exploration across Prometheus and Loki clusters.</p>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center space-x-1.5 bg-slate-900 p-1.5 rounded-lg border border-slate-800">
          <button
            onClick={() => {
              setActiveTab('logs');
              setQuery('{job="sentinelops"}');
            }}
            className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              activeTab === 'logs' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Loki Logs
          </button>
          <button
            onClick={() => {
              setActiveTab('metrics');
              setQuery('up');
            }}
            className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              activeTab === 'metrics' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Prometheus Metrics
          </button>
          <button
            onClick={() => setActiveTab('traces')}
            className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              activeTab === 'traces' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            OpenTelemetry Traces
          </button>
        </div>
      </div>

      {/* Query Bar */}
      <div className="flex items-center space-x-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            placeholder={activeTab === 'logs' ? '{job="sentinelops"} or {service="payment-service"}' : 'up or rate(http_requests_total[5m])'}
            className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white font-mono text-sm focus:outline-none focus:border-sky-500"
          />
        </div>
        <button
          onClick={handleQuery}
          disabled={loading}
          className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center space-x-2 transition-colors"
        >
          {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Terminal className="w-3.5 h-3.5" />}
          <span>Execute Query</span>
        </button>
      </div>

      {/* Results View */}
      {activeTab === 'logs' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs overflow-x-auto min-h-[350px]">
          {logResults.length === 0 ? (
            <div className="text-slate-500 p-8 text-center">
              No log stream matched query: <code className="text-slate-400">{query}</code>
            </div>
          ) : (
            <div className="space-y-1">
              {logResults.map((stream, idx) => (
                <div key={idx} className="space-y-1 border-b border-slate-800/60 pb-2 mb-2">
                  <div className="text-sky-400 font-bold">{JSON.stringify(stream.stream)}</div>
                  {stream.values?.map((val: any, vIdx: number) => (
                    <div key={vIdx} className="text-slate-300 hover:bg-slate-800/40 px-2 py-0.5 rounded">
                      <span className="text-slate-500 mr-2">{new Date(val[0] / 1000000).toLocaleTimeString()}</span>
                      <span>{val[1]}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'metrics' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs overflow-x-auto min-h-[350px]">
          {metricResults.length === 0 ? (
            <div className="text-slate-500 p-8 text-center">
              No vector metrics returned for query: <code className="text-slate-400">{query}</code>
            </div>
          ) : (
            <div className="space-y-2">
              {metricResults.map((m, idx) => (
                <div key={idx} className="p-3 bg-slate-800/40 border border-slate-800 rounded-lg flex items-center justify-between">
                  <div className="text-slate-300">
                    <span className="font-bold text-sky-400">{m.metric?.__name__ || 'metric'}</span>
                    <span className="text-slate-400 ml-2">{JSON.stringify(m.metric)}</span>
                  </div>
                  <div className="font-bold text-emerald-400 text-sm px-3 py-1 bg-emerald-950/60 rounded border border-emerald-800">
                    {m.value?.[1]}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'traces' && (
        <div className="p-12 text-center text-slate-400 border border-dashed border-slate-800 rounded-xl bg-slate-800/20">
          <Layers className="w-10 h-10 text-slate-500 mx-auto mb-3" />
          <p className="text-sm font-semibold text-white">OpenTelemetry Traces & Spans</p>
          <p className="text-xs text-slate-400 mt-1">Trace receiver is ready. Instrument services using OpenTelemetry SDK to view distributed waterfall traces.</p>
        </div>
      )}
    </div>
  );
};
