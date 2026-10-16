import os
import sys
import time
import json
import signal
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List

class AuditTracer:
    def __init__(self, output_path: str = None):
        # Resolve output directory via env var or default to current directory
        default_dir = os.getenv("RAGLEMETRY_OUTPUT_DIR", ".")
        default_file = os.path.join(default_dir, "audit_trace.json")
        self.output_path = output_path or default_file
        
        self.trace_data: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self._lock = threading.Lock()
        self._flushed = False

        try:
            signal.signal(signal.SIGINT, self._safe_signal_handler)
        except (ValueError, AttributeError):
            pass

    def _safe_signal_handler(self, signum, frame):
        self.flush()
        sys.exit(130)  # Clean POSIX exit code for SIGINT

    def _sanitize_for_json(self, obj: Any) -> Any:
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, dict):
            return {str(k): self._sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple, set)):
            return [self._sanitize_for_json(i) for i in obj]
        else:
            return str(obj)

    def log(self, stage: str, message: str, details: Dict[str, Any] = None) -> None:
        try:
            elapsed_ms = round((time.time() - self.start_time) * 1000, 2)
            safe_details = self._sanitize_for_json(details or {})

            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_ms": elapsed_ms,
                "stage": str(stage),
                "message": str(message),
                "details": safe_details,
            }

            with self._lock:
                self.trace_data.append(event)

            try:
                print(f"[{elapsed_ms:>7.2f} ms] [{stage:<10}] {message}", flush=True)
            except Exception:
                pass

        except Exception as e:
            try:
                sys.stderr.write(f"[TELEMETRY_INTERNAL_ERROR] Failed to log event: {e}\n")
            except Exception:
                pass  

    def flush(self) -> bool:
        with self._lock:
            if self._flushed:
                return True
            events_snapshot = list(self.trace_data)
            self._flushed = True
    
        try:
            payload = {
                "meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_events": len(events_snapshot),
                    "total_duration_ms": round((time.time() - self.start_time) * 1000, 2)
                },
                "audit_trace": events_snapshot
            }

            # Ensure destination directory exists
            output_dir = os.path.dirname(self.output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)

            print(f"\n[Audit] File safely saved as '{self.output_path}'", flush=True)
            return True

        except Exception as e:
            try:
                sys.stderr.write(f"[TELEMETRY_INTERNAL_ERROR] Failed to flush audit trace: {e}\n")
            except Exception:
                pass  
        return False

tracer = AuditTracer()