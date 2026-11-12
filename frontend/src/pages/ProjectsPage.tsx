import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Project, Organization } from '../types';
import { FolderKanban, Plus, Server, AlertCircle, CheckCircle2, ArrowRight, ShieldCheck, Layers, X, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';

export const ProjectsPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    description: '',
    organization_id: 'org_default'
  });

  const fetchData = async () => {
    try {
      const [projRes, orgRes] = await Promise.all([
        api.get('/projects'),
        api.get('/organizations')
      ]);
      setProjects(projRes.data);
      setOrganizations(orgRes.data);
    } catch (e) {
      console.error('Failed to load projects', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await api.post('/projects', formData);
      await fetchData();
      setIsModalOpen(false);
      setFormData({ name: '', slug: '', description: '', organization_id: organizations[0]?.id || 'org_default' });
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Software Projects</h1>
          <p className="text-sm text-slate-400 mt-1">Multi-project portfolio, environment isolation, and dedicated observability dashboards.</p>
        </div>
        <button
          onClick={() => {
            setErrorMsg(null);
            setIsModalOpen(true);
          }}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm transition-colors shadow-lg shadow-sky-900/30"
        >
          <Plus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {projects.map((proj) => (
          <div key={proj.id} className="bg-slate-800/40 border border-slate-800 hover:border-slate-700/80 rounded-xl p-5 flex flex-col justify-between transition-all group">
            <div>
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-lg bg-sky-950/70 border border-sky-800 flex items-center justify-center text-sky-400">
                  <FolderKanban className="w-5 h-5" />
                </div>
                <span className={`text-xs px-2.5 py-1 rounded-full font-semibold flex items-center space-x-1.5 ${
                  proj.health_status === 'healthy' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                  'bg-rose-950 text-rose-300 border border-rose-800'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    proj.health_status === 'healthy' ? 'bg-emerald-400' : 'bg-rose-400'
                  }`}></span>
                  <span className="capitalize">{proj.health_status}</span>
                </span>
              </div>

              <div className="mt-4">
                <h2 className="text-lg font-bold text-white group-hover:text-sky-300 transition-colors">{proj.name}</h2>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">{proj.description || 'No description provided.'}</p>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-2 text-xs bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-500 block">Services:</span>
                  <span className="text-white font-semibold flex items-center space-x-1 mt-0.5">
                    <Server className="w-3.5 h-3.5 text-sky-400" />
                    <span>{proj.services_count} active</span>
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Incidents:</span>
                  <span className={`font-semibold flex items-center space-x-1 mt-0.5 ${
                    proj.active_incidents_count > 0 ? 'text-rose-400' : 'text-slate-300'
                  }`}>
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{proj.active_incidents_count} open</span>
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between">
              <span className="text-[11px] font-mono text-slate-500 uppercase">{proj.slug}</span>
              <Link
                to={`/projects/${proj.id}`}
                className="inline-flex items-center space-x-1.5 text-xs font-semibold text-sky-400 hover:text-sky-300 transition-colors"
              >
                <span>Project Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        ))}
      </div>

      {/* New Project Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl relative">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-sky-950 border border-sky-800 flex items-center justify-center text-sky-400">
                  <FolderKanban className="w-4 h-4" />
                </div>
                <h3 className="text-lg font-bold text-white">Create New Project</h3>
              </div>
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
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Project Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. E-Commerce Platform or PRD Engine"
                  value={formData.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)+/g, '');
                    setFormData({ ...formData, name, slug });
                  }}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Slug Identifier *</label>
                <input
                  type="text"
                  required
                  value={formData.slug}
                  onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm font-mono focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Organization</label>
                <select
                  value={formData.organization_id}
                  onChange={(e) => setFormData({ ...formData, organization_id: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:border-sky-500"
                >
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id}>{org.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Description</label>
                <textarea
                  rows={2}
                  placeholder="Summary of this project's microservices and purpose..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:border-sky-500"
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
                  className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center space-x-2"
                >
                  {submitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>Create Project</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
