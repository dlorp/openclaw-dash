"""Cron jobs collector."""

import time
from datetime import datetime
from typing import Any

from openclaw_dash.collectors.base import (
    CollectorResult,
    CollectorState,
    parse_json_output,
    run_command,
    update_collector_state,
)
from openclaw_dash.demo import is_demo_mode, mock_cron_jobs

COLLECTOR_NAME = "cron"


def collect() -> dict[str, Any]:
    """Collect cron job information with robust error handling.

    Returns:
        Dictionary containing cron jobs list and counts, with collection metadata.
    """
    start_time = time.time()

    # Return mock data in demo mode
    if is_demo_mode():
        jobs = mock_cron_jobs()
        data = {
            "jobs": jobs,
            "total": len(jobs),
            "enabled": sum(1 for j in jobs if j.get("enabled")),
            "collected_at": datetime.now().isoformat(),
        }
        result = CollectorResult(data=data)
        update_collector_state(COLLECTOR_NAME, result)
        return data

    # Run CLI command
    stdout, error, state = run_command(
        ["openclaw", "cron", "list", "--json"],
        timeout=3.0,
    )

    duration_ms = (time.time() - start_time) * 1000

    if state != CollectorState.OK or stdout is None:
        # Handle specific error cases
        error_type = None
        if state == CollectorState.TIMEOUT:
            error = "Command timed out"
            error_type = "timeout"
        elif state == CollectorState.UNAVAILABLE:
            error = "OpenClaw CLI not found"
            error_type = "cli_not_found"
        elif error:
            error_type = "command_failed"
        else:
            error = "Failed to get cron jobs"

        error_data = {
            "jobs": [],
            "total": 0,
            "enabled": 0,
            "collected_at": datetime.now().isoformat(),
            "error": error,
            "_error_type": error_type,
        }

        result = CollectorResult(
            data=error_data,
            state=state,
            error=error,
            error_type=error_type,
            duration_ms=duration_ms,
        )
        update_collector_state(COLLECTOR_NAME, result)
        return error_data

    # Parse JSON output
    raw_data, parse_error = parse_json_output(stdout, default={})

    if parse_error:
        error_data = {
            "jobs": [],
            "total": 0,
            "enabled": 0,
            "collected_at": datetime.now().isoformat(),
            "error": parse_error,
            "_error_type": "json_parse_error",
        }

        result = CollectorResult(
            data=error_data,
            state=CollectorState.ERROR,
            error=parse_error,
            error_type="json_parse_error",
            duration_ms=duration_ms,
        )
        update_collector_state(COLLECTOR_NAME, result)
        return error_data

    # Process jobs
    jobs = []
    raw_jobs = raw_data.get("jobs", [])

    for j in raw_jobs:
        try:
            jobs.append(
                {
                    "id": j.get("id", j.get("jobId", "?")),
                    "name": j.get("name", j.get("id", "unnamed")),
                    "enabled": j.get("enabled", True),
                    "schedule": j.get("schedule", {}),
                    "last_run": j.get("lastRun"),
                    "next_run": j.get("nextRun"),
                }
            )
        except (TypeError, AttributeError):
            # Skip malformed job entries
            continue

    data = {
        "jobs": jobs,
        "total": len(jobs),
        "enabled": sum(1 for j in jobs if j.get("enabled")),
        "collected_at": datetime.now().isoformat(),
    }

    result = CollectorResult(
        data=data,
        state=CollectorState.OK,
        duration_ms=duration_ms,
    )
    update_collector_state(COLLECTOR_NAME, result)
    return data
