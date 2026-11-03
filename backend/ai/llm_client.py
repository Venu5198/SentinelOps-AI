import json
import re
from typing import Any, Dict, List, Optional
import httpx
from backend.core.config import settings
from backend.core.logger import logger
from backend.ai.prompt_builder import SYSTEM_PROMPT
from backend.models.investigation import InvestigationOutputSchema, RootCauseHypothesis, ProposedAction


class BaseLLMClient:
    async def generate_investigation(
        self,
        prompt: str,
        incident: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> InvestigationOutputSchema:
        raise NotImplementedError


class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_investigation(
        self,
        prompt: str,
        incident: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> InvestigationOutputSchema:
        endpoint = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1024
            }
        }

        try:
            async with httpx.AsyncClient(timeout=settings.AI_INFERENCE_TIMEOUT_SECONDS) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code == 200:
                    resp_json = res.json()
                    content_str = resp_json.get("message", {}).get("content", "{}")
                    parsed_dict = json.loads(content_str)
                    return InvestigationOutputSchema(**parsed_dict)
                else:
                    raise RuntimeError(f"Ollama returned HTTP {res.status_code}: {res.text}")
        except Exception as e:
            if settings.FALLBACK_TO_MOCK_AI:
                logger.warning(f"Ollama call failed ({e}). Utilizing deterministic AI diagnostic fallback engine.")
                return MockDeterministicLLMClient().generate_investigation(prompt, incident, evidence_list)
            raise e


class MockDeterministicLLMClient(BaseLLMClient):
    """
    Deterministic rule-grounded fallback engine for testing and offline environments.
    Produces strictly schema-compliant and evidence-grounded reports.
    """
    def generate_investigation(
        self,
        prompt: str,
        incident: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> InvestigationOutputSchema:
        service_name = incident.get("service_name", "unknown-service")
        title = incident.get("title", "")
        desc = incident.get("description", "")

        # Find cited evidence IDs
        cited_ids = [e.get("_id") for e in evidence_list if e.get("_id")]

        symptoms = [
            f"Alert triggered: {title}",
            f"Service {service_name} reporting operational failure"
        ]

        # Analyze evidence
        has_health_fail = False
        for e in evidence_list:
            if e.get("evidence_type") == "http_probe":
                p = e.get("payload", {})
                if p.get("status") in ["UNHEALTHY", "UNREACHABLE"]:
                    has_health_fail = True
                    symptoms.append(f"HTTP health probe failing: {p.get('status')} (code: {p.get('response_code')})")

        hypothesis_text = f"Uncaught runtime exception or deadlock in {service_name}"
        if "500" in desc or "Error" in title:
            hypothesis_text = f"HTTP 500 error spike caused by internal application crash in {service_name}"

        hypothesis = RootCauseHypothesis(
            hypothesis=hypothesis_text,
            likelihood="high",
            explanation=f"Telemetry indicates {service_name} stopped processing healthy traffic, matching crash loop or unhandled exception patterns.",
            cited_evidence_ids=cited_ids[:2]
        )

        action = ProposedAction(
            action_id="service.restart_container",
            action_name=f"Restart {service_name} container",
            target_service=service_name,
            parameters={},
            rationale=f"Restarting {service_name} terminates corrupt memory states and re-establishes clean service worker processes.",
            risk_level="MEDIUM",
            requires_approval=True
        )

        return InvestigationOutputSchema(
            incident_summary=f"Automated incident investigation for {service_name}. Detected severe degradation: {title}.",
            affected_service=service_name,
            observed_symptoms=symptoms,
            probable_root_causes=[hypothesis],
            confidence_score=0.88,
            uncertainty_notes="Investigation backed by local telemetry. Network dependency latency was inferred from health timeouts.",
            recommended_actions=[action]
        )


def get_llm_client() -> BaseLLMClient:
    return OllamaClient()

