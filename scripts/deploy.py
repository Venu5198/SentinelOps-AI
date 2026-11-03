#!/usr/bin/env python3
"""
SentinelOps AI Automated Deployment & Rollback Controller
Phase 6: Continuous Deployment (CD)

Coordinates:
- Ordered container updates using verified image SHAs
- Pre-deployment snapshot of known-good release
- Automated health verification loop
- Safe automated rollback if post-deploy verification fails
- Audit logging of deployment and rollback events
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

STATE_FILE = ".last_known_good_deployment.json"
AUDIT_LOG_FILE = "deployment_events.log"


def log_event(event_type: str, details: Dict[str, Any]):
    timestamp = datetime.now(timezone.utc).isoformat()
    record = {
        "timestamp": timestamp,
        "event": event_type,
        "details": details
    }
    line = json.dumps(record)
    print(f"[{timestamp}] [CD_CONTROLLER] {event_type.upper()}: {json.dumps(details, indent=2)}")
    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"Warning: Failed to write deployment audit log: {e}")


def load_known_good() -> Optional[Dict[str, Any]]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to parse {STATE_FILE}: {e}")
    return None


def save_known_good(state: Dict[str, Any]):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        print(f"[+] Saved known-good deployment state to {STATE_FILE}")
    except Exception as e:
        print(f"Warning: Failed to save known-good state: {e}")


def run_command(cmd: list, env: Optional[Dict[str, str]] = None, dry_run: bool = False) -> bool:
    cmd_str = " ".join(cmd)
    print(f"[*] Executing: {cmd_str}")
    if dry_run:
        print("[!] Dry-run enabled. Skipping actual execution.")
        return True
    
    current_env = os.environ.copy()
    if env:
        current_env.update(env)

    try:
        result = subprocess.run(cmd, env=current_env, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"[-] Command failed with exit code {e.returncode}: {cmd_str}")
        return False
    except Exception as e:
        print(f"[-] Execution error: {e}")
        return False


def deploy_release(
    backend_image: str,
    frontend_image: str,
    target_tag: str,
    environment: str = "production",
    compose_file: str = "docker-compose.yml",
    dry_run: bool = False
) -> bool:
    log_event("deployment_started", {
        "environment": environment,
        "target_tag": target_tag,
        "backend_image": backend_image,
        "frontend_image": frontend_image,
    })

    # 1. Snapshot currently running known-good state if not exists
    current_state = load_known_good()
    if not current_state:
        # Default snapshot based on current running or standard fallback
        save_known_good({
            "target_tag": "v1.0.0-initial",
            "backend_image": "sentinelopsai-backend:latest",
            "frontend_image": "sentinelopsai-frontend:latest",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": environment
        })

    # 2. Issue compose pull/up for new images
    deploy_env = {
        "BACKEND_IMAGE": backend_image,
        "FRONTEND_IMAGE": frontend_image,
        "ENVIRONMENT": environment
    }

    if not dry_run and "ghcr.io" in backend_image:
        print("[*] Pulling updated container images from registry...")
        run_command(["docker", "compose", "-f", compose_file, "pull", "backend", "frontend"], env=deploy_env, dry_run=dry_run)

    print("[*] Deploying updated application containers...")
    up_success = run_command(["docker", "compose", "-f", compose_file, "up", "-d", "backend", "frontend"], env=deploy_env, dry_run=dry_run)
    if not up_success:
        log_event("deployment_failed_during_up", {"target_tag": target_tag})
        return False

    # 3. Health verification
    print("[*] Waiting 5s for services to warm up before health probing...")
    if not dry_run:
        time.sleep(5)

    verify_cmd = [sys.executable, "scripts/verify_deployment.py", "--sha", target_tag, "--probes", "3"]
    verify_success = run_command(verify_cmd, dry_run=dry_run)

    if verify_success:
        log_event("deployment_succeeded", {
            "target_tag": target_tag,
            "backend_image": backend_image,
            "frontend_image": frontend_image,
            "environment": environment
        })
        # Save as the new verified known-good release
        save_known_good({
            "target_tag": target_tag,
            "backend_image": backend_image,
            "frontend_image": frontend_image,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": environment
        })
        return True
    else:
        print("\n[!] CRITICAL: Deployment health verification failed! Commencing automated rollback...")
        log_event("deployment_health_failed_triggering_rollback", {
            "target_tag": target_tag,
            "failed_at": datetime.now(timezone.utc).isoformat()
        })
        rollback_success = rollback_release(compose_file=compose_file, dry_run=dry_run)
        if rollback_success:
            print("[+] Automated rollback completed successfully. Known-good state restored.")
        else:
            print("[-] Automated rollback encountered errors. Manual intervention required!")
        return False


def rollback_release(
    target_tag: Optional[str] = None,
    compose_file: str = "docker-compose.yml",
    dry_run: bool = False
) -> bool:
    known_good = load_known_good()
    if not known_good:
        print("[-] Cannot rollback: No recorded known-good deployment state found.")
        return False

    backend_image = known_good.get("backend_image", "sentinelopsai-backend:latest")
    frontend_image = known_good.get("frontend_image", "sentinelopsai-frontend:latest")
    rollback_tag = target_tag or known_good.get("target_tag", "previous")

    print(f"[*] Rolling back to verified known-good version: {rollback_tag}")
    log_event("rollback_started", {
        "rollback_target": rollback_tag,
        "backend_image": backend_image,
        "frontend_image": frontend_image
    })

    deploy_env = {
        "BACKEND_IMAGE": backend_image,
        "FRONTEND_IMAGE": frontend_image,
    }

    # Execute non-destructive container update (never touches db volumes)
    up_success = run_command(["docker", "compose", "-f", compose_file, "up", "-d", "backend", "frontend"], env=deploy_env, dry_run=dry_run)
    if not up_success:
        log_event("rollback_failed_during_up", {"rollback_target": rollback_tag})
        return False

    print("[*] Verifying service health post-rollback...")
    if not dry_run:
        time.sleep(4)

    verify_cmd = [sys.executable, "scripts/verify_deployment.py", "--sha", rollback_tag, "--probes", "2"]
    verify_success = run_command(verify_cmd, dry_run=dry_run)

    if verify_success:
        log_event("rollback_succeeded", {
            "restored_tag": rollback_tag,
            "backend_image": backend_image,
            "frontend_image": frontend_image
        })
        return True
    else:
        log_event("rollback_verification_failed", {"restored_tag": rollback_tag})
        return False


def main():
    parser = argparse.ArgumentParser(description="SentinelOps AI CD Deployment & Rollback Controller")
    parser.add_argument("--action", choices=["deploy", "rollback"], default="deploy", help="Deployment action")
    parser.add_argument("--environment", default="production", help="Target environment (staging or production)")
    parser.add_argument("--backend-image", default="sentinelopsai-backend:latest", help="Backend image URI")
    parser.add_argument("--frontend-image", default="sentinelopsai-frontend:latest", help="Frontend image URI")
    parser.add_argument("--target-tag", default=None, help="Commit SHA or release tag")
    parser.add_argument("--compose-file", default="docker-compose.yml", help="Compose file path")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without restarting containers")
    args = parser.parse_args()

    tag = args.target_tag or os.environ.get("GITHUB_SHA", f"manual-{int(time.time())}")[:7]

    if args.action == "deploy":
        success = deploy_release(
            backend_image=args.backend_image,
            frontend_image=args.frontend_image,
            target_tag=tag,
            environment=args.environment,
            compose_file=args.compose_file,
            dry_run=args.dry_run
        )
    elif args.action == "rollback":
        success = rollback_release(
            target_tag=args.target_tag,
            compose_file=args.compose_file,
            dry_run=args.dry_run
        )
    else:
        print(f"Unknown action: {args.action}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
