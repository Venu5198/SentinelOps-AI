# SentinelOps AI

> Autonomous AI-powered IT Incident Management Platform.

SentinelOps AI continuously monitors application infrastructure, detects operational failures, gathers diagnostic evidence (metrics, logs, health checks), investigates incidents with structured local AI inference, identifies probable root causes, recommends risk-classified remediation actions, enforces strict human approval gates, executes allowlisted remediation safely, verifies service recovery, and maintains an immutable audit trail.

---

## Key Capabilities

- **Automated Detection & Ingestion:** Native Alertmanager webhook ingestion with fingerprint-based deduplication.
- **Contextual Evidence Gathering:** Correlates Prometheus metrics, Loki log streams, and live HTTP health probes.
- **Evidence-Backed AI Investigation:** Structured local AI inference (Ollama) producing hypotheses citing concrete evidence IDs.
- **Human-in-the-Loop Approval:** Cryptographic action signature verification with 15-minute expiration window before any infrastructure mutation.
- **Restricted Remediation Execution:** Strict allowlisted actions (`container.restart`, `health_check`); zero arbitrary shell execution.
- **Automated Recovery Verification:** Multi-step post-remediation health check polling before transitioning to `RESOLVED`.
- **Immutable Audit Logging:** Tamper-evident logging of all security-relevant and state-altering actions.

---

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, Pydantic v2, Motor (MongoDB async), Redis
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide React
- **Persistence:** MongoDB 7.0 (Collections: users, services, incidents, evidence, investigations, approvals, remediation_executions, audit_logs)
- **Coordination:** Redis 7.0 (Deduplication locks, rate limiting)
- **AI Subsystem:** Ollama local inference (`qwen2.5` / `llama3.2`) with pluggable provider architecture
- **Telemetry:** Prometheus, Alertmanager, Grafana Loki
- **Testing:** Pytest, HTTPX, Playwright E2E

---

## Directory Structure

```
.
├── backend/                  # FastAPI Application Core
│   ├── api/v1/               # Versioned REST & Webhook Routers
│   ├── core/                 # Config, Security, RBAC, Logging
│   ├── db/                   # MongoDB & Redis Client Connections
│   ├── models/               # Pydantic Schemas & BSON Converters
│   ├── services/             # Business Logic Layer
│   ├── ai/                   # AI Prompting, Sanitization & Inference
│   ├── executor/             # Restricted Remediation Executor & Allowlist
│   └── integrations/         # Prometheus, Loki, Docker Adapters
├── frontend/                 # React 18 + Vite Operations Dashboard
│   ├── src/
│   │   ├── components/       # UI Components & Approval Modals
│   │   ├── pages/            # Dashboard, Incidents, Detail, Audit
│   │   └── services/         # API Client Services
├── docker/                   # Docker Compose & Service Configs
│   ├── prometheus/           # Prometheus Alert Rules & Config
│   ├── alertmanager/         # Alertmanager Routing Config
│   ├── loki/                 # Loki Log Aggregator Config
│   └── payment-service/      # Sample Monitored Target Application
├── docs/                     # Architectural & Requirements Documentation
└── tests/                    # Backend Unit, Integration & Playwright E2E Tests
```

---

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.12+
- Node.js 20+ & npm
- Docker Engine & Docker Compose

### 2. Backend Setup
```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Running Tests
```bash
# Backend unit & integration tests
pytest -v

# Playwright E2E tests
pytest tests/e2e/test_full_journey.py -v
```

---

## Documentation Links

- [PRD Analysis](docs/PRD_ANALYSIS.md)
- [Requirements Specification](docs/REQUIREMENTS.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [Technology Stack Decisions (ADRs)](docs/TECH_STACK_DECISIONS.md)
- [Implementation Status Tracker](docs/IMPLEMENTATION_STATUS.md)

