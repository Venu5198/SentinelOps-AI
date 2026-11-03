# SentinelOps AI — Detailed Requirements Specification

**Document Version:** 1.0  
**PRD Reference:** Notion PRD v1.0 Section 5, 6, 7, 8, 9, 12  
**Status:** Approved  

---

## 1. Functional Requirements (FR)

### FR-01: Infrastructure Monitoring — Priority: P0
* **Description:** Continuous ingestion and visualization of health status, performance metrics, and container availability for registered services.
* **Capabilities:**
  - CPU and Memory utilization polling.
  - Periodic HTTP health probe execution (status, response time).
  - API error rate and request latency tracking via Prometheus metrics.
  - Container status and restart counters from Docker daemon.
* **Failure Mode:** When monitoring telemetry is lost, the service status MUST transition to `UNKNOWN` or `DEGRADED`. Under no circumstance shall a silent failure be marked as `HEALTHY`.

### FR-02: Incident Detection and Ingestion — Priority: P0
* **Description:** Secure webhook endpoint receiving Prometheus Alertmanager payloads, performing payload validation, severity classification, and fingerprint-based deduplication.
* **Payload Specification:** Complies with Alertmanager Webhook v4 specification.
* **Deduplication Rule:** Alerts sharing an active `fingerprint` (composed of `alertname + service + severity`) must update the existing incident timeline and increment occurrence count rather than creating duplicate active incidents.
* **Error Handling:** Malformed or missing mandatory fields (`status`, `labels.alertname`, `labels.service`) return HTTP 422 Unprocessable Entity and log a rejection audit event.

### FR-03: Incident Management & Lifecycle — Priority: P0
* **Description:** State machine governing incident lifecycle with strict role-based state transition enforcement.
* **Allowed States:**
  1. `DETECTED` (Initial state upon alert ingestion)
  2. `ACKNOWLEDGED` (Assigned operator acknowledges triage)
  3. `INVESTIGATING` (Evidence collection & AI diagnostic run underway)
  4. `ROOT_CAUSE_IDENTIFIED` (Diagnostic report generated with hypotheses)
  5. `AWAITING_APPROVAL` (Remediation proposed; awaiting human decision)
  6. `REMEDIATING` (Approved action actively executing via restricted executor)
  7. `VERIFYING` (Post-remediation automated health checks running)
  8. `RESOLVED` (Recovery verified successfully)
  9. `FAILED` (Remediation or verification failed)
  10. `ESCALATED` (Operator manually escalates unresolved incident)
  11. `CLOSED` (Terminal state)
* **Enforcement:** Transitions violating the lifecycle DAG (e.g. `DETECTED` directly to `RESOLVED` without verification) are rejected with HTTP 400 Bad Request.

### FR-04: Diagnostic Evidence Collection — Priority: P0
* **Description:** Automated aggregation of multi-source diagnostic artifacts associated with the incident time window ($T_{\text{detect}} \pm 15 \text{ mins}$).
* **Evidence Sources:**
  - **Metrics:** Prometheus instantaneous and range queries (HTTP 5xx rate, P95 latency, memory).
  - **Logs:** Loki LogQL queries filtering on `{service="<name>"}` with severity `error` or `fatal`.
  - **Health Probes:** Recent response bodies, status codes, and network latency.
  - **Container State:** Exit codes, restart counts, and OOM-kill flags.
* **Format:** Normalized JSON evidence schema containing `evidence_id`, `source`, `service`, `observed_at`, `evidence_type`, and `payload`.

### FR-05: AI Investigation Engine — Priority: P0
* **Description:** Local inference engine (Ollama) processing normalized evidence via structured prompts to generate evidence-grounded incident reports.
* **Output Schema (Strict Pydantic):**
  - `incident_summary`: High-level explanation of the breakdown.
  - `affected_service`: Identified service name.
  - `observed_symptoms`: Factual list directly extracted from evidence.
  - `probable_root_causes`: Ranked hypotheses with explicit evidence IDs cited.
  - `confidence_score`: Floating point between 0.00 and 1.00 (calibrated).
  - `uncertainty_notes`: Explicit identification of missing or contradictory evidence.
  - `recommended_actions`: Action recommendations conforming to allowlisted operations.
* **Guardrail:** AI-generated claims without corresponding evidence references are flagged as unsupported. If the local LLM fails or times out (30s threshold), the incident remains editable for manual triage.

### FR-06: Remediation Recommendations — Priority: P0
* **Description:** Mapping of root-cause hypotheses to structured remediation action proposals with risk scoring.
* **Risk Classifications:**
  - `LOW`: Read-only health probe, cache key eviction.
  - `MEDIUM`: Single stateless container restart (e.g., `payment-service`).
  - `HIGH`: Service reconfiguration or stateful service manipulation.
* **Payload:** Proposals must specify `action_id`, `action_name`, `target_service`, `parameters`, `rationale`, and `estimated_impact`.

### FR-07: Human Approval Workflow — Priority: P0
* **Description:** Mandatory interactive gate requiring authenticated operator or admin sign-off before any mutating operation executes.
* **Controls:**
  - Signature includes exact hash of `action_id + parameters + target_service`.
  - Time-to-Live (TTL): Approvals expire after 15 minutes if not executed.
  - Rejection: Operator can reject with mandatory reason field; state transitions to `FAILED` or `ESCALATED`.

### FR-08: Restricted Remediation Execution — Priority: P0
* **Description:** Sandboxed executor component isolated from general application logic.
* **Security Controls:**
  - **Hardcoded Allowlist:** Only registered action identifiers (`service.restart_container`, `service.verify_health`, `cache.clear_service_key`) can execute.
  - **Strict Parameter Validation:** Service name must exist in registered database services; no shell parameters or flags permitted.
  - **No Subshell:** Direct API / Docker SDK invocation; no `subprocess.run(shell=True)`.
  - **Idempotency:** Distributed Redis lock on `incident_id` prevents duplicate concurrent execution attempts.

### FR-09: Recovery Verification — Priority: P0
* **Description:** Post-execution verification engine that executes configured health checks against the remediated service over a 60-second window.
* **Evaluation Criteria:**
  - At least 3 consecutive successful HTTP 200 health probes.
  - Prometheus error rate returns below the alert threshold ($\le 0.01$).
* **Outcomes:** If checks pass $\rightarrow$ transition to `RESOLVED`. If checks fail or time out $\rightarrow$ transition to `FAILED` with escalation option enabled.

### FR-10: Authentication and Role-Based Access Control (RBAC) — Priority: P0
* **Description:** Stateless JWT bearer token authentication with Bcrypt password hashing.
* **Role Hierarchy:**
  - `admin`: Full platform control (user management, policy edits, approvals, executions).
  - `operator`: Incident triage, manual investigation triggers, approval/rejection of remediation.
  - `viewer`: Read-only access to incidents, metrics, dashboards, and audit logs.

### FR-11: Audit Logging — Priority: P0
* **Description:** Append-only, tamper-evident audit journal capturing all security-relevant and operational actions.
* **Logged Events:** User login, role modification, alert ingestion, incident status change, AI investigation initiation, remediation proposal, approval/rejection, execution start/finish, verification outcome.
* **Fields:** `actor_id`, `actor_role`, `action`, `resource_type`, `resource_id`, `status`, `request_ip`, `correlation_id`, `timestamp`.

### FR-12: Incident Reporting — Priority: P1
* **Description:** Automated post-incident report generator producing structured JSON and Markdown summaries containing full chronological timeline, evidence artifacts, diagnostic reports, approval records, and recovery metrics.

---

## 2. Non-Functional Requirements (NFR)

| ID | Category | Requirement Specification | Verification Method |
|---|---|---|---|
| **NFR-01** | Standard API Latency | P95 latency $< 500\text{ ms}$ for standard read/write REST endpoints. | Pytest benchmark & Locust load testing (20 concurrent requests). |
| **NFR-02** | Alert Ingestion Throughput | Alert ingestion P95 latency $< 2000\text{ ms}$, capable of handling alert bursts without dropping payloads. | Asynchronous FastAPI background task with Redis deduplication buffer. |
| **NFR-03** | Dashboard Load Performance | Initial dashboard load and telemetry rendering within $3\text{ seconds}$ on standard desktop browser. | Playwright performance timing metrics. |
| **NFR-04** | AI Inference Latency & Timeout | Local LLM inference timeout capped at $45\text{ seconds}$; non-blocking asynchronous execution. | Timeout wrapper with graceful fallback to manual triage state. |
| **NFR-05** | High Availability / Fault Tolerance | If Prometheus, Loki, or Ollama are unreachable, core incident triage remains fully operational. | Degraded source indicators in UI; unit tests for partial integration failures. |
| **NFR-06** | Zero Shell Injection Surface | Absolute prohibition of shell execution; all executor integrations must use typed SDKs or HTTP clients. | Static security analysis (Bandit/Semgrep) & security test suite. |
| **NFR-07** | Prompt Injection Defense | All ingested log messages and alert labels treated as untrusted data; wrapped in delimited tags with prompt insulation. | Adversarial prompt injection test suite verifying LLM remains constrained. |

---

## 3. User Stories (US)

- **US-01 (Monitoring):** *As a DevOps Engineer*, I want to view real-time monitored service health on an intuitive dashboard, so that I can immediately identify unhealthy infrastructure components.
- **US-02 (Detection):** *As an SRE*, I want Alertmanager alerts to be automatically ingested and deduplicated into actionable incidents, so that critical failures are never missed or drowned in alert storms.
- **US-03 (AI Investigation):** *As a Backend Engineer*, I want an AI engine to correlate logs, metrics, and errors into probable root-cause hypotheses, so that my investigation time is reduced from hours to minutes.
- **US-04 (Evidence Inspection):** *As an SRE*, I want to click and inspect the exact log lines and metric data points that the AI cited as proof, so that I can independently verify diagnostic accuracy.
- **US-05 (Human Approval):** *As an Infrastructure Administrator*, I want an approval gate where I review the exact command and target container before execution, so that unintended infrastructure mutations are blocked.
- **US-06 (Automated Verification):** *As a DevOps Engineer*, I want SentinelOps AI to automatically test service recovery after remediation, so that I know whether the fix actually restored healthy operations.
- **US-07 (Audit Compliance):** *As an Administrator*, I want an immutable record of every user action, approval, and execution, so that our organization maintains full operational compliance.
- **US-08 (Reporting):** *As an Engineering Manager*, I want exportable incident timelines and post-mortem summaries, so that recurring operational vulnerabilities can be systematically eliminated.

---

## 4. Acceptance Criteria (AC-01 through AC-18)

* **AC-01 (Alert Ingestion):** GIVEN a valid Alertmanager webhook payload for a registered service, WHEN received by `/api/v1/alerts/webhook`, THEN an incident is created with status `DETECTED`, appropriate severity, and timestamp.
* **AC-02 (Malformed Alert Rejection):** GIVEN an alert payload missing `status` or `labels.alertname`, WHEN ingested, THEN the request is rejected with HTTP 422 and no incident is created.
* **AC-03 (Fingerprint Deduplication):** GIVEN an active incident with fingerprint $F$, WHEN a subsequent alert with fingerprint $F$ is received, THEN the existing incident occurrence count is incremented and no duplicate incident is created.
* **AC-04 (RBAC Filtering):** GIVEN an authenticated user with `viewer` role, WHEN requesting `/api/v1/incidents`, THEN only authorized records are returned, and mutating actions (acknowledge, approve) are rejected with HTTP 403.
* **AC-05 (Evidence Aggregation):** GIVEN an incident on service $S$, WHEN investigation begins, THEN telemetry from Prometheus and Loki for service $S$ within the incident window is attached as normalized evidence.
* **AC-06 (Degraded Evidence Graceful Handling):** GIVEN Prometheus is down, WHEN evidence is gathered, THEN Loki logs and health checks are still collected, and Prometheus is explicitly recorded as `UNAVAILABLE`.
* **AC-07 (Structured AI Report):** GIVEN normalized evidence, WHEN the AI engine runs, THEN it outputs a strictly schema-compliant diagnosis with cited evidence IDs, hypotheses, and recommended remediation.
* **AC-08 (AI Failure Fallback):** GIVEN Ollama is offline or times out, WHEN investigation is requested, THEN the system flags `AI_UNAVAILABLE` in the incident record and keeps the incident accessible for manual triage.
* **AC-09 (Approval Role Enforcement):** GIVEN a user with `viewer` role, WHEN attempting to approve an action, THEN the backend returns HTTP 403 Forbidden and records an authorization failure in audit logs.
* **AC-10 (Remediation Rejection):** GIVEN a proposed remediation, WHEN an operator rejects it with reason $R$, THEN the execution is permanently blocked and the incident state reflects rejection.
* **AC-11 (Action Parameter Binding):** GIVEN an approved action, WHEN submitted to the restricted executor, THEN execution proceeds ONLY IF the action ID, target service, and parameters exactly match the approval signature.
* **AC-12 (Allowlist Enforcement):** GIVEN an action not in the hardcoded allowlist (e.g. `rm -rf /` or arbitrary bash), WHEN submitted, THEN the executor rejects the request immediately without invoking any subshell.
* **AC-13 (Execution Timeout / Failure Handling):** GIVEN a container restart command that exceeds 30s timeout, WHEN executing, THEN the execution records status `FAILED`, and the incident remains unresolved with escalation enabled.
* **AC-14 (Recovery Verification Success):** GIVEN successful remediation execution, WHEN post-action health probes return HTTP 200 for 3 consecutive checks, THEN the incident automatically transitions to `RESOLVED`.
* **AC-15 (Recovery Verification Failure):** GIVEN a remediated service whose health probe continues returning HTTP 500, WHEN verification completes, THEN the incident transitions to `FAILED` and prompts for manual escalation.
* **AC-16 (Audit Log Completeness):** GIVEN any sensitive action (login, state transition, approval, execution), WHEN processed, THEN an immutable audit record is stored with `actor_id`, `action`, `resource_id`, `timestamp`, `result`, and `correlation_id`.
* **AC-17 (Unauthenticated Request Protection):** GIVEN a request without a valid JWT token to any `/api/v1/` endpoint (except `/auth/login` and `/health`), THEN the request is rejected with HTTP 401 Unauthorized.
* **AC-18 (Complete Incident Detail Auditability):** GIVEN a resolved incident, WHEN opened by an authorized user, THEN the complete chronological sequence of alerts, evidence, AI diagnosis, approvals, execution logs, and verification checks is displayed.

---

## 5. AI Evaluation Methodology & Benchmark Scenarios

To ensure deterministic verification of AI diagnostic reliability, a fixed evaluation suite of 8 labeled failure scenarios is established:

| Scenario ID | Failure Description | Injected Symptoms | Expected Root Cause Hypothesis | Expected Action |
|---|---|---|---|---|
| **SC-01** | Payment API 500 Outage | HTTP 500 error spike, NullPointer in payment controller logs. | Application uncaught exception in payment service. | `container.restart(payment-service)` |
| **SC-02** | MongoDB Connection Pool Exhaustion | Error: "ServerSelectionTimeoutError", connection count maxed out. | Database connection starvation. | `service.health_check(mongodb)` + restart service. |
| **SC-03** | Memory Leak / OOM Kill | Memory usage slope $+15\%\text{/min}$, Docker exit code 137. | Out-Of-Memory termination. | `container.restart` + alert scaling. |
| **SC-04** | Redis Cache Connection Refused | Error: "ConnectionError: Error 111 connecting to redis:6379". | Redis cache daemon unavailable. | `service.health_check(redis)`. |
| **SC-05** | API Latency Degradation | P99 latency $> 4500\text{ ms}$, CPU saturation at $99\%$. | Thread contention or CPU starvation. | `container.restart(payment-service)`. |
| **SC-06** | Upstream Dependency Timeout | HTTP 504 Gateway Timeout in order service calling payment service. | Downstream service failure. | Identify downstream dependency as root cause. |
| **SC-07** | Corrupted Cache Key | Cache deserialize JSONDecodeError on user session key. | Incompatible cached data format. | `cache.flush_key(target_key)`. |
| **SC-08** | Container CrashLoopBackOff | Rapid restart count $> 5$, exit code 1 immediately on boot. | Misconfiguration or missing environment variable. | Recommend configuration rollback; do not blindly restart. |

**Scoring Rubric:**
- **Accurate:** Primary hypothesis matches ground truth AND all cited evidence IDs exist.
- **Partially Accurate:** Identifies the affected component but misses exact mechanism.
- **Hallucination / Failure:** Recommends non-allowlisted commands, invents unobserved metrics, or displays confidence $> 0.8$ with zero evidence references. Target accuracy threshold: $\ge 80\%$.

