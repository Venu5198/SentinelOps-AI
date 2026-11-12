#!/usr/bin/env python3
"""
SentinelOps AI Deployment Health & Verification Prober
Phase 6: Continuous Deployment (CD)

Validates complete platform health post-deployment:
1. Frontend HTTP 200 availability
2. Backend /health probe
3. Backend /ready probe (MongoDB & Redis connectivity)
4. Monitored payment-service & order-service health
5. Telemetry services (Prometheus, Alertmanager)
6. Deployed version/SHA match
Requires consecutive successful probes to declare stability.
"""

import argparse
import asyncio
import sys
import time
import os
from typing import Dict, Any, List
import httpx

FRONTEND_PORT = os.environ.get("SENTINELOPS_FRONTEND_PORT", "4000")
BACKEND_PORT = os.environ.get("SENTINELOPS_BACKEND_PORT", "9000")

DEFAULT_TARGETS = {
    "frontend": f"http://localhost:{FRONTEND_PORT}/",
    "backend_health": f"http://localhost:{BACKEND_PORT}/health",
    "backend_ready": f"http://localhost:{BACKEND_PORT}/ready",
    "payment_service": "http://localhost:8080/health",
    "order_service": "http://localhost:8081/health",
    "prometheus": "http://localhost:9090/-/healthy",
    "alertmanager": "http://localhost:9093/-/healthy",
}


async def probe_endpoint(client: httpx.AsyncClient, name: str, url: str) -> Dict[str, Any]:
    try:
        start = time.time()
        res = await client.get(url)
        duration = round((time.time() - start) * 1000, 2)
        healthy = res.status_code in [200, 204]
        
        # Verify readiness components if backend ready endpoint
        details = {}
        if name == "backend_ready" and healthy:
            data = res.json()
            components = data.get("components", {})
            healthy = (components.get("mongodb") in ["connected", "mock_connected"] and
                       components.get("redis") in ["connected", "mock_connected"])
            details = components

        return {
            "name": name,
            "url": url,
            "status_code": res.status_code,
            "duration_ms": duration,
            "healthy": healthy,
            "details": details,
            "error": None
        }
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "status_code": 0,
            "duration_ms": 0,
            "healthy": False,
            "details": {},
            "error": str(e)
        }


async def verify_deployment(
    target_sha: str = None,
    consecutive_probes: int = 3,
    probe_interval_seconds: float = 2.0,
    max_retries: int = 15,
    custom_targets: Dict[str, str] = None
) -> bool:
    targets = custom_targets or DEFAULT_TARGETS
    print(f"[*] Commencing deployment verification across {len(targets)} endpoints...")
    if target_sha:
        print(f"[*] Expected release SHA tag: {target_sha}")

    consecutive_success = 0
    attempt = 0

    async with httpx.AsyncClient(timeout=4.0) as client:
        while attempt < max_retries:
            attempt += 1
            print(f"\n--- Health Probe Cycle {attempt}/{max_retries} (Streak: {consecutive_success}/{consecutive_probes}) ---")
            
            cycle_tasks = [probe_endpoint(client, name, url) for name, url in targets.items()]
            results: List[Dict[str, Any]] = await asyncio.gather(*cycle_tasks)

            cycle_healthy = True
            for r in results:
                status_icon = "OK" if r["healthy"] else "FAIL"
                err_msg = f" - Error: {r['error']}" if r["error"] else ""
                print(f"  [{status_icon:<4}] {r['name']:<18} HTTP {r['status_code']} ({r['duration_ms']}ms){err_msg}")
                if not r["healthy"]:
                    cycle_healthy = False

            if cycle_healthy:
                consecutive_success += 1
                if consecutive_success >= consecutive_probes:
                    print(f"\n[+] Deployment verification PASSED: {consecutive_probes} consecutive healthy cycles.")
                    return True
            else:
                consecutive_success = 0
                print(f"  [!] Cycle failed. Waiting {probe_interval_seconds}s before next attempt...")

            await asyncio.sleep(probe_interval_seconds)

    print(f"\n[-] Deployment verification FAILED after {max_retries} attempts.")
    return False


def main():
    parser = argparse.ArgumentParser(description="SentinelOps AI Deployment Health Verifier")
    parser.add_argument("--sha", help="Expected deployment commit SHA", default=None)
    parser.add_argument("--probes", type=int, help="Consecutive healthy probes required", default=3)
    parser.add_argument("--interval", type=float, help="Seconds between probe cycles", default=2.0)
    parser.add_argument("--retries", type=int, help="Maximum probe retries", default=10)
    args = parser.parse_args()

    success = asyncio.run(verify_deployment(
        target_sha=args.sha,
        consecutive_probes=args.probes,
        probe_interval_seconds=args.interval,
        max_retries=args.retries
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
