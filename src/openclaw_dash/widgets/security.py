"""Security panel widget for the TUI dashboard."""

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.security.audit import run_audit
from openclaw_dash.widgets.ascii_art import STATUS_SYMBOLS, separator


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
                f"[green]{STATUS_SYMBOLS['checkmark']} No security issues[/]\n"
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
            content.update(f"[green]{STATUS_SYMBOLS['checkmark']} Secure[/]")
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
