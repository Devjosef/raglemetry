# Raglemetry

**Audit-Focused Telemetry Compilation for Incident Response**

## Introduction

During a 2 A.M. incident call, engineers spend valuable time hunting through monolithic codebases, microservice logs, and cloud platform consoles. While generative AI can speed up prioritization, Large Language Models are probabilistic systems subject to hallucination and variance. In critical production failures, relying solely on ungrounded AI summaries creates dangerous confirmation bias.

Raglemetry enforces an **ABS (Audit Before Synthesis)** architecture:

- **Deterministic Retrieval:** Parallel asynchronous workers scan live system artifacts (Git, logs, DDL database telemetry) without waiting for vector database embedding updates.
- **Immutable Audit Trace:** Before any synthesis occurs, Raglemetry emits a structured, human-readable `audit_trace.json` representing ground truth.
- **Pluggable Context Compilation:** The framework compiles the verified audit trace into a structured prompt, allowing you to plug in any local model runtime (e.g., Ollama, Mistral, Llama.cpp) or inspect the raw prompt directly.

## What Raglemetry Is & Is Not

| What Raglemetry IS | What Raglemetry IS NOT |
|---|---|
| **A Local Diagnostic Utility:** Designed to run locally as an air-gapped shell tool or container. | **A Commercial SaaS:** It contains zero telemetry tracking, cloud SaaS dependencies, or subscription billing hooks. |
| **A Deterministic Auditer:** Relies on Boyer-Moore scanning and direct hash lookups with \(O(1)\) complexity rather than vector embeddings. | **An Autonomous Agent:** It does not execute remote remediation scripts or modify production servers automatically. |
| **Provider-Agnostic:** Decouples trace generation from model execution, supporting local offline runtimes out-of-the-box. | **A Monolithic APM:** It is a targeted incident-response compiler, not a 24/7 application performance monitoring suite. |

## System Architecture

```text
               ┌──► Worker 1: Git Service (Commit SHAs, Diff) ────────┐
               │                                                      │
               ├──► Worker 2: Log Scanner (Sublinear String Match) ───┼──► audit_trace.json
[ Alert Trigger ]                                                     │    (Ground Truth)
               ├──► Worker 3: DB Execution Log (Fingerprint State) ───┤          │
               │                                                      │          │
               └──► Worker 4: Local Runtime / Pluggable LLM Client ───┘          ▼
                                                                        Strict Compiler Prompt
                                                                           & Diagnostic Report
```

## Key Technical Mechanisms

### Retrieval 

Rather than maintaining vector indexes on fast-changing log streams, Raglemetry uses targeted hash lookups and Boyer-Moore pattern scanning. This provides instant, index-free scanning over raw telemetry files.

### Latency & Graceful Interruption

Workers run concurrently using asynchronous threads. If execution is interrupted (e.g., via `Ctrl+C`), the thread-safe telemetry wrapper flushes all collected state up to that millisecond, preserving the truth in `audit_trace.json`.

### Enforcement & Anti-Hallucination

To prevent models from fabricating details, the prompt template enforces strict structural boundaries, requiring direct source stage citations for every claim or commit SHA.

### Input Handling & Redaction

Log messages, commit messages, and query statements can contain sensitive data:

- **Secret Scrubbing:** PII, JWTs, bearer tokens, and email addresses are sanitized at the worker layer before writing to disk.
- **SQL Sanitization:** Query string literals are stripped to prevent data leakage.

## Directory Structure

```text
raglemetry/
├── README.md
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .dockerignore
├── src/
│   ├── main.py             # Entry point & CLI handler
│   ├── telemetry.py        # Real-time audit logger & graceful shutdown
│   ├── ingestion/          # Data parsers & PII/secret scrubbing
│   ├── workers/            # Concurrent search workers & circuit breakers
│   └── synthesis/          # Prompt framing & citation verifier
│       ├── synthesis.py    # Deterministic prompt compilation
│       └── llm_client.py   # Pluggable local LLM runtime (Ollama/fallback)
├── mock/                   # Ground-truth mock incident artifacts
│   ├── app.log             # Sample microservice application logs
│   ├── db_telemetry.json   # Sample structural database transaction logs
│   └── git_history.json    # Sample commit history and metadata
├── output/                 # Local runtime output directory
│   └── audit_trace.json    # Generated immutable ground truth trace
└── tests/                  # Unit & integration test suites
```

## Quick Start & Usage

### 1. Run via Docker

```bash
docker-compose -f docker/docker-compose.yml up --build
```

### 2. Trigger an Incident Diagnostic

```bash
python -m src.main --alert "TIMEOUT" --sha a8f9c2d --fingerprint FP_ERR_504
```

If execution is interrupted during a scan (`Ctrl+C`), the telemetry wrapper preserves your data:

```text
[Audit] File safely saved as 'output/audit_trace.json'
```

## Configuration (`.env`)

You can configure local model execution behavior via environment variables:

```dotenv
RAGLEMETRY_OUTPUT_DIR=output
RAGLEMETRY_LLM_PROVIDER=ollama
OLLAMA_MODEL=mistral
OLLAMA_HOST=http://localhost:11434/api/generate
```

## License

MIT License. See [`LICENSE`](LICENSE) for details.
