import json
from typing import Any, Dict, List

import httpx

from backend.ai.prompt_builder import SYSTEM_PROMPT
from backend.core.config import settings
from backend.core.logger import logger
from backend.models.investigation import InvestigationOutputSchema, ProposedAction, RootCauseHypothesis


class BaseLLMClient:
    async def generate_investigation(
        self, prompt: str, incident: Dict[str, Any], evidence_list: List[Dict[str, Any]]
    ) -> InvestigationOutputSchema:
        raise NotImplementedError


class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_investigation(
        self, prompt: str, incident: Dict[str, Any], evidence_list: List[Dict[str, Any]]
    ) -> InvestigationOutputSchema:
        candidate_urls = [self.base_url]
        if "host.docker.internal" in self.base_url:
            candidate_urls.append("http://localhost:11434")
        elif "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            candidate_urls.append("http://host.docker.internal:11434")
        candidate_urls = list(dict.fromkeys(candidate_urls))

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 1024},
        }

        last_error = None
        for base in candidate_urls:
            endpoint = f"{base}/api/chat"
            try:
                timeout_cfg = httpx.Timeout(float(settings.AI_INFERENCE_TIMEOUT_SECONDS), connect=3.0)
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    res = await client.post(endpoint, json=payload)
                    if res.status_code == 200:
                        resp_json = res.json()
                        content_str = resp_json.get("message", {}).get("content", "{}").strip()
                        if content_str.startswith("```json"):
                            content_str = content_str[7:]
                        if content_str.startswith("```"):
                            content_str = content_str[3:]
                        if content_str.endswith("```"):
                            content_str = content_str[:-3]
                        content_str = content_str.strip()
                        parsed_dict = json.loads(content_str)
                        logger.info(f"Live Ollama inference succeeded via {base} using {self.model}")
                        return InvestigationOutputSchema(**parsed_dict)
                    else:
                        last_error = RuntimeError(f"Ollama returned HTTP {res.status_code}: {res.text}")
            except (json.JSONDecodeError, ValueError) as val_err:
                logger.warning(f"Ollama output validation or JSON parse error from {base}: {val_err}")
                last_error = val_err
            except httpx.TimeoutException as timeout_err:
                logger.warning(
                    f"Ollama inference timed out after {settings.AI_INFERENCE_TIMEOUT_SECONDS}s on {base}: {timeout_err}"
                )
                last_error = timeout_err
            except Exception as e:
                logger.warning(f"Ollama connection or inference error on {base}: {e}")
                last_error = e

        if settings.FALLBACK_TO_MOCK_AI:
            logger.warning(f"Ollama call failed ({last_error}). Utilizing deterministic AI diagnostic fallback engine.")
            return MockDeterministicLLMClient().generate_investigation(prompt, incident, evidence_list)
        raise last_error


class MockDeterministicLLMClient(BaseLLMClient):
    """
    Deterministic rule-grounded fallback engine for testing and offline environments.
    Produces strictly schema-compliant and evidence-grounded reports.
    """

    def generate_investigation(
        self, prompt: str, incident: Dict[str, Any], evidence_list: List[Dict[str, Any]]
    ) -> InvestigationOutputSchema:
        service_name = incident.get("service_name", "unknown-service")
        title = incident.get("title", "")
        desc = incident.get("description", "")

        # Find cited evidence IDs
        cited_ids = [e.get("_id") for e in evidence_list if e.get("_id")]

        symptoms = [f"Alert triggered: {title}", f"Service {service_name} reporting operational failure"]

        # Analyze evidence
        has_health_fail = False
        for e in evidence_list:
            if e.get("evidence_type") == "http_probe":
                p = e.get("payload", {})
                if p.get("status") in ["UNHEALTHY", "UNREACHABLE"]:
                    has_health_fail = True
                    symptoms.append(f"HTTP health probe failing: {p.get('status')} (code: {p.get('response_code')})")

        hypothesis_text = f"Uncaught runtime exception or deadlock in {service_name}"
        if has_health_fail:
            hypothesis_text = f"Service unreachable or process terminated in {service_name}"
        elif "500" in desc or "Error" in title:
            hypothesis_text = f"HTTP 500 error spike caused by internal application crash in {service_name}"

        hypothesis = RootCauseHypothesis(
            hypothesis=hypothesis_text,
            likelihood="high",
            explanation=f"Telemetry indicates {service_name} stopped processing healthy traffic, matching crash loop or unhandled exception patterns.",
            cited_evidence_ids=cited_ids[:2],
        )

        action = ProposedAction(
            action_id="service.restart_container",
            action_name=f"Restart {service_name} container",
            target_service=service_name,
            parameters={},
            rationale=f"Restarting {service_name} terminates corrupt memory states and re-establishes clean service worker processes.",
            risk_level="MEDIUM",
            requires_approval=True,
        )

        return InvestigationOutputSchema(
            incident_summary=f"Automated incident investigation for {service_name}. Detected severe degradation: {title}.",
            affected_service=service_name,
            observed_symptoms=symptoms,
            probable_root_causes=[hypothesis],
            confidence_score=0.88,
            uncertainty_notes="Investigation backed by local telemetry. Network dependency latency was inferred from health timeouts.",
            recommended_actions=[action],
        )


def get_llm_client() -> BaseLLMClient:
    return OllamaClient()
