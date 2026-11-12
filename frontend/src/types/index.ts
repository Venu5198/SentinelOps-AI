export type UserRole = 'admin' | 'operator' | 'viewer';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description?: string;
  projects_count: number;
  created_at: string;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string;
  organization_id: string;
  status: 'active' | 'archived' | 'maintenance';
  services_count: number;
  active_incidents_count: number;
  health_status: 'healthy' | 'degraded' | 'unhealthy';
  created_at: string;
}

export interface Environment {
  id: string;
  name: string;
  slug: string;
  description?: string;
  env_type: 'development' | 'staging' | 'production' | 'custom';
  project_id: string;
  services_count: number;
  created_at: string;
}

export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type IncidentStatus = 
  | 'DETECTED'
  | 'ACKNOWLEDGED'
  | 'INVESTIGATING'
  | 'ROOT_CAUSE_IDENTIFIED'
  | 'AWAITING_APPROVAL'
  | 'REMEDIATING'
  | 'VERIFYING'
  | 'RESOLVED'
  | 'FAILED'
  | 'ESCALATED'
  | 'CLOSED';

export interface Incident {
  id: string;
  fingerprint: string;
  service_name: string;
  project_id?: string;
  environment?: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  title: string;
  description: string;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  occurrence_count: number;
  assigned_to?: string;
  detected_at: string;
  updated_at: string;
  resolved_at?: string;
}

export interface Service {
  id: string;
  name: string;
  project_id: string;
  environment: string;
  service_type: string;
  endpoint_url: string;
  health_endpoint: string;
  health_status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  monitoring_enabled: boolean;
  last_check_at?: string;
  last_error?: string;
}

export interface DiscoveredService {
  id: string;
  name: string;
  container_id?: string;
  container_name?: string;
  image?: string;
  source: string;
  detected_endpoints: string[];
  detected_health_path: string;
  status: 'discovered' | 'approved' | 'ignored';
  discovered_at: string;
}

export interface Integration {
  id: string;
  name: string;
  integration_type: 'prometheus' | 'loki' | 'alertmanager' | 'tempo' | 'docker' | 'kubernetes';
  endpoint_url: string;
  project_id?: string;
  status: 'connected' | 'degraded' | 'disconnected' | 'untested';
  last_checked_at?: string;
  last_error?: string;
}

export interface Evidence {
  id: string;
  incident_id: string;
  source: string;
  evidence_type: string;
  name: string;
  payload: any;
  summary?: string;
  observed_at: string;
}

export interface RootCauseHypothesis {
  hypothesis: string;
  likelihood: string;
  explanation: string;
  cited_evidence_ids: string[];
}

export interface ProposedAction {
  action_id: string;
  action_name: string;
  target_service: string;
  parameters: Record<string, any>;
  rationale: string;
  risk_level: string;
  requires_approval: boolean;
}

export interface InvestigationReport {
  incident_summary: string;
  affected_service: string;
  observed_symptoms: string[];
  probable_root_causes: RootCauseHypothesis[];
  confidence_score: number;
  uncertainty_notes?: string;
  recommended_actions: ProposedAction[];
}

export interface Investigation {
  id: string;
  incident_id: string;
  model_name: string;
  report: InvestigationReport;
  status: string;
  created_at: string;
}

export interface Approval {
  id: string;
  incident_id: string;
  action_id?: string;
  action_name: string;
  target_service: string;
  parameters: Record<string, any>;
  rationale?: string;
  risk_level?: string;
  action_signature?: string;
  signature?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  requested_by: string;
  approved_by?: string;
  rejected_by?: string;
  expires_at: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  actor_id: string;
  actor_role: UserRole;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, any>;
  result?: string;
  correlation_id?: string;
  request_ip?: string;
  status?: 'SUCCESS' | 'FAILURE';
  timestamp: string;
}
