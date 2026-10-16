import argparse
import asyncio
import sys
import shutil
from typing import Dict, Any

from src.telemetry import tracer
from src.workers.log_scanner import scan_log_async
from src.workers.git_worker import fetch_git_context_async
from src.workers.db_worker import fetch_db_telemetry_async
from src.ingestion.scrubbers import scrub_audit_payload
from src.synthesis.synthesis import build_synthesis_prompt

class RaglemetryCLI:
    def __init__(self, log_path: str, search_pattern: str, target_sha: str = None, target_fingerprint: str = None):
        self.log_path = log_path
        self.search_pattern = search_pattern
        self.target_sha = target_sha
        self.target_fingerprint = target_fingerprint


MOCK_GIT_INDEX = {
    "a8f9c2d": {
        "sha": "a8f9c2d",
        "author": "dev-alice",
        "timestamp": "2026-09-25T01:45:00Z",
        "message": "refactor(db): update pool connection timeout to 200ms",
        "files_changed": ["src/db/pool.py", "config/database.yaml"]
    }
}

MOCK_DB_INDEX = {
    "FP_ERR_504": {
        "transaction_id": "TX_99201",
        "query_fingerprint": "FP_ERR_504",
        "command_type": "DDL_ALTER",
        "execution_time_ms": 4820,
        "lock_wait": True,
        "schema_target": "active_sessions"
    }
}


async def run_diagnostic_pipeline(
    log_path: str,
    search_pattern: str,
    target_sha: str = None,
    target_fingerprint: str = None
) -> Dict[str, Any]:
   
    tracer.log("MAIN", "Initializing Raglemetry concurrent audit scan")

    try:
        log_task = scan_log_async(log_path, search_pattern)
        git_task = fetch_git_context_async(target_sha, None, MOCK_GIT_INDEX)
        db_task = fetch_db_telemetry_async(target_fingerprint, MOCK_DB_INDEX)

        log_results, git_results, db_results = await asyncio.gather(
            log_task, git_task, db_task, return_exceptions=True
        )

        raw_telemetry = {
            "logs": log_results if not isinstance(log_results, Exception) else [],
            "git": git_results if not isinstance(git_results, Exception) else {},
            "db": db_results if not isinstance(db_results, Exception) else {}
        }

        tracer.log("SCRUBBER", "Sanitizing collected worker payloads")
        clean_telemetry = scrub_audit_payload(raw_telemetry)

        prompt_payload = build_synthesis_prompt(tracer.trace_data)

        tracer.log("MAIN", "Diagnostic pipeline execution completed successfully")

        return {
            "telemetry": clean_telemetry,
            "synthesis_prompt": prompt_payload
        }

    except Exception as e:
        tracer.log("MAIN_ERROR", f"Uncaught pipeline error: {str(e)}")
        return {}

    finally:
        tracer.flush()


def check_local_runtimes() -> None:
    """Scans the host system for common local model runtimes or CLI binaries."""
    runtimes = ["ollama", "llama-cli", "lmstudio", "llamacpp"]
    detected = [rt for rt in runtimes if shutil.which(rt)]
    
    if detected:
        print(f"[Check] Detected local model runtimes: {', '.join(detected)}")
    else:
        print("[Check] No standard local runtimes detected in PATH (running in standalone audit trace mode).")


def main():
    parser = argparse.ArgumentParser(description="Raglemetry: Audit Before Synthesis (ABS) Diagnostic Engine")
    parser.add_argument("--log-path", default="app.log", help="Path to incident log file")
    parser.add_argument("--pattern", "--alert", dest="pattern", default="TIMEOUT", help="Search pattern or alert text")
    parser.add_argument("--sha", default="a8f9c2d", help="Git commit SHA to lookup")
    parser.add_argument("--fingerprint", default="FP_ERR_504", help="DB query fingerprint")

    args = parser.parse_args()

    cli = RaglemetryCLI(args.log_path, args.pattern, args.sha, args.fingerprint)
    
    print("=" * 60)
    print(" RAGLEMETRY: Audit Before Synthesis (ABS) Diagnostic Engine ")
    print("=" * 60)

    # Perform agnostic local environment check
    check_local_runtimes()

    result = asyncio.run(
        run_diagnostic_pipeline(
            cli.log_path,
            cli.search_pattern,
            cli.target_sha,
            cli.target_fingerprint
        )
    )

    if result.get("synthesis_prompt"):
        print("\n--- COMPILED SYNTHESIS PROMPT HARNESS ---")
        print(result["synthesis_prompt"])


if __name__ == "__main__":
    main()