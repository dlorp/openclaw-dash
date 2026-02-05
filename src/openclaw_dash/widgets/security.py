"""Security panel widget for the TUI dashboard."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.security.audit import run_audit
from openclaw_dash.security.deps import DependencyScanner, DependencyScanResult
from openclaw_dash.widgets.ascii_art import STATUS_SYMBOLS, mini_bar, separator


def get_severity_color(severity: str) -> str:
    """Get color for severity level."""
    return {
        "critical": "bold red",
        "high": "red",
        "medium": "yellow",
        "low": "cyan",
        "info": "dim",
    }.get(severity, "white")


def get_severity_icon(severity: str) -> str:
    """Get icon for severity level."""
    return {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🔵",
        "info": "⚪",
    }.get(severity, "•")


class SecurityPanel(Static):
    """Security audit display panel with severity breakdown."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="security-content")

    def refresh_data(self) -> None:
        """Refresh security audit data."""
        try:
            result = run_audit(deep=False)
        except Exception as e:
            content = self.query_one("#security-content", Static)
            content.update(f"[red]Error: {e}[/]")
            return

        content = self.query_one("#security-content", Static)
        findings = result.findings
        summary = result.summary

        if not findings:
            content.update(
                f"[green]{STATUS_SYMBOLS['check']} No security issues[/]\n"
                f"[dim]Scanned {result.scanned_files} files, "
                f"{result.scanned_dirs} dirs[/]"
            )
            return

        lines: list[str] = []

        # Summary header with severity counts
        summary_parts = []
        if summary.get("critical", 0):
            summary_parts.append(f"[bold red]🔴 {summary['critical']}[/]")
        if summary.get("high", 0):
            summary_parts.append(f"[red]🟠 {summary['high']}[/]")
        if summary.get("medium", 0):
            summary_parts.append(f"[yellow]🟡 {summary['medium']}[/]")
        if summary.get("low", 0):
            summary_parts.append(f"[cyan]🔵 {summary['low']}[/]")
        if summary.get("info", 0):
            summary_parts.append(f"[dim]⚪ {summary['info']}[/]")

        lines.append(" ".join(summary_parts))
        lines.append(separator(30, "dotted"))

        # Show findings (limit to first 6 for space)
        for finding in findings[:6]:
            color = get_severity_color(finding.severity)
            icon = get_severity_icon(finding.severity)
            title = finding.title[:38]

            lines.append(f"{icon} [{color}]{title}[/]")

            # Show path if available (truncated)
            if finding.path:
                path_display = finding.path
                if len(path_display) > 35:
                    path_display = "..." + path_display[-32:]
                lines.append(f"   [dim]{path_display}[/]")

        # Show overflow indicator
        remaining = len(findings) - 6
        if remaining > 0:
            lines.append(f"   [dim]... and {remaining} more[/]")

        content.update("\n".join(lines))


class SecuritySummaryPanel(Static):
    """Compact security summary for dashboard overview."""

    def compose(self) -> ComposeResult:
        yield Static("", id="security-summary")

    def refresh_data(self) -> None:
        """Refresh security summary."""
        try:
            result = run_audit(deep=False)
        except Exception:
            content = self.query_one("#security-summary", Static)
            content.update("[dim]? Error[/]")
            return

        content = self.query_one("#security-summary", Static)
        summary = result.summary

        total = sum(summary.values())
        if total == 0:
            content.update(f"[green]{STATUS_SYMBOLS['check']} Secure[/]")
            return

        # Build compact summary
        parts = []
        if summary.get("critical", 0):
            parts.append(f"[bold red]🔴 {summary['critical']}[/]")
        if summary.get("high", 0):
            parts.append(f"[red]🟠 {summary['high']}[/]")
        if summary.get("medium", 0):
            parts.append(f"[yellow]🟡 {summary['medium']}[/]")

        content.update(" ".join(parts) if parts else f"[green]{total} low[/]")


class DepsPanel(Static):
    """Dependency vulnerability panel.

    Scans Python (pip-audit, safety) and Node (npm audit) dependencies
    for known vulnerabilities.
    """

    def __init__(
        self,
        project_dir: Path | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.project_dir = project_dir
        self._last_scan: DependencyScanResult | None = None
        self._last_scan_time: datetime | None = None

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="deps-content")

    def refresh_data(self) -> None:
        """Refresh dependency scan data."""
        content = self.query_one("#deps-content", Static)

        # Cache scans for 5 minutes (scanning is slow)
        now = datetime.now()
        if (
            self._last_scan is not None
            and self._last_scan_time is not None
            and (now - self._last_scan_time).total_seconds() < 300
        ):
            self._render_deps_result(content, self._last_scan)
            return

        try:
            scanner = DependencyScanner(project_dir=self.project_dir)
            result = scanner.scan(include_npm=True)
            self._last_scan = result
            self._last_scan_time = now
            self._render_deps_result(content, result)
        except Exception as e:
            content.update(f"[red]{STATUS_SYMBOLS['cross']} Scan failed[/]\n[dim]{e}[/]")

    def _render_deps_result(self, content: Static, result: DependencyScanResult) -> None:
        """Render the dependency scan result."""
        summary = result.summary
        vulns = result.vulnerabilities

        # No vulnerabilities
        if not vulns:
            no_vuln_lines: list[str] = [
                f"[green]{STATUS_SYMBOLS['check']} No vulnerabilities[/]",
                separator(28, "dotted"),
                f"[dim]Scanned {result.packages_scanned} packages[/]",
            ]
            if result.errors:
                no_vuln_lines.append(
                    f"[yellow]{STATUS_SYMBOLS['warning']} {len(result.errors)} warnings[/]"
                )
            content.update("\n".join(no_vuln_lines))
            return

        lines: list[str] = []
        total = len(vulns)
        critical = summary.get("critical", 0)
        high = summary.get("high", 0)
        medium = summary.get("medium", 0)
        low = summary.get("low", 0)

        # Summary line
        summary_parts = []
        if critical:
            summary_parts.append(f"[bold red]🔴 {critical}[/]")
        if high:
            summary_parts.append(f"[red]🟠 {high}[/]")
        if medium:
            summary_parts.append(f"[yellow]🟡 {medium}[/]")
        if low:
            summary_parts.append(f"[cyan]🔵 {low}[/]")

        lines.append(" ".join(summary_parts))

        # Severity bar visualization
        if total > 0:
            bar_width = 22
            crit_chars = int((critical / total) * bar_width)
            high_chars = int((high / total) * bar_width)
            med_chars = int((medium / total) * bar_width)
            low_chars = bar_width - crit_chars - high_chars - med_chars

            bar = (
                f"[bold red]{'█' * crit_chars}[/]"
                f"[red]{'█' * high_chars}[/]"
                f"[yellow]{'█' * med_chars}[/]"
                f"[cyan]{'░' * low_chars}[/]"
            )
            lines.append(bar)

        lines.append(separator(28, "dotted"))

        # Show top vulnerabilities sorted by severity
        shown = sorted(
            vulns,
            key=lambda v: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(v.severity, 4),
        )[:5]

        for vuln in shown:
            icon = get_severity_icon(vuln.severity)
            color = get_severity_color(vuln.severity)
            pkg = f"{vuln.package}@{vuln.installed_version}"[:24]
            lines.append(f"{icon} [{color}]{pkg}[/]")

            if vuln.fix_version:
                lines.append(f"   [dim]→ fix: {vuln.fix_version}[/]")

        remaining = len(vulns) - 5
        if remaining > 0:
            lines.append(f"   [dim]... +{remaining} more[/]")

        if result.errors:
            lines.append(
                f"\n[yellow]{STATUS_SYMBOLS['warning']} {len(result.errors)} scan errors[/]"
            )

        content.update("\n".join(lines))


class DepsSummaryPanel(Static):
    """Compact dependency vulnerability summary."""

    def __init__(
        self,
        project_dir: Path | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.project_dir = project_dir
        self._last_scan: DependencyScanResult | None = None
        self._last_scan_time: datetime | None = None

    def compose(self) -> ComposeResult:
        yield Static("", id="deps-summary")

    def refresh_data(self) -> None:
        """Refresh dependency summary."""
        content = self.query_one("#deps-summary", Static)

        now = datetime.now()
        if (
            self._last_scan is not None
            and self._last_scan_time is not None
            and (now - self._last_scan_time).total_seconds() < 300
        ):
            self._render_summary(content, self._last_scan)
            return

        try:
            scanner = DependencyScanner(project_dir=self.project_dir)
            result = scanner.scan(include_npm=True)
            self._last_scan = result
            self._last_scan_time = now
            self._render_summary(content, result)
        except Exception:
            content.update("[dim] Deps: scan failed[/]")

    def _render_summary(self, content: Static, result: DependencyScanResult) -> None:
        """Render compact summary."""
        summary = result.summary
        total = len(result.vulnerabilities)

        if total == 0:
            content.update(
                f"[green]{STATUS_SYMBOLS['check']} Deps OK[/] — {result.packages_scanned} pkgs"
            )
            return

        critical = summary.get("critical", 0)
        high = summary.get("high", 0)
        medium = summary.get("medium", 0)

        parts = []
        if critical:
            parts.append(f"[bold red]🔴 {critical}[/]")
        if high:
            parts.append(f"[red]🟠 {high}[/]")
        if medium:
            parts.append(f"[yellow]🟡 {medium}[/]")

        # Risk score bar
        score = min(1.0, (critical * 4 + high * 2 + medium) / 10)
        bar = mini_bar(score, width=5)

        content.update(f" {' '.join(parts)} {bar}")
