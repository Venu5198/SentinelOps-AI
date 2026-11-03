# SentinelOps AI — Technology Stack Decisions & ADRs

**Document Version:** 1.0  
**PRD Reference:** Notion PRD v1.0 Section 1, 5, 9, 13  
**Status:** Approved Architectural Decision Records  

---

## Architecture Decision Records (ADRs)

### ADR-001: Backend Runtime & Web Framework
* **Decision:** Python 3.12+ with **FastAPI** and **Pydantic v2**.
* **Context & PRD Alignment:** PRD Section 1, 5, 9 mandates rapid async processing, robust schema validation, clean REST APIs, and native AI/LLM library integration.
* **Alternatives Evaluated:** Node.js/Express, Go (Gin), Python (Django/Flask).
* **Rationale:**
  - FastAPI provides native async event loops, auto-generated OpenAPI 3.1 specifications, and first-class typing through Pydantic v2.
  - Python is the primary ecosystem for AI integration (Ollama SDK, LangChain/LangGraph, data manipulation).
  - Eliminates polyglot runtime overhead for backend and AI components.
* **Consequences:** CPU-bound processing must be offloaded to worker threads or background tasks to keep the async event loop responsive.

---

### ADR-002: Frontend Framework & Build System
* **Decision:** **React 18** with **TypeScript**, **Vite**, and **Tailwind CSS**.
* **Context & PRD Alignment:** PRD Section 9.1 specifies a responsive, component-based operations dashboard with low latency and clean operational ergonomics.
* **Alternatives Evaluated:** Next.js (App Router), Vue 3, Svelte.
* **Rationale:**
  - SentinelOps AI is a single-tenant/self-hosted operational dashboard behind authentication; Server-Side Rendering (SSR) adds unnecessary container complexity and build friction without SEO benefits.
  - Vite provides instantaneous hot-module replacement (HMR), tiny production bundles, and static file serving from an Nginx container.
  - Tailwind CSS enables rapid, consistent styling with dark-mode support tailored for operations centers.
* **Consequences:** Initial page load requires browser JavaScript execution; handled cleanly by lightweight client bundle.

---

### ADR-003: Primary Database Engine
* **Decision:** **MongoDB 7.0** (Community Edition) via `motor` async driver.
* **Context & PRD Alignment:** PRD Section 16 defines semi-structured, evolving documents: polymorphic diagnostic evidence (metrics, logs, stack traces), investigation reports with nested citations, and variable alert payloads.
* **Alternatives Evaluated:** PostgreSQL (with JSONB), SQLite.
* **Rationale:**
  - Diagnostic evidence payloads vary drastically between sources (Prometheus scalar vs. Loki multi-line log streams vs. Docker state JSON). MongoDB's document model avoids complex relational normalization or rigid migrations during rapid incident triage iterations.
  - Native TTL indexes support automated retention policies for historical evidence and alert buffers.
  - High write throughput for event ingestion and append-only audit logging.
* **Consequences:** Relational integrity (e.g. cascading deletes) must be managed cleanly in the service layer; strict Pydantic schemas enforce application-level type consistency.

---

### ADR-004: Coordination, Locking & Caching
* **Decision:** **Redis 7.0** (Standalone) via `redis.asyncio`.
* **Context & PRD Alignment:** PRD Section 5 (FR-02, FR-08) requires distributed locks for alert deduplication and mutual exclusion on remediation execution.
* **Alternatives Evaluated:** Celery with RabbitMQ, in-memory Python locks.
* **Rationale:**
  - In-memory Python locks fail when multiple backend worker processes are spawned.
  - Redis provides sub-millisecond atomic key-value operations (`SET NX PX`) for distributed deduplication and mutex locking.
  - Zero heavy message-broker overhead for the initial local-first MVP.
* **Consequences:** Requires Redis container in Docker Compose; failure mode defaults to degraded in-memory locks if Redis is temporarily unreachable.

---

### ADR-005: AI Inference Subsystem
* **Decision:** **Ollama** local inference runtime with pluggable LLM provider abstraction (`BaseLLMClient`).
* **Context & PRD Alignment:** PRD Section 1.1, 9.3 requires self-hosted, local-first operation without mandatory paid cloud API keys, while keeping the architecture open to configurable providers (OpenAI, Anthropic).
* **Target Local Models:** `qwen2.5:latest` (or `llama3.2:3b` / `mistral:7b`) running on host or Docker.
* **Rationale:**
  - Protects sensitive infrastructure logs from exfiltration to third-party cloud APIs.
  - Zero operational cost per token; fully reproducible offline evaluation.
  - Pluggable interface allows immediate switching to an OpenAI-compatible cloud endpoint when internet and credentials are provided.
* **Consequences:** Local inference latency is hardware-dependent (CPU vs. GPU); backend enforces strict 45s timeouts and graceful fallback to manual triage.

---

### ADR-006: Observability & Telemetry Integration
* **Decision:** **Prometheus** (Metrics), **Alertmanager** (Alerting), and **Grafana Loki** (Log Aggregation).
* **Context & PRD Alignment:** PRD Section 1, 5 (FR-01, FR-04), 9.1 mandates standardized monitoring and log correlation.
* **Alternatives Evaluated:** Elasticsearch / OpenSearch, OpenTelemetry Collector.
* **Rationale:**
  - Standard industry telemetry stack with lightweight resource footprint in local Docker Compose.
  - PromQL and LogQL provide expressive query semantics for time-bounded evidence extraction ($T_{\text{detect}} \pm 15\text{ mins}$).
  - Alertmanager webhook protocol provides a mature, standard notification pipeline.
* **Consequences:** Requires pre-configured Docker Compose service definitions and sample instrumentation.

---

### ADR-007: Remediation Execution Architecture
* **Decision:** **Hardcoded Action Catalog** + **Docker Python SDK** (`docker.from_env()`).
* **Context & PRD Alignment:** PRD Section 1.1, 5 (FR-08) strictly forbids arbitrary shell execution, subshell spawning, or unsupervised AI command execution.
* **Alternatives Evaluated:** Ansible runner, SSH commands, raw `subprocess.Popen(shell=True)`.
* **Rationale:**
  - Directly using the Docker Engine API socket eliminates shell injection vulnerabilities (`&&`, `;`, `|`, `` ` ``).
  - Remediation actions are typed classes with strict parameters (e.g. `service_name: Literal["payment-service", "order-service"]`).
  - Guarantees complete auditability and exact parameter verification before execution.
* **Consequences:** Execution service must have read/write access to Docker socket (`/var/run/docker.sock`).

---

### ADR-008: Authentication & Authorization Strategy
* **Decision:** **Stateless JWT (HMAC-SHA256)** with **Bcrypt** password hashing and **FastAPI Security Dependencies**.
* **Context & PRD Alignment:** PRD Section 5 (FR-10) requires JWT authentication and role-based access control (Admin, Operator, Viewer).
* **Alternatives Evaluated:** Stateful session cookies, OAuth2 / OIDC server.
* **Rationale:**
  - Simple, standard, stateless, and horizontally scalable across API instances.
  - Clear RBAC policy enforcement using FastAPI dependency injection (`require_role(["admin", "operator"])`).
  - No external Identity Provider (IdP) required for local-first deployment.
* **Consequences:** Token revocation before expiration requires Redis token blacklist.

---

### ADR-009: End-to-End & Automated Testing Strategy
* **Decision:** **Pytest** + **HTTPX** for backend unit/integration tests; **Playwright** for frontend and end-to-end browser workflows.
* **Context & PRD Alignment:** PRD Section 9, 14 (Epic 9) requires automated verification of user journeys, API contracts, and security boundaries.
* **Rationale:**
  - HTTPX AsyncClient enables fast, in-process async testing of FastAPI endpoints without port binding.
  - Playwright provides cross-browser automation, headless execution, screenshot capture, and resilient element locators for modern React SPAs.
* **Consequences:** Playwright browser binaries must be cached or pre-installed in development environments.

---

### ADR-010: Deployment Orchestration
* **Decision:** **Docker Compose** for initial release (MVP); Kubernetes manifests prepared in `k8s/` for post-MVP transition.
* **Context & PRD Alignment:** PRD Section 1, 9.3 mandates local-first Docker Compose as the primary runtime for the initial release, with Kubernetes deferred.
* **Rationale:**
  - Single-command developer experience: `docker compose up -d`.
  - Predictable resource limits, isolated bridge networking, and local volume persistence.
* **Consequences:** Cross-container networking must use internal Docker service DNS names (`mongodb:27017`, `prometheus:9090`).

