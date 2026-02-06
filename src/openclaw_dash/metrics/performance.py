"""Performance metrics - response times, error rates, tool call analysis."""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_dash.demo import is_demo_mode, mock_metrics

DEFAULT_METRICS_DIR = Path.home() / ".openclaw" / "workspace" / "metrics"
GATEWAY_LOG_DIR = Path.home() / ".openclaw" / "logs"
TMP_LOG_DIR = Path("/tmp/openclaw")


@dataclass
class ToolCallMetric:
    """Metrics for a single tool call type."""

    name: str
    count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_ms: float = 0
    avg_ms: float = 0
    error_rate: float = 0


class PerformanceMetrics:
    """Collect and analyze performance metrics from logs."""

    def __init__(self, metrics_dir: Path | None = None):
        self.metrics_dir = metrics_dir or DEFAULT_METRICS_DIR
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.perf_file = self.metrics_dir / "performance.json"

        # Patterns for log parsing
        self.ws_pattern = re.compile(r"\[ws\] ⇄ res ([✓✗]) (\S+) (\d+)ms")
        self.tool_error_pattern = re.compile(r"tool.*(?:error|failed|exception)", re.IGNORECASE)

    def _load_history(self) -> dict[str, Any]:
        """Load performance history from disk."""
        if self.perf_file.exists():
            try:
                return json.loads(self.perf_file.read_text())
            except (OSError, json.JSONDecodeError):
                pass
        return {"daily": {}, "last_parsed_pos": {}}

    def _save_history(self, data: dict[str, Any]) -> None:
        """Save performance history to disk."""
        self.perf_file.write_text(json.dumps(data, indent=2, default=str))

    def _find_log_files(self) -> list[Path]:
        """Find gateway log files to parse."""
        logs: list[Path] = []

        # Check ~/.openclaw/logs/
        if GATEWAY_LOG_DIR.exists():
            logs.extend(GATEWAY_LOG_DIR.glob("gateway*.log"))

        # Check /tmp/openclaw/
        if TMP_LOG_DIR.exists():
            logs.extend(TMP_LOG_DIR.glob("openclaw-*.log"))

        return sorted(logs, key=lambda p: p.stat().st_mtime, reverse=True)[:3]

    def _parse_log_line(self, line: str) -> dict[str, Any] | None:
        """Parse a single log line for relevant metrics."""
        # Try JSON format first
        try:
            if line.strip().startswith("{"):
                data = json.loads(line)
                # Check for embedded log content
                if "0" in data and isinstance(data["0"], str):
                    # Nested content, skip for now
                    return None
                return data
        except json.JSONDecodeError:
            pass

        # Try plain text ws pattern
        match = self.ws_pattern.search(line)
        if match:
            success = match.group(1) == "✓"
            action = match.group(2)
            latency_ms = int(match.group(3))
            return {
                "type": "ws_response",
                "action": action,
                "success": success,
                "latency_ms": latency_ms,
            }

        # Check for tool errors
        if self.tool_error_pattern.search(line):
            return {"type": "tool_error", "raw": line[:200]}

        return None

    def parse_logs(self) -> dict[str, ToolCallMetric]:
        """Parse gateway logs for performance data."""
        logs: list[Path] = self._find_log_files()
        tool_metrics: dict[str, ToolCallMetric] = {}

        for log_file in logs:
            try:
                with open(log_file, errors="ignore") as f:
                    for line in f:
                        parsed = self._parse_log_line(line)
                        if not parsed:
                            continue

                        if parsed.get("type") == "ws_response":
                            action = parsed["action"]
                            if action not in tool_metrics:
                                tool_metrics[action] = ToolCallMetric(name=action)

                            m = tool_metrics[action]
                            m.count += 1
                            m.total_ms += parsed["latency_ms"]
                            if parsed["success"]:
                                m.success_count += 1
                            else:
                                m.error_count += 1
            except OSError:
                continue

        # Calculate averages
        for m in tool_metrics.values():
            if m.count > 0:
                m.avg_ms = round(m.total_ms / m.count, 2)
                m.error_rate = round(m.error_count / m.count * 100, 2)

        return tool_metrics

    def collect(self) -> dict[str, Any]:
        """Collect current performance metrics."""
        # Return mock data in demo mode
        if is_demo_mode():
            mock_data = mock_metrics()
            return {
                "summary": {
                    "total_calls": mock_data["requests_today"],
                    "total_errors": mock_data["errors_today"],
                    "error_rate_pct": mock_data["error_rate"] * 100,
                    "avg_latency_ms": mock_data["avg_latency_ms"],
                },
                "slowest": [
                    {"name": "browser.screenshot", "avg_ms": 1250, "count": 12},
                    {"name": "exec", "avg_ms": 890, "count": 45},
                ],
                "error_prone": [
                    {"name": "web_fetch", "error_rate": 5.0, "errors": 2},
                ],
                "by_action": {},
                "collected_at": datetime.now().isoformat(),
            }

        history = self._load_history()
        today = datetime.now().date().isoformat()

        # Parse logs
        tool_metrics = self.parse_logs()

        # Aggregate stats
        total_calls = sum(m.count for m in tool_metrics.values())
        total_errors = sum(m.error_count for m in tool_metrics.values())
        total_latency = sum(m.total_ms for m in tool_metrics.values())

        avg_latency = round(total_latency / total_calls, 2) if total_calls > 0 else 0
        error_rate = round(total_errors / total_calls * 100, 2) if total_calls > 0 else 0

        # Top slowest actions
        sorted_by_latency = sorted(tool_metrics.values(), key=lambda m: m.avg_ms, reverse=True)[:5]

        # Most error-prone actions
        sorted_by_errors = sorted(
            [m for m in tool_metrics.values() if m.error_count > 0],
            key=lambda m: m.error_rate,
            reverse=True,
        )[:5]

        # Update daily history
        if today not in history["daily"]:
            history["daily"][today] = {
                "total_calls": 0,
                "total_errors": 0,
                "avg_latency_ms": 0,
            }

        history["daily"][today].update(
            {
                "total_calls": total_calls,
                "total_errors": total_errors,
                "avg_latency_ms": avg_latency,
                "updated_at": datetime.now().isoformat(),
            }
        )

        self._save_history(history)

        return {
            "summary": {
                "total_calls": total_calls,
                "total_errors": total_errors,
                "error_rate_pct": error_rate,
                "avg_latency_ms": avg_latency,
            },
            "slowest": [
                {"name": m.name, "avg_ms": m.avg_ms, "count": m.count} for m in sorted_by_latency
            ],
            "error_prone": [
                {"name": m.name, "error_rate": m.error_rate, "errors": m.error_count}
                for m in sorted_by_errors
            ],
            "by_action": {name: asdict(m) for name, m in tool_metrics.items()},
            "collected_at": datetime.now().isoformat(),
        }

    def get_trend(self, days: int = 7) -> list[dict[str, Any]]:
        """Get daily performance trend."""
        history = self._load_history()
        dates = sorted(history["daily"].keys(), reverse=True)[:days]
        return [{"date": d, **history["daily"][d]} for d in dates]
