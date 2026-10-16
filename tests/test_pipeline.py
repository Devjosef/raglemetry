import pytest
from src.main import run_diagnostic_pipeline, RaglemetryCLI

@pytest.mark.asyncio
async def test_run_diagnostic_pipeline_handles_missing_files_gracefully():
    cli = RaglemetryCLI("non_existent_file.log", "PATTERN", "invalid_sha", "invalid_fp")
    result = await run_diagnostic_pipeline(
        cli.log_path,
        cli.search_pattern,
        cli.target_sha,
        cli.target_fingerprint
    )
    
    assert "synthesis_prompt" in result
    assert "INSUFFICIENT TELEMETRY" in result["synthesis_prompt"] or "CLOSED_LOOP_PROMPT_TEMPLATE" in str(result)