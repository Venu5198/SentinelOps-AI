export type UserRole = 'admin' | 'operator' | 'viewer';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
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
  environment: string;
  endpoint_url: string;
  health_endpoint: string;
  health_status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  monitoring_enabled: boolean;
  last_check_at?: string;
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
  action_id: string;
  action_signature: string;
  target_service: string;
  parameters: Record<string, any>;
  rationale: string;
  risk_level: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  requested_by: string;
  approved_by?: string;
  decision_reason?: string;
  expires_at: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  actor_id: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  result: string;
  details?: Record<string, any>;
  correlation_id?: string;
  timestamp: string;
}

