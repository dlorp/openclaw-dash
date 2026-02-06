"""Tests for the alerts collector and widget."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from openclaw_dash import demo
from openclaw_dash.collectors import alerts
from openclaw_dash.collectors.alerts import (
    Alert,
    Severity,
    collect,
    get_severity_color,
    get_severity_icon,
)


class TestAlert:
    """Tests for the Alert dataclass."""

    def test_alert_creation(self):
        alert = Alert(
            severity=Severity.HIGH,
            title="Test alert",
            source="test/source",
            description="Test description",
        )
        assert alert.severity == Severity.HIGH
        assert alert.title == "Test alert"
        assert alert.source == "test/source"
        assert alert.description == "Test description"
        assert isinstance(alert.timestamp, datetime)

    def test_alert_to_dict(self):
        alert = Alert(
            severity=Severity.CRITICAL,
            title="Critical issue",
            source="ci/github",
            url="https://github.com/example",
        )
        data = alert.to_dict()
        assert data["severity"] == "critical"
        assert data["title"] == "Critical issue"
        assert data["source"] == "ci/github"
        assert data["url"] == "https://github.com/example"
        assert "timestamp" in data

    def test_alert_default_metadata(self):
        alert = Alert(severity=Severity.INFO, title="Info", source="test")
        assert alert.metadata == {}


class TestSeverity:
    """Tests for severity levels."""

    def test_severity_ordering(self):
        # Critical should be highest priority (lowest number)
        assert Severity.CRITICAL < Severity.HIGH
        assert Severity.HIGH < Severity.MEDIUM
        assert Severity.MEDIUM < Severity.LOW
        assert Severity.LOW < Severity.INFO

    def test_severity_values(self):
        assert Severity.CRITICAL.value == 1
        assert Severity.INFO.value == 5


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_severity_color(self):
        assert get_severity_color("critical") == "red"
        assert get_severity_color("high") == "red"
        assert get_severity_color("medium") == "yellow"
        assert get_severity_color("low") == "blue"
        assert get_severity_color("info") == "dim"
        assert get_severity_color("unknown") == "white"

    def test_get_severity_icon(self):
        assert get_severity_icon("critical") == "🔴"
        assert get_severity_icon("high") == "🟠"
        assert get_severity_icon("medium") == "🟡"
        assert get_severity_icon("low") == "🔵"
        assert get_severity_icon("info") == ""
        assert get_severity_icon("unknown") == "•"


class TestCollect:
    """Tests for the main collect function."""

    def test_collect_returns_dict(self):
        result = collect(
            include_ci=False,
            include_security=False,
            include_context=False,
        )
        assert isinstance(result, dict)
        assert "alerts" in result
        assert "total" in result
        assert "summary" in result
        assert "collected_at" in result

    def test_collect_summary_keys(self):
        result = collect(
            include_ci=False,
            include_security=False,
            include_context=False,
        )
        summary = result["summary"]
        assert "critical" in summary
        assert "high" in summary
        assert "medium" in summary
        assert "low" in summary
        assert "info" in summary

    def test_collect_alerts_is_list(self):
        result = collect(
            include_ci=False,
            include_security=False,
            include_context=False,
        )
        assert isinstance(result["alerts"], list)

    @patch("openclaw_dash.collectors.alerts.collect_ci_failures")
    def test_collect_includes_ci_when_enabled(self, mock_ci):
        demo.disable_demo_mode()  # Disable demo mode to test real code path
        mock_ci.return_value = [
            Alert(severity=Severity.HIGH, title="CI Failed", source="github/test")
        ]
        result = collect(include_ci=True, include_security=False, include_context=False)
        mock_ci.assert_called_once()
        assert result["total"] >= 1

    @patch("openclaw_dash.collectors.alerts.collect_ci_failures")
    def test_collect_excludes_ci_when_disabled(self, mock_ci):
        collect(include_ci=False, include_security=False, include_context=False)
        mock_ci.assert_not_called()

    def test_alerts_sorted_by_severity(self):
        """Verify that alerts are sorted by severity (critical first)."""
        demo.disable_demo_mode()  # Disable demo mode to test real code path
        with (
            patch("openclaw_dash.collectors.alerts.collect_ci_failures") as mock_ci,
            patch("openclaw_dash.collectors.alerts.collect_security_vulnerabilities") as mock_sec,
            patch("openclaw_dash.collectors.alerts.collect_context_warnings") as mock_ctx,
        ):
            # Return alerts in wrong order
            mock_ci.return_value = [Alert(severity=Severity.LOW, title="Low priority", source="ci")]
            mock_sec.return_value = [
                Alert(severity=Severity.CRITICAL, title="Critical!", source="security")
            ]
            mock_ctx.return_value = [
                Alert(severity=Severity.MEDIUM, title="Medium", source="context")
            ]

            result = collect(include_ci=True, include_security=True, include_context=True)
            alert_list = result["alerts"]

            # Critical should be first
            assert alert_list[0]["severity"] == "critical"
            assert alert_list[1]["severity"] == "medium"
            assert alert_list[2]["severity"] == "low"


class TestCollectCIFailures:
    """Tests for CI failure collection."""

    @patch("subprocess.run")
    def test_returns_empty_list_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = alerts.collect_ci_failures(repos=["test/repo"])
        assert result == []

    @patch("subprocess.run")
    def test_parses_github_response(self, mock_run):
        import json

        now = datetime.now()
        mock_response = [
            {
                "databaseId": 123,
                "name": "CI",
                "conclusion": "failure",
                "createdAt": now.isoformat() + "Z",
                "headBranch": "main",
                "url": "https://github.com/test/repo/actions/runs/123",
            }
        ]
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_response),
        )
        result = alerts.collect_ci_failures(repos=["test/repo"])
        assert len(result) == 1
        assert result[0].source == "github/repo"
        assert result[0].severity == Severity.CRITICAL  # main branch


class TestCollectContextWarnings:
    """Tests for context usage warnings."""

    @patch("subprocess.run")
    def test_no_warning_under_threshold(self, mock_run):
        import json

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"contextUsage": 0.5}),
        )
        result = alerts.collect_context_warnings()
        assert result == []

    @patch("subprocess.run")
    def test_warning_at_high_usage(self, mock_run):
        import json

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"contextUsage": 0.80}),  # 80%
        )
        result = alerts.collect_context_warnings()
        assert len(result) == 1
        assert result[0].severity == Severity.HIGH

    @patch("subprocess.run")
    def test_critical_at_very_high_usage(self, mock_run):
        import json

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"contextUsage": 0.95}),  # 95%
        )
        result = alerts.collect_context_warnings()
        assert len(result) == 1
        assert result[0].severity == Severity.CRITICAL


class TestAlertsWidget:
    """Tests for the AlertsPanel widget."""

    def test_format_time_just_now(self):
        from openclaw_dash.widgets.alerts import AlertsPanel

        panel = AlertsPanel()
        now = datetime.now().isoformat()
        result = panel._format_time(now)
        assert result == "just now"

    def test_format_time_minutes_ago(self):
        from openclaw_dash.widgets.alerts import AlertsPanel

        panel = AlertsPanel()
        past = (datetime.now() - timedelta(minutes=15)).isoformat()
        result = panel._format_time(past)
        assert "m ago" in result

    def test_format_time_hours_ago(self):
        from openclaw_dash.widgets.alerts import AlertsPanel

        panel = AlertsPanel()
        past = (datetime.now() - timedelta(hours=3)).isoformat()
        result = panel._format_time(past)
        assert "h ago" in result

    def test_format_time_days_ago(self):
        from openclaw_dash.widgets.alerts import AlertsPanel

        panel = AlertsPanel()
        past = (datetime.now() - timedelta(days=2)).isoformat()
        result = panel._format_time(past)
        assert "d ago" in result

    def test_format_time_empty(self):
        from openclaw_dash.widgets.alerts import AlertsPanel

        panel = AlertsPanel()
        result = panel._format_time("")
        assert result == "?"
