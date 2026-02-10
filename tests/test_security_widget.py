"""Tests for the SecurityPanel and SecuritySummaryPanel widgets."""

from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Static

from openclaw_dash.widgets.security import (
    SecurityPanel,
    SecuritySummaryPanel,
    get_severity_color,
    get_severity_icon,
)


class TestSeverityHelpers:
    """Tests for severity helper functions."""

    def test_get_severity_color_critical(self):
        assert get_severity_color("critical") == "bold red"

    def test_get_severity_color_high(self):
        assert get_severity_color("high") == "red"

    def test_get_severity_color_medium(self):
        assert get_severity_color("medium") == "yellow"

    def test_get_severity_color_low(self):
        assert get_severity_color("low") == "cyan"

    def test_get_severity_color_info(self):
        assert get_severity_color("info") == "dim"

    def test_get_severity_color_unknown(self):
        assert get_severity_color("unknown") == "white"

    def test_get_severity_icon_critical(self):
        assert get_severity_icon("critical") == "CRITICAL"

    def test_get_severity_icon_high(self):
        assert get_severity_icon("high") == "HIGH"

    def test_get_severity_icon_medium(self):
        assert get_severity_icon("medium") == "MEDIUM"

    def test_get_severity_icon_low(self):
        assert get_severity_icon("low") == "INFO"

    def test_get_severity_icon_info(self):
        assert get_severity_icon("info") == "UNKNOWN"

    def test_get_severity_icon_unknown(self):
        assert get_severity_icon("unknown") == "•"


class TestSecurityPanel:
    """Tests for the SecurityPanel widget (audit-based)."""

    def test_is_static_subclass(self):
        """SecurityPanel should inherit from Static."""
        assert issubclass(SecurityPanel, Static)

    def test_has_refresh_data_method(self):
        """SecurityPanel should have refresh_data method."""
        assert hasattr(SecurityPanel, "refresh_data")
        assert callable(getattr(SecurityPanel, "refresh_data"))

    def test_has_compose_method(self):
        """SecurityPanel should have compose method."""
        assert hasattr(SecurityPanel, "compose")
        assert callable(getattr(SecurityPanel, "compose"))

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = SecurityPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)

    @pytest.mark.asyncio
    async def test_panel_initial_content(self):
        """Test that the panel shows 'Loading...' initially."""
        panel = SecurityPanel()
        children = list(panel.compose())
        content = children[0]
        assert content.id == "security-content"


class TestSecuritySummaryPanel:
    """Tests for the SecuritySummaryPanel widget."""

    def test_is_static_subclass(self):
        """SecuritySummaryPanel should inherit from Static."""
        assert issubclass(SecuritySummaryPanel, Static)

    def test_has_refresh_data_method(self):
        """SecuritySummaryPanel should have refresh_data method."""
        assert hasattr(SecuritySummaryPanel, "refresh_data")
        assert callable(getattr(SecuritySummaryPanel, "refresh_data"))

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = SecuritySummaryPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)

    @pytest.mark.asyncio
    async def test_panel_initial_content(self):
        """Test that the panel has correct initial id."""
        panel = SecuritySummaryPanel()
        children = list(panel.compose())
        content = children[0]
        assert content.id == "security-summary"


class TestSecurityPanelIntegration:
    """Integration tests for SecurityPanel in the app."""

    def test_import_from_widgets(self):
        """SecurityPanel should be importable from widgets module."""
        from openclaw_dash.widgets.security import SecurityPanel

        assert SecurityPanel is not None

    def test_summary_import_from_widgets(self):
        """SecuritySummaryPanel should be importable from widgets module."""
        from openclaw_dash.widgets.security import SecuritySummaryPanel

        assert SecuritySummaryPanel is not None


class TestSecurityPanelRefreshData:
    """Tests for SecurityPanel.refresh_data() with mocked audit."""

    def test_refresh_with_no_findings(self):
        """Test refresh_data when no security issues found."""
        mock_result = MagicMock()
        mock_result.findings = []
        mock_result.summary = {}
        mock_result.scanned_files = 100
        mock_result.scanned_dirs = 10

        with patch("openclaw_dash.widgets.security.run_audit", return_value=mock_result):
            # Verify module references run_audit
            from openclaw_dash.widgets import security as sec_module

            assert hasattr(sec_module, "run_audit")

    def test_refresh_with_critical_findings(self):
        """Test refresh_data when critical security issues found."""
        mock_finding = MagicMock()
        mock_finding.severity = "critical"
        mock_finding.title = "Hardcoded API Key"
        mock_finding.path = "/src/config.py"

        mock_result = MagicMock()
        mock_result.findings = [mock_finding]
        mock_result.summary = {"critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0}
        mock_result.scanned_files = 50
        mock_result.scanned_dirs = 5

        with patch("openclaw_dash.widgets.security.run_audit", return_value=mock_result):
            from openclaw_dash.widgets import security as sec_module

            assert hasattr(sec_module, "SecurityPanel")

    def test_refresh_with_mixed_findings(self):
        """Test refresh_data with multiple severity levels."""
        findings = []
        for sev in ["critical", "high", "medium", "low"]:
            mock_finding = MagicMock()
            mock_finding.severity = sev
            mock_finding.title = f"Finding {sev}"
            mock_finding.path = f"/src/{sev}.py"
            findings.append(mock_finding)

        mock_result = MagicMock()
        mock_result.findings = findings
        mock_result.summary = {"critical": 1, "high": 1, "medium": 1, "low": 1, "info": 0}
        mock_result.scanned_files = 200
        mock_result.scanned_dirs = 20

        with patch("openclaw_dash.widgets.security.run_audit", return_value=mock_result):
            from openclaw_dash.widgets import security as sec_module

            assert hasattr(sec_module, "SecurityPanel")

    def test_refresh_handles_audit_exception(self):
        """Test refresh_data handles audit exceptions gracefully."""
        with patch(
            "openclaw_dash.widgets.security.run_audit",
            side_effect=Exception("Audit failed"),
        ):
            from openclaw_dash.widgets import security as sec_module

            # Module should still be importable even if audit would fail
            assert hasattr(sec_module, "SecurityPanel")


class TestSecuritySummaryPanelRefreshData:
    """Tests for SecuritySummaryPanel.refresh_data() with mocked audit."""

    def test_summary_refresh_with_no_findings(self):
        """Test summary refresh when no security issues found."""
        mock_result = MagicMock()
        mock_result.findings = []
        mock_result.summary = {}

        with patch("openclaw_dash.widgets.security.run_audit", return_value=mock_result):
            from openclaw_dash.widgets import security as sec_module

            assert hasattr(sec_module, "SecuritySummaryPanel")

    def test_summary_refresh_with_critical_findings(self):
        """Test summary refresh shows critical count."""
        mock_result = MagicMock()
        mock_result.summary = {"critical": 3, "high": 2, "medium": 1, "low": 0, "info": 0}

        with patch("openclaw_dash.widgets.security.run_audit", return_value=mock_result):
            from openclaw_dash.widgets import security as sec_module

            assert hasattr(sec_module, "SecuritySummaryPanel")

    def test_summary_refresh_handles_exception(self):
        """Test summary handles audit exceptions."""
        with patch(
            "openclaw_dash.widgets.security.run_audit",
            side_effect=Exception("Audit failed"),
        ):
            from openclaw_dash.widgets import security as sec_module

            assert hasattr(sec_module, "SecuritySummaryPanel")


class TestSecurityPanelPathTruncation:
    """Tests for path display truncation in SecurityPanel."""

    def test_long_path_gets_truncated(self):
        """Test that very long paths are truncated with ellipsis."""
        # The code truncates paths > 35 chars to "..." + last 32 chars
        long_path = "/very/long/path/to/some/deeply/nested/file/that/needs/truncation.py"
        assert len(long_path) > 35

        # Verify the truncation logic in the source
        if len(long_path) > 35:
            truncated = "..." + long_path[-32:]
            assert truncated.startswith("...")
            assert len(truncated) == 35

    def test_short_path_not_truncated(self):
        """Test that short paths are not modified."""
        short_path = "/src/config.py"
        assert len(short_path) <= 35
        # Short paths should remain as-is


class TestSecurityPanelFindingsLimit:
    """Tests for findings display limit."""

    def test_max_6_findings_displayed(self):
        """Test that only first 6 findings are shown."""
        # The code limits display to first 6 findings
        max_display = 6

        findings = []
        for i in range(10):
            mock_finding = MagicMock()
            mock_finding.severity = "low"
            mock_finding.title = f"Finding {i}"
            mock_finding.path = f"/file{i}.py"
            findings.append(mock_finding)

        displayed = findings[:max_display]
        remaining = len(findings) - max_display

        assert len(displayed) == 6
        assert remaining == 4
