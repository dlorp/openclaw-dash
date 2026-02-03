"""Backup verification: check memory files and workspace sync."""

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class BackupConfig:
    """Configuration for backup verification."""

    workspace_path: Path = field(default_factory=lambda: Path.home() / ".openclaw" / "workspace")
    memory_subdir: str = "memory"
    max_age_hours: int = 48  # Memory files older than this are considered stale
    required_files: list[str] = field(
        default_factory=lambda: [
            "AGENTS.md",
            "SOUL.md",
            "USER.md",
            "MEMORY.md",
        ]
    )


@dataclass
class FileCheck:
    """Result of checking a single file."""

    path: str
    exists: bool
    size_bytes: int
    last_modified: datetime | None
    age_hours: float | None
    status: str  # ok, missing, stale, empty


@dataclass
class SyncCheck:
    """Result of checking workspace sync status."""

    is_git_repo: bool
    has_remote: bool
    branch: str
    ahead: int
    behind: int
    uncommitted: int
    last_commit_date: datetime | None
    status: str  # synced, ahead, behind, dirty, not-a-repo


@dataclass
class BackupReport:
    """Complete backup verification report."""

    timestamp: datetime
    workspace_path: str
    file_checks: list[FileCheck]
    memory_checks: list[FileCheck]
    sync_check: SyncCheck
    overall_status: str  # healthy, warning, critical
    issues: list[str]


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


class BackupVerifier:
    """Verify backup status of workspace and memory files."""

    def __init__(self, config: BackupConfig | None = None):
        self.config = config or BackupConfig()

    def check_file(self, path: Path, max_age_hours: int | None = None) -> FileCheck:
        """Check status of a single file."""
        if not path.exists():
            return FileCheck(
                path=str(path),
                exists=False,
                size_bytes=0,
                last_modified=None,
                age_hours=None,
                status="missing",
            )

        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600

        if stat.st_size == 0:
            status = "empty"
        elif max_age_hours and age_hours > max_age_hours:
            status = "stale"
        else:
            status = "ok"

        return FileCheck(
            path=str(path),
            exists=True,
            size_bytes=stat.st_size,
            last_modified=mtime,
            age_hours=round(age_hours, 1),
            status=status,
        )

    def check_required_files(self) -> list[FileCheck]:
        """Check all required workspace files."""
        checks = []
        for filename in self.config.required_files:
            path = self.config.workspace_path / filename
            checks.append(self.check_file(path))
        return checks

    def check_memory_files(self) -> list[FileCheck]:
        """Check recent memory files."""
        memory_dir = self.config.workspace_path / self.config.memory_subdir
        checks = []

        if not memory_dir.exists():
            return [
                FileCheck(
                    path=str(memory_dir),
                    exists=False,
                    size_bytes=0,
                    last_modified=None,
                    age_hours=None,
                    status="missing",
                )
            ]

        # Check for today's and yesterday's memory files
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        for date_str in [today, yesterday]:
            path = memory_dir / f"{date_str}.md"
            checks.append(self.check_file(path, max_age_hours=self.config.max_age_hours))

        # Also check any other recent files
        for path in sorted(memory_dir.glob("*.md"), reverse=True)[:5]:
            if path.name not in [f"{today}.md", f"{yesterday}.md"]:
                checks.append(self.check_file(path, max_age_hours=self.config.max_age_hours * 2))

        return checks

    def check_sync_status(self) -> SyncCheck:
        """Check git sync status of workspace."""
        workspace = self.config.workspace_path

        # Check if it's a git repo
        code, _, _ = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=workspace)
        if code != 0:
            return SyncCheck(
                is_git_repo=False,
                has_remote=False,
                branch="",
                ahead=0,
                behind=0,
                uncommitted=0,
                last_commit_date=None,
                status="not-a-repo",
            )

        # Get current branch
        _, branch, _ = run(["git", "branch", "--show-current"], cwd=workspace)

        # Check for remote
        code, remotes, _ = run(["git", "remote"], cwd=workspace)
        has_remote = bool(remotes.strip())

        # Get ahead/behind counts
        ahead, behind = 0, 0
        if has_remote:
            _, status, _ = run(
                ["git", "rev-list", "--left-right", "--count", f"origin/{branch}...HEAD"],
                cwd=workspace,
            )
            parts = status.split()
            if len(parts) == 2:
                try:
                    behind, ahead = int(parts[0]), int(parts[1])
                except ValueError:
                    pass

        # Check uncommitted changes
        _, diff_output, _ = run(["git", "status", "--porcelain"], cwd=workspace)
        uncommitted = len([line for line in diff_output.split("\n") if line.strip()])

        # Get last commit date
        _, commit_date_str, _ = run(["git", "log", "-1", "--format=%ci"], cwd=workspace)
        try:
            last_commit_date = datetime.fromisoformat(
                commit_date_str.replace(" ", "T").split("+")[0]
            )
        except ValueError:
            last_commit_date = None

        # Determine status
        if uncommitted > 0:
            status = "dirty"
        elif behind > 0:
            status = "behind"
        elif ahead > 0:
            status = "ahead"
        else:
            status = "synced"

        return SyncCheck(
            is_git_repo=True,
            has_remote=has_remote,
            branch=branch,
            ahead=ahead,
            behind=behind,
            uncommitted=uncommitted,
            last_commit_date=last_commit_date,
            status=status,
        )

    def verify(self) -> BackupReport:
        """Run full backup verification."""
        file_checks = self.check_required_files()
        memory_checks = self.check_memory_files()
        sync_check = self.check_sync_status()

        issues = []

        # Check required files
        for check in file_checks:
            if check.status == "missing":
                issues.append(f"Missing required file: {Path(check.path).name}")
            elif check.status == "empty":
                issues.append(f"Empty required file: {Path(check.path).name}")

        # Check memory files
        today_check = next(
            (c for c in memory_checks if datetime.now().strftime("%Y-%m-%d") in c.path), None
        )
        if today_check and today_check.status == "missing":
            issues.append("No memory file for today")

        stale_memory = [c for c in memory_checks if c.status == "stale"]
        if stale_memory:
            issues.append(f"{len(stale_memory)} stale memory file(s)")

        # Check sync status
        if sync_check.status == "dirty":
            issues.append(f"{sync_check.uncommitted} uncommitted changes in workspace")
        elif sync_check.status == "behind":
            issues.append(f"Workspace is {sync_check.behind} commits behind remote")
        elif sync_check.status == "not-a-repo":
            issues.append("Workspace is not a git repository")

        # Determine overall status
        critical_issues = [i for i in issues if "Missing required" in i or "not a git" in i]
        warning_issues = [i for i in issues if i not in critical_issues]

        if critical_issues:
            overall_status = "critical"
        elif warning_issues:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return BackupReport(
            timestamp=datetime.now(),
            workspace_path=str(self.config.workspace_path),
            file_checks=file_checks,
            memory_checks=memory_checks,
            sync_check=sync_check,
            overall_status=overall_status,
            issues=issues,
        )


def format_backup_report(report: BackupReport) -> str:
    """Format backup report for display."""
    status_emoji = {
        "healthy": "✅",
        "warning": "⚠️",
        "critical": "🚨",
    }

    file_emoji = {
        "ok": "✅",
        "missing": "❌",
        "stale": "⏰",
        "empty": "📭",
    }

    sync_emoji = {
        "synced": "✅",
        "ahead": "⬆️",
        "behind": "⬇️",
        "dirty": "📝",
        "not-a-repo": "❌",
    }

    lines = [
        "## 💾 Backup Verification Report",
        "",
        f"**Status:** {status_emoji.get(report.overall_status, '❓')} {report.overall_status.upper()}",
        f"**Workspace:** `{report.workspace_path}`",
        f"**Checked:** {report.timestamp.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    # Issues
    if report.issues:
        lines.append("### ⚠️ Issues Found")
        for issue in report.issues:
            lines.append(f"- {issue}")
        lines.append("")

    # Required files
    lines.append("### 📄 Required Files")
    for check in report.file_checks:
        emoji = file_emoji.get(check.status, "❓")
        name = Path(check.path).name
        if check.exists:
            size = f"{check.size_bytes:,} bytes"
            age = f"{check.age_hours:.0f}h ago" if check.age_hours else "unknown"
            lines.append(f"- {emoji} **{name}** — {size}, {age}")
        else:
            lines.append(f"- {emoji} **{name}** — not found")
    lines.append("")

    # Memory files
    lines.append("### 🧠 Memory Files")
    for check in report.memory_checks:
        emoji = file_emoji.get(check.status, "❓")
        name = Path(check.path).name
        if check.exists:
            size = f"{check.size_bytes:,} bytes"
            age = f"{check.age_hours:.0f}h ago" if check.age_hours else "unknown"
            lines.append(f"- {emoji} **{name}** — {size}, {age}")
        else:
            lines.append(f"- {emoji} **{name}** — not found")
    lines.append("")

    # Sync status
    sync = report.sync_check
    lines.append("### 🔄 Sync Status")
    lines.append(f"- **Status:** {sync_emoji.get(sync.status, '❓')} {sync.status}")

    if sync.is_git_repo:
        lines.append(f"- **Branch:** {sync.branch}")
        if sync.has_remote:
            lines.append(f"- **Ahead/Behind:** ↑{sync.ahead} ↓{sync.behind}")
        if sync.uncommitted:
            lines.append(f"- **Uncommitted:** {sync.uncommitted} files")
        if sync.last_commit_date:
            lines.append(f"- **Last commit:** {sync.last_commit_date.strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


def format_backup_summary(report: BackupReport) -> str:
    """Format a brief backup summary."""
    status_emoji = {
        "healthy": "✅",
        "warning": "⚠️",
        "critical": "🚨",
    }

    emoji = status_emoji.get(report.overall_status, "❓")

    if report.overall_status == "healthy":
        return f"{emoji} Backup status: **healthy** — all files present, workspace synced"
    else:
        issue_summary = "; ".join(report.issues[:3])
        if len(report.issues) > 3:
            issue_summary += f" (+{len(report.issues) - 3} more)"
        return f"{emoji} Backup status: **{report.overall_status}** — {issue_summary}"
