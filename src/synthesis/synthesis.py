import json
from typing import Dict, Any, List

from src.telemetry import tracer


# Entry point for prompts and its boundaries & constraints.
class DiagnosticCompiler:
    def __init__(self, target_model: str = "gpt-4o"):
        self.target_model = target_model



CLOSED_LOOP_PROMPT_TEMPLATE = """[1. CONSTRAINT / ROLE]
Act as Raglemetry's Root Cause Diagnostic Compiler. You are an elite, deterministic Systems Incident Inspector.
You do not hypothesize, speculate, or fill in knowledge gaps.

[2. FRAMEWORK]
Analyze the provided AUDIT TRACE under a strict Closed-Loop Verification Methodology.
Treat the input trace as a Deterministic Finite Automaton (DFA) execution log.

[3. PARAMETERS]
- Variable A (Trace Input State):
```json
{audit_trace_json}
```

- Variable B (Invariants): Reduced Hallucination, Mandatory Source Citations, Zero PII Exposure.
- Variable C (Halting Condition): If evidence in Variable A contains zero failure indicators, output "HALT: NO SYSTEM FAILURE DETECTED" and stop token generation.

[4. EXECUTION CONSTRAINTS]
Do not output generic pleasantries, intros, conversational setups, or summaries. Go straight to the markdown report.

CITATION RULE: Every claim, commit SHA, error message, or DDL command MUST include a direct citation to the source stage and identifier (e.g., [Git: a8f9c2d], [Log: line 42], [DB: transaction_id]).

SHORTCIRCUIT RULE: Evaluate the telemetry evidence. If the root cause cannot be definitively proven from Variable A alone, halt immediately and output:

"INSUFFICIENT TELEMETRY EVIDENCE FOR CONCLUSION: Missing [Target Dependency / Missing Log / Unmatched Commit]"

Do not process any further tokens or speculate on hypothetical causes.

Output exclusively in the following rigid structure:

Incident Root Cause Summary
Status: [CONFIRMED / INSUFFICIENT TELEMETRY]
Core Diagnosis: [1-2 sentences stating the exact verified failure point with direct citation]

Evidence & Verification
Source Stage
Identifier / Citation
Verified Observation
[e.g., Log Scanner]
[e.g., Log: line 104]
[Exact matched line/code without assumptions]

[e.g., Git Worker]
[e.g., Git: a8f9c2d]
[Exact commit payload details]

[e.g., DB Worker]
[e.g., DB: CMD_1089]
[Structural transaction execution state]

Timeline of Events (Ground Truth DFA Trace)
[Elapsed MS] [Stage]: [Verified transition event extracted directly from timestamps]
"""

# Filters the raw audit trace down to the actionable worker.
def extract_diagnostic_events(
    audit_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    
    diagnostic_events = []

    for event in audit_events:
        stage = event.get("stage", "")

        # Retain only deterministic worker stages that contain evidence.
        if stage in ("LOG_WORKER", "GIT_WORKER", "DB_WORKER", "SCRUBBER"):
            diagnostic_events.append(
                {
                    "ms": event.get("elapsed_ms"),
                    "stage": stage,
                    "message": event.get("message"),
                    "details": event.get("details", {}),
                }
            )

    return diagnostic_events

# Formats the filtered audit events into the closed loop prompt.
def build_synthesis_prompt(audit_events: List[Dict[str, Any]]) -> str:
   
    tracer.log(
        "SYNTHESIS",
        "Compiling closed-loop prompt payload from audit trace",
    )

    clean_events = extract_diagnostic_events(audit_events)
    formatted_json = json.dumps(clean_events, indent=2)

    prompt = CLOSED_LOOP_PROMPT_TEMPLATE.format(
        audit_trace_json=formatted_json
    )

    tracer.log(
        "SYNTHESIS",
        f"Closed-loop prompt successfully compiled ({len(prompt)} characters)",
    )

    return prompt