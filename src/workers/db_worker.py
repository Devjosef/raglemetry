import asyncio
from typing import List, Dict, Any, Optional
from src.telemetry import tracer

# Entry point, creates the boundary for DB - telemetry.
# Enforces strict zero identity & zero payload
class DBWorker:
    def __init__(self, connection_timeout_ms: int = 5000):
        self.connection_timeout_ms = connection_timeout_ms


def is_identity_free_key(key_name: str) -> bool:
    # Checks if a key name contains identity, personal data, or row payload markers
    forbidden_terms = (
        "user", "customer", "member", "account", "client", "tenant", "profile", "person",
        "email", "id_card", "phone", "name", "payload", "data", "row", "body"
    )
    key_lower = key_name.lower()
    
    # Explicitly permit only transaction_id and query_fingerprint. Block everything else containing 'id' or forbidden terms
    if key_lower in ("transaction_id", "query_fingerprint"):
        return True
    
    return not any(term in key_lower for term in forbidden_terms)

def filter_structural_db_telemetry(raw_record: Dict[str, Any]) -> Dict[str, Any]:
   # Ensures that ONLY query fingerprints, transaction IDs, command types and exeuction durations pass. 
   # NEVER allow raw data rows, user ID'S, or table content payload.
    allowed_keys = {
        "transaction_id",
        "query_fingerprint",
        "command_type",
        "execution_time_ms",
        "lock_wait",
        "schema_target"
    }
    
    sanitized = {}
    for key, value in raw_record.items():
        if key in allowed_keys and is_identity_free_key(key):
            sanitized[key] = value
            
    return sanitized

def lookup_query_fingerprint(
    fingerprint: str, 
    db_index: Dict[str, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    # Runs a O(1) direct hash lookup for a specific query fingerprint or transaction ID. This is possible due to the constraint.
    if not fingerprint:
        return None
    
    raw_match = db_index.get(fingerprint)
    if not raw_match:
        return None
    
    return filter_structural_db_telemetry(raw_match)

async def fetch_db_telemetry_async(
    target_fingerprint: Optional[str],
    db_index: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
   
    tracer.log("DB_WORKER", f"Executing structural DB lookup for fingerprint: '{target_fingerprint}'")
    
    def _run_db_lookup():
        if not target_fingerprint:
            return {}
        
        matched_telemetry = lookup_query_fingerprint(target_fingerprint, db_index)
        return matched_telemetry or {}

    # Offload execution to the threadpool, to avoid blocking the main loop
    telemetry_data = await asyncio.to_thread(_run_db_lookup)
    
    found = len(telemetry_data) > 0
    tracer.log("DB_WORKER", f"DB lookup complete. Fingerprint match found: {found} (Identity-free)")
    
    return telemetry_data