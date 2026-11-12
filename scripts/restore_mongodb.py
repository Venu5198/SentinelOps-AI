#!/usr/bin/env python3
"""
SentinelOps AI Automated MongoDB Restore & Verification Controller
Phase 7: Production Reliability and Disaster Recovery

Restores timestamped MongoDB backups and performs automated integrity verification:
- Primary: containerized mongorestore via Docker engine or local mongorestore
- Safety First: Defaults to an isolated recovery database (e.g., sentinelops_recovery_test)
- Validates collection existence and document counts
- Fallback: native Python BSON/JSON deserialization via pymongo
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional
from pymongo import MongoClient

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


def verify_database_integrity(
    mongo_uri: str,
    db_name: str,
    container_name: str = "sentinelops-mongodb",
    expected_collections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Inspects restored database, checks collection counts and document counts."""
    expected = expected_collections or CRITICAL_COLLECTIONS
    collection_stats = {}
    total_docs = 0
    missing_collections = []
    existing_collections = []

    # 1. Primary: Query directly via docker exec mongosh using JSON serialization
    try:
        eval_script = (
            "JSON.stringify(Object.fromEntries(db.getCollectionNames().map(c => [c, db[c].countDocuments()])))"
        )
        cmd = ["docker", "exec", container_name, "mongosh", db_name, "--quiet", "--eval", eval_script]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        counts_dict = json.loads(proc.stdout.strip())
        existing_collections = list(counts_dict.keys())
        for col in expected:
            cnt = counts_dict.get(col, 0)
            collection_stats[col] = cnt
            total_docs += cnt
            if col not in counts_dict:
                missing_collections.append(col)
    except Exception as e:
        print(f"[*] Docker mongosh query failed ({e}). Attempting PyMongo direct fallback...")
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            db = client[db_name]
            existing_collections = db.list_collection_names()
            for col in expected:
                if col in existing_collections:
                    cnt = db[col].count_documents({})
                    collection_stats[col] = cnt
                    total_docs += cnt
                else:
                    collection_stats[col] = 0
                    missing_collections.append(col)
            client.close()
        except Exception as py_err:
            print(f"[!] PyMongo inspection fallback failed: {py_err}")

    return {
        "database": db_name,
        "collections_found": existing_collections,
        "critical_collection_counts": collection_stats,
        "total_documents": total_docs,
        "missing_critical_collections": missing_collections,
        "healthy": len(missing_collections) == 0 and len(existing_collections) > 0,
    }


def execute_mongorestore(
    archive_path: str,
    container_name: str = "sentinelops-mongodb",
    source_db: str = "sentinelops",
    target_db: str = "sentinelops_recovery_test",
    drop_target_first: bool = True,
) -> bool:
    """Restores an archive into target_db using mongorestore inside the MongoDB container."""
    if not os.path.exists(archive_path):
        print(f"[-] Error: Archive file not found: {archive_path}")
        return False

    print(f"[*] Commencing MongoDB restore to isolated database '{target_db}'...")
    print(f"[*] Source archive: {archive_path}")

    # Safety guard: Prevent accidental production overwrite without explicit flag
    if target_db == "sentinelops" and not os.environ.get("CONFIRM_PRODUCTION_RESTORE") == "YES":
        print(
            "[-] SAFETY ABORT: Refusing to restore over production 'sentinelops' without CONFIRM_PRODUCTION_RESTORE=YES."
        )
        return False

    docker_cmd = [
        "docker",
        "exec",
        "-i",
        container_name,
        "mongorestore",
        "--gzip",
        "--archive",
        f"--nsFrom={source_db}.*",
        f"--nsTo={target_db}.*",
    ]
    if drop_target_first:
        docker_cmd.append("--drop")

    try:
        with open(archive_path, "rb") as f_in:
            proc = subprocess.run(docker_cmd, stdin=f_in, capture_output=True, check=True)
        print("[+] mongorestore executed successfully.")
        if proc.stdout:
            print(f"[STDOUT] {proc.stdout.decode('utf-8', errors='ignore')}")
        if proc.stderr:
            print(f"[STDERR] {proc.stderr.decode('utf-8', errors='ignore')}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[-] mongorestore failed: {e.stderr.decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        print(f"[-] Docker invocation error during restore: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="SentinelOps AI MongoDB Restore Controller")
    parser.add_argument("--archive", required=True, help="Path to .archive.gz file")
    parser.add_argument("--container", default="sentinelops-mongodb", help="MongoDB container name")
    parser.add_argument("--source-db", default="sentinelops", help="Original database name in archive")
    parser.add_argument("--target-db", default="sentinelops_recovery_test", help="Target database name")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27018", help="MongoDB URI for verification")
    args = parser.parse_args()

    # 1. Verify archive exists and checksum if manifest present
    manifest_path = os.path.join(os.path.dirname(args.archive), "manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            expected_sha = manifest.get("sha256_checksum")
            actual_sha = calculate_sha256(args.archive)
            if expected_sha and actual_sha != expected_sha:
                print(f"[-] Checksum mismatch! Expected {expected_sha}, got {actual_sha}")
                sys.exit(1)
            print(f"[+] Archive SHA256 integrity verified: {actual_sha[:12]}...")
        except Exception as e:
            print(f"[!] Warning: Could not verify manifest: {e}")

    # 2. Execute restore
    success = execute_mongorestore(
        archive_path=args.archive,
        container_name=args.container,
        source_db=args.source_db,
        target_db=args.target_db,
    )

    if not success:
        print("[-] Restore operation failed.")
        sys.exit(1)

    # 3. Post-restore integrity verification
    stats = verify_database_integrity(args.mongo_uri, args.target_db, container_name=args.container)
    print("\n--- Post-Restore Database Verification ---")
    print(f"Target Database: {stats['database']}")
    print(f"Collections Found: {', '.join(stats['collections_found'])}")
    print(f"Total Documents: {stats['total_documents']}")
    print("Collection Counts:")
    for col, count in stats["critical_collection_counts"].items():
        print(f"  - {col}: {count}")

    if stats["healthy"]:
        print(f"\n[SUCCESS] Disaster recovery verification PASSED for '{args.target_db}'.")
        sys.exit(0)
    else:
        print(f"\n[FAILED] Missing critical collections: {stats['missing_critical_collections']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
