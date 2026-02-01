"""Version and build information for openclaw-dash."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from functools import lru_cache

__all__ = ["VERSION", "get_version_info", "VersionInfo"]

VERSION = "0.1.0"


@dataclass
class VersionInfo:
    """Version and build metadata."""

    version: str
    git_commit: str | None
    git_branch: str | None
    build_date: str | None

    @property
    def short_commit(self) -> str:
        """Return short git commit hash."""
        if self.git_commit:
            return self.git_commit[:7]
        return "unknown"

    def format_short(self) -> str:
        """Format as compact string for footer display."""
        parts = [f"v{self.version}"]
        if self.git_commit:
            parts.append(self.short_commit)
        return " ".join(parts)

    def format_full(self) -> str:
        """Format as full version string."""
        parts = [f"openclaw-dash v{self.version}"]
        if self.git_commit:
            parts.append(f"({self.short_commit})")
        if self.git_branch and self.git_branch != "main":
            parts.append(f"[{self.git_branch}]")
        return " ".join(parts)


def _run_git(args: list[str]) -> str | None:
    """Run a git command and return output, or None on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


@lru_cache(maxsize=1)
def get_version_info() -> VersionInfo:
    """Get version information including git metadata.

    Results are cached for the lifetime of the process.
    """
    return VersionInfo(
        version=VERSION,
        git_commit=_run_git(["rev-parse", "HEAD"]),
        git_branch=_run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
        build_date=_run_git(["log", "-1", "--format=%ci"]),
    )
