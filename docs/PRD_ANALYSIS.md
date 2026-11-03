# SentinelOps AI — PRD Analysis & Traceability

**Document Version:** 1.0  
**PRD Reference:** Notion PRD v1.0 (`40d48773-4755-8188-9692-c5c3c0658511`)  
**Status:** Complete Analysis  

---

## 1. Executive Summary & Product Objective

SentinelOps AI is a self-hosted, local-first, AI-assisted IT Incident Management Platform. It continuously monitors application infrastructure, detects operational failures via automated alert ingestion, gathers contextual diagnostic evidence (metrics, logs, health checks), investigates incidents with structured local AI inference, identifies probable root causes, recommends risk-classified remediation actions, enforces strict human approval gates, executes allowlisted remediation safely, verifies service recovery, and maintains an immutable audit trail.

### Core Product Principle
> **AI may investigate and recommend. Deterministic policy controls, authorization, and human approval govern infrastructure changes. The AI must never receive unrestricted shell or infrastructure access.**

---

## 2. Problem Statement & Operational Impact

Modern distributed application stacks suffer from severe operational friction during outages:
1. **Context Fragmentation:** Logs, metrics, and alerts reside in disparate silos (Prometheus, Loki, Alertmanager, container runtimes). Engineers waste critical triage minutes assembling context.
2. **Investigation Latency:** Manual correlation between telemetry spikes (HTTP 500s, latency, container restarts) and underlying causes is slow and cognitive-heavy.
3. **Remediation Risk:** Uncontrolled manual interventions risk unintended blast radius; lack of verification leads to false recovery assumptions.
4. **Accountability Gaps:** Missing audit records prevent post-incident learning, compliance tracing, and operational reviews.

SentinelOps AI addresses these through a unified pipeline: **Detect $\rightarrow$ Ingest & Deduplicate $\rightarrow$ Gather Evidence $\rightarrow$ AI Investigate $\rightarrow$ Human Approve $\rightarrow$ Restricted Execute $\rightarrow$ Verify Recovery $\rightarrow$ Audit & Report**.

---

## 3. User Personas & Permissions Matrix

| Persona | Role Key | Core Needs & PRD Permissions |
|---|---|---|
| **DevOps Engineer** | `operator` | Monitors service health, triggers manual investigations, executes approved allowlisted container restarts, inspects post-action recovery verification. |
| **Site Reliability Engineer (SRE)** | `operator` | Analyzes incident root-cause hypotheses, validates evidence correlation, reviews confidence metrics, verifies SLO/error budgets. |
| **Backend Engineer** | `operator` / `viewer` | Explores application logs, latency spikes, and dependency connection failures. |
| **Infrastructure Administrator** | `admin` | Manages users, configures RBAC policies, manages allowlisted actions, audits privileged operations, approves high-risk remediation. |
| **Engineering Manager** | `viewer` | Reviews incident frequency, mean-time-to-recovery (MTTR), service reliability reports, and audit logs. |

---

## 4. Goals and Non-Goals Analysis

### 4.1 Product Goals
- **G-01 (Automated Detection):** Ingest Alertmanager alerts; detect predefined deterministic failures.
- **G-02 (Centralized Incident Management):** Full incident lifecycle tracking across standard operational states.
- **G-03 (Consistent Evidence Collection):** Normalized telemetry gathering from Prometheus, Loki, and health endpoints.
- **G-04 (Evidence-Backed AI Investigation):** Schema-validated diagnostic reports citing concrete evidence references.
- **G-05 (Controlled Remediation):** Strictly allowlisted, human-approved, parameter-validated actions.
- **G-06 (Post-Action Recovery Verification):** Automated health polling post-execution to confirm actual resolution.
- **G-07 (Auditability & Traceability):** Tamper-evident audit logs for all sensitive actions and approvals.
- **G-08 (Reproducible AI Evaluation):** Evaluation framework with labeled synthetic incident datasets.

### 4.2 Non-Goals for Initial Scope (Explicit Guardrails)
- **NO** autonomous production infrastructure mutations without explicit human approval.
- **NO** arbitrary shell command execution (`sh -c`, `bash`, raw SSH, or unvalidated parameters).
- **NO** automatic source-code editing or automated database schema migrations.
- **NO** multi-cloud provider or external SaaS billing/multi-tenancy complexity.
- **NO** predictive or probabilistic incident forecasting.
- **NO** multi-agent conversational choreography beyond the required LangGraph/chain investigation workflow.

---

## 5. Traceability Matrix: PRD Requirements to Implementation Modules

| PRD Req ID | PRD Title & Priority | Functional Description | Architecture / Implementation Module | Acceptance Criteria |
|---|---|---|---|---|
| **FR-01** | Infrastructure Monitoring (P0) | Real-time health, CPU/mem, error rates, latency from Prometheus & health endpoints. | `backend/services/monitoring_service.py`<br>`frontend/src/pages/MonitoringPage.tsx` | AC-01, AC-06 |
| **FR-02** | Incident Detection & Ingestion (P0) | Alertmanager webhook receiver, validation, fingerprinting, deduplication. | `backend/api/v1/alerts.py`<br>`backend/services/deduplication_service.py` | AC-01, AC-02, AC-03 |
| **FR-03** | Incident Management (P0) | State machine transitions, listing, filtering, detail views, assignments. | `backend/api/v1/incidents.py`<br>`backend/models/incident.py`<br>`frontend/src/pages/IncidentDetailPage.tsx` | AC-04, AC-18 |
| **FR-04** | Diagnostic Evidence Collection (P0) | Fetch metrics (Prometheus), logs (Loki), container states, health checks. | `backend/services/evidence_collector.py`<br>`backend/integrations/` | AC-05, AC-06 |
| **FR-05** | AI Investigation Engine (P0) | Structured diagnosis, hypotheses, evidence references, uncertainty quantification. | `backend/ai/investigation_engine.py`<br>`backend/ai/schemas.py`<br>`backend/ai/llm_client.py` | AC-07, AC-08 |
| **FR-06** | Remediation Recommendations (P0) | Risk classification, action templates, rationale binding. | `backend/services/remediation_service.py`<br>`backend/models/remediation.py` | AC-07, AC-12 |
| **FR-07** | Human Approval Workflows (P0) | Exact-action binding, expiration timeout, RBAC validation. | `backend/api/v1/approvals.py`<br>`backend/services/approval_service.py`<br>`frontend/src/components/ApprovalModal.tsx` | AC-09, AC-10, AC-11 |
| **FR-08** | Restricted Remediation Execution (P0) | Strict allowlist, Docker socket restart adapter, idempotency, timeout. | `backend/executor/restricted_executor.py`<br>`backend/executor/allowlist.py` | AC-11, AC-12, AC-13 |
| **FR-09** | Recovery Verification (P0) | Polling service health checks post-action, state progression. | `backend/services/verification_service.py` | AC-14, AC-15 |
| **FR-10** | Authentication & RBAC (P0) | JWT bearer auth, password hashing, Admin/Operator/Viewer roles. | `backend/api/v1/auth.py`<br>`backend/core/security.py`<br>`backend/core/rbac.py` | AC-04, AC-09, AC-17 |
| **FR-11** | Audit Logging (P0) | Tamper-evident audit log collection for all state changes & executions. | `backend/services/audit_service.py`<br>`backend/models/audit_log.py`<br>`frontend/src/pages/AuditLogPage.tsx` | AC-16 |
| **FR-12** | Incident Reporting (P1) | Post-incident report generation (JSON/Markdown) with full timeline. | `backend/api/v1/reports.py`<br>`backend/services/report_generator.py` | AC-18 |

---

## 6. Security Boundaries & Authorization Protocol

```
+---------------------------------------------------------------------------------+
|                                UNTRUSTED REALM                                  |
|   External Alerts (Alertmanager)  /  Application Logs (Loki)  /  Metrics        |
|                                                                                 |
|   * Treated as hostile data: sanitized, prompt-injection shielded               |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                             SENTINELOPS AI BACKEND                              |
|                                                                                 |
|  [Authentication & RBAC Filter] -> Validates JWT & User Role                   |
|  [Evidence Sanitizer]           -> Strips control tokens, limits token window   |
|  [AI Investigation Engine]      -> Produces Hypothesis & Recommendations ONLY   |
|                                                                                 |
|                   +---------------------------------------+                     |
|                   | CRITICAL SECURITY CHECKPOINT:         |                     |
|                   | Human Approval Gate (Operator/Admin)  |                     |
|                   | - Binds to exact SHA-256 action hash  |                     |
|                   | - 15-minute expiration time           |                     |
|                   +---------------------------------------+                     |
+---------------------------------------------------------------------------------+
                                       |
                                       v (Valid Token + Signed Approval)
+---------------------------------------------------------------------------------+
|                           RESTRICTED EXECUTOR SERVICE                           |
|                                                                                 |
|  - Validates allowlisted action ID against hardcoded catalog                    |
|  - Verifies parameter types (e.g., target_service in registered_services)       |
|  - Enforces single concurrent execution lock via Redis                          |
|  - Never invokes shell / sub-process shell strings                              |
|  - Directly calls Docker Engine SDK for container restart / HTTP health check   |
|  - Commits immutable Audit Log before & after execution                         |
+---------------------------------------------------------------------------------+
```

---

## 7. Assumptions & Open Decisions Resolution

Based on PRD Section 11:
1. **Permitted Remediation Operations (P0):**
   - `service.health_check`: Probe HTTP health endpoint.
   - `container.restart`: Restart registered Docker application container (e.g. `payment-service`).
   - `cache.flush_key`: Evict corrupted cache keys for specific service.
2. **Approval Policy:** 100% of infrastructure-altering operations (`container.restart`, `cache.flush_key`) require explicit Operator or Admin approval. Read-only health verification does not require separate approval.
3. **Data Retention:** In-memory / MongoDB local retention set to 30 days for incidents, 90 days for audit logs.
4. **Local AI Model:** Primary target: `qwen2.5:latest` or `llama3.2:3b` via Ollama; graceful fallback to deterministic mock / OpenAI-compatible provider if Ollama is not running.
5. **Kubernetes Scope:** Deferred to post-MVP milestone M9 per PRD Section 9.3 and Section 14.

---

## 8. Definition of Done Checklist

- [ ] All 12 Functional Requirements (FR-01 to FR-12) implemented and unit/integration tested.
- [ ] 18 Acceptance Criteria (AC-01 to AC-18) validated with automated Pytest and Playwright tests.
- [ ] Deterministic failure scenario (Payment API HTTP 500) successfully detected, investigated by AI, approved by human, remediated, and verified.
- [ ] Zero arbitrary shell execution surfaces in backend codebase.

