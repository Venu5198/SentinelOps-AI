import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDashboardPage } from './pages/ProjectDashboardPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';
import { ServicesPage } from './pages/ServicesPage';
import { DiscoveryPage } from './pages/DiscoveryPage';
import { IntegrationsPage } from './pages/IntegrationsPage';
import { TelemetryExplorerPage } from './pages/TelemetryExplorerPage';
import { AuditLogPage } from './pages/AuditLogPage';
import { LoginPage } from './pages/LoginPage';

const ProtectedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = localStorage.getItem('sentinelops_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return (
    <div className="min-h-screen flex flex-col bg-slate-900 text-slate-100">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-8 overflow-y-auto max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedLayout><DashboardPage /></ProtectedLayout>} />
        <Route path="/projects" element={<ProtectedLayout><ProjectsPage /></ProtectedLayout>} />
        <Route path="/projects/:projectId" element={<ProtectedLayout><ProjectDashboardPage /></ProtectedLayout>} />
        <Route path="/incidents" element={<ProtectedLayout><IncidentsPage /></ProtectedLayout>} />
        <Route path="/incidents/:id" element={<ProtectedLayout><IncidentDetailPage /></ProtectedLayout>} />
        <Route path="/services" element={<ProtectedLayout><ServicesPage /></ProtectedLayout>} />
        <Route path="/discovery" element={<ProtectedLayout><DiscoveryPage /></ProtectedLayout>} />
        <Route path="/integrations" element={<ProtectedLayout><IntegrationsPage /></ProtectedLayout>} />
        <Route path="/telemetry" element={<ProtectedLayout><TelemetryExplorerPage /></ProtectedLayout>} />
        <Route path="/approvals" element={<ProtectedLayout><IncidentsPage /></ProtectedLayout>} />
        <Route path="/audit" element={<ProtectedLayout><AuditLogPage /></ProtectedLayout>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
