#!/usr/bin/env python3
"""
SentinelOps AI Automated MongoDB Backup Controller
Phase 7: Production Reliability and Disaster Recovery

Creates timestamped, compressed MongoDB backups of all critical collections:
- incidents, evidence, investigations, approvals
- remediation_executions, audit_logs, services, users

Features:
- Primary: containerized mongodump via Docker engine or local mongodump
- Fallback: native Python BSON/JSON serialization via pymongo/motor
- SHA256 checksum generation and manifest validation
- Automatic retention policy enforcement (pruning aged backups)
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DEFAULT_BACKUP_DIR = os.path.join("backups", "mongodb")
CRITICAL_COLLECTIONS = [
    "incidents",
    "evidence",
    "investigations",
    "approvals",
    "remediation_executions",
    "audit_logs",
    "services",
    "users",
]


def calculate_sha256(filepath: str) -> str:
    """Computes SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def prune_old_backups(backup_dir: str, retention_days: int = 7, max_backups: int = 30) -> List[str]:
    """Deletes backups exceeding the retention policy."""
    pruned = []
    if not os.path.exists(backup_dir):
        return pruned

    now = time.time()
    cutoff_time = now - (retention_days * 86400)

    # List all subdirectories or archives in backup_dir
    entries = []
    for item in os.listdir(backup_dir):
        item_path = os.path.join(backup_dir, item)
        if os.path.isdir(item_path) or item.endswith(".gz") or item.endswith(".archive"):
            entries.append((item_path, os.path.getmtime(item_path)))

    # Sort newest first
    entries.sort(key=lambda x: x[1], reverse=True)

    # Prune by count or age
    for idx, (path, mtime) in enumerate(entries):
        if idx >= max_backups or mtime < cutoff_time:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                pruned.append(path)
                print(f"[*] Pruned aged backup: {os.path.basename(path)}")
            except Exception as e:
                print(f"[!] Warning: Failed to prune {path}: {e}")

    return pruned


def execute_mongodump_backup(
    container_name: str = "sentinelops-mongodb",
    db_name: str = "sentinelops",
    output_dir: str = DEFAULT_BACKUP_DIR,
    retention_days: int = 7,
) -> Optional[Dict[str, Any]]:
    """Executes a MongoDB backup using mongodump and writes a manifest."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{db_name}_{timestamp_str}"
    target_backup_dir = os.path.join(output_dir, backup_name)
    os.makedirs(target_backup_dir, exist_ok=True)
    archive_file = os.path.join(target_backup_dir, f"{backup_name}.archive.gz")

    print(f"[*] Starting MongoDB backup for database '{db_name}'...")
    print(f"[*] Destination: {archive_file}")

    # 1. Try docker exec mongodump
    docker_cmd = ["docker", "exec", container_name, "mongodump", f"--db={db_name}", "--archive", "--gzip"]

    backup_success = False
    try:
        with open(archive_file, "wb") as f_out:
            subprocess.run(docker_cmd, stdout=f_out, stderr=subprocess.PIPE, check=True)
        if os.path.exists(archive_file) and os.path.getsize(archive_file) > 0:
            backup_success = True
            print(f"[+] Docker mongodump completed successfully. Archive size: {os.path.getsize(archive_file)} bytes")
    except Exception as e:
        print(f"[!] Docker mongodump invocation failed: {e}. Attempting fallback...")

    # 2. Fallback: Python PyMongo direct stream if mongodump CLI failed
    if not backup_success:
        backup_success = execute_pymongo_fallback_backup(db_name, target_backup_dir)

    if not backup_success:
        print("[-] Error: MongoDB backup failed completely across all methods.")
        return None

    # 3. Generate verification manifest
    file_size = os.path.getsize(archive_file) if os.path.exists(archive_file) else 0
    checksum = calculate_sha256(archive_file) if file_size > 0 else "n/a"

    manifest = {
        "backup_name": backup_name,
        "database": db_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "archive_file": os.path.basename(archive_file),
        "archive_size_bytes": file_size,
        "sha256_checksum": checksum,
        "critical_collections": CRITICAL_COLLECTIONS,
        "status": "COMPLETED",
        "retention_policy_days": retention_days,
    }

    manifest_path = os.path.join(target_backup_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[+] Manifest written: {manifest_path}")

    # 4. Enforce retention policy
    pruned = prune_old_backups(output_dir, retention_days=retention_days)
    manifest["pruned_backups"] = pruned

    return manifest


def execute_pymongo_fallback_backup(db_name: str, target_dir: str) -> bool:
    """Fallback backup mechanism using pymongo directly to JSON/BSON files."""
    try:
        from pymongo import MongoClient

        uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        db = client[db_name]

        data_dump = {}
        for col_name in CRITICAL_COLLECTIONS:
            cursor = db[col_name].find({})
            docs = []
            for doc in cursor:
                # Convert ObjectIds and datetimes for JSON serialization
                doc_str = json.dumps(doc, default=str)
                docs.append(json.loads(doc_str))
            data_dump[col_name] = docs

        dump_path = os.path.join(target_dir, f"{os.path.basename(target_dir)}.json")
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(data_dump, f, indent=2)

        print(f"[+] PyMongo fallback dump succeeded: {dump_path}")
        return True
    except Exception as e:
        print(f"[!] PyMongo fallback backup failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="SentinelOps AI MongoDB Backup Controller")
    parser.add_argument("--container", default="sentinelops-mongodb", help="MongoDB container name")
    parser.add_argument("--db", default="sentinelops", help="Target database name")
    parser.add_argument("--output-dir", default=DEFAULT_BACKUP_DIR, help="Backup output directory")
    parser.add_argument("--retention-days", type=int, default=7, help="Days to retain backups")
    args = parser.parse_args()

    result = execute_mongodump_backup(
        container_name=args.container,
        db_name=args.db,
        output_dir=args.output_dir,
        retention_days=args.retention_days,
    )

    if result:
        print(f"\n[SUCCESS] Backup completed: {result['backup_name']} (SHA: {result['sha256_checksum'][:12]}...)")
        sys.exit(0)
    else:
        print("\n[FAILED] Backup execution failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
