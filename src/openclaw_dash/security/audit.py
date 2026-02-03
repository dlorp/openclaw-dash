"""Main security audit runner."""

from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Common secret patterns to detect
SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?", "API Key"),
    (r"(?i)(secret|token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?", "Secret/Token"),
    (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?", "Password"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"xox[baprs]-[a-zA-Z0-9\-]{10,}", "Slack Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}", "Bearer Token"),
    (r"AIza[0-9A-Za-z_\-]{35}", "Google API Key"),
    (r"(?i)discord[_\-]?token\s*[:=]\s*['\"]?([a-zA-Z0-9_\.\-]{50,})['\"]?", "Discord Token"),
]

# Files/dirs to skip when scanning
SKIP_PATTERNS = [
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env.example",
    "*.pyc",
    "*.log",
]


@dataclass
class Finding:
    """A security finding."""

    severity: str  # critical, high, medium, low, info
    category: str  # secrets, permissions, config
    title: str
    description: str
    path: str | None = None
    line: int | None = None
    recommendation: str = ""
    auto_fixable: bool = False


@dataclass
class AuditResult:
    """Result of a security audit."""

    findings: list[Finding] = field(default_factory=list)
    scanned_files: int = 0
    scanned_dirs: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "scanned_files": self.scanned_files,
            "scanned_dirs": self.scanned_dirs,
            "summary": self.summary,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "description": f.description,
                    "path": f.path,
                    "line": f.line,
                    "recommendation": f.recommendation,
                    "auto_fixable": f.auto_fixable,
                }
                for f in self.findings
            ],
        }


class SecurityAudit:
    """Main security audit class."""

    def __init__(self, openclaw_dir: Path | str | None = None):
        self.openclaw_dir = Path(openclaw_dir) if openclaw_dir else Path.home() / ".openclaw"
        self.result = AuditResult()

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        name = path.name
        for pattern in SKIP_PATTERNS:
            if "*" in pattern:
                if path.match(pattern):
                    return True
            elif name == pattern:
                return True
        return False

    def scan_secrets(self, deep: bool = False) -> None:
        """Scan for exposed secrets in config files."""
        config_files = [
            self.openclaw_dir / "config.json",
            self.openclaw_dir / "config.yaml",
            self.openclaw_dir / "config.yml",
            self.openclaw_dir / ".env",
            self.openclaw_dir / "credentials.json",
        ]

        # Add workspace files in deep mode
        if deep:
            workspace = self.openclaw_dir / "workspace"
            if workspace.exists():
                for ext in ["*.json", "*.yaml", "*.yml", "*.env", "*.toml", "*.ini", "*.conf"]:
                    config_files.extend(workspace.rglob(ext))

        for config_file in config_files:
            if not config_file.exists():
                continue
            if self._should_skip(config_file):
                continue

            self.result.scanned_files += 1

            try:
                content = config_file.read_text(errors="ignore")
            except (PermissionError, OSError):
                continue

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern, secret_type in SECRET_PATTERNS:
                    if re.search(pattern, line):
                        # Check if it's likely a placeholder
                        if any(
                            ph in line.lower() for ph in ["example", "xxx", "your_", "changeme"]
                        ):
                            continue

                        self.result.findings.append(
                            Finding(
                                severity="critical",
                                category="secrets",
                                title=f"Potential {secret_type} exposed",
                                description=f"Found potential {secret_type} in plaintext",
                                path=str(config_file),
                                line=line_num,
                                recommendation="Move secrets to environment variables or a secure vault",
                                auto_fixable=False,
                            )
                        )
                        break  # One finding per line

    def check_permissions(self) -> None:
        """Check file permissions on OpenClaw directory."""
        if not self.openclaw_dir.exists():
            self.result.findings.append(
                Finding(
                    severity="info",
                    category="permissions",
                    title="OpenClaw directory not found",
                    description=f"{self.openclaw_dir} does not exist",
                    path=str(self.openclaw_dir),
                )
            )
            return

        self.result.scanned_dirs += 1

        # Check main directory permissions
        try:
            dir_stat = self.openclaw_dir.stat()
            dir_mode = stat.S_IMODE(dir_stat.st_mode)

            # Should be 700 (rwx------) or 750 at most
            if dir_mode & 0o077:  # Others or group have any access
                dir_mode & 0o004
                world_writable = dir_mode & 0o002
                group_writable = dir_mode & 0o020

                severity = "high" if (world_writable or group_writable) else "medium"

                self.result.findings.append(
                    Finding(
                        severity=severity,
                        category="permissions",
                        title="OpenClaw directory too permissive",
                        description=f"Directory has mode {oct(dir_mode)} (should be 0700)",
                        path=str(self.openclaw_dir),
                        recommendation=f"chmod 700 {self.openclaw_dir}",
                        auto_fixable=True,
                    )
                )
        except (PermissionError, OSError) as e:
            self.result.findings.append(
                Finding(
                    severity="medium",
                    category="permissions",
                    title="Cannot check directory permissions",
                    description=str(e),
                    path=str(self.openclaw_dir),
                )
            )

        # Check sensitive files
        sensitive_files = [
            "config.json",
            "credentials.json",
            ".env",
            "state.json",
            "tokens.json",
        ]

        for filename in sensitive_files:
            filepath = self.openclaw_dir / filename
            if not filepath.exists():
                continue

            self.result.scanned_files += 1

            try:
                file_stat = filepath.stat()
                file_mode = stat.S_IMODE(file_stat.st_mode)

                # Should be 600 (rw-------) or 640 at most
                if file_mode & 0o077:
                    self.result.findings.append(
                        Finding(
                            severity="high" if file_mode & 0o007 else "medium",
                            category="permissions",
                            title=f"Sensitive file too permissive: {filename}",
                            description=f"File has mode {oct(file_mode)} (should be 0600)",
                            path=str(filepath),
                            recommendation=f"chmod 600 {filepath}",
                            auto_fixable=True,
                        )
                    )
            except (PermissionError, OSError):
                continue

    def check_config(self) -> None:
        """Check for weak configuration settings."""
        config_path = self.openclaw_dir / "config.json"
        if not config_path.exists():
            return

        self.result.scanned_files += 1

        try:
            config = json.loads(config_path.read_text())
        except (json.JSONDecodeError, PermissionError, OSError):
            return

        # Check for auth disabled
        if config.get("auth", {}).get("enabled") is False:
            self.result.findings.append(
                Finding(
                    severity="high",
                    category="config",
                    title="Authentication disabled",
                    description="Auth is explicitly disabled in config",
                    path=str(config_path),
                    recommendation="Enable authentication for production use",
                    auto_fixable=False,
                )
            )

        # Check for open endpoints
        if config.get("server", {}).get("host") in ["0.0.0.0", "::"]:
            if not config.get("auth", {}).get("enabled", True):
                self.result.findings.append(
                    Finding(
                        severity="critical",
                        category="config",
                        title="Server exposed without authentication",
                        description="Server bound to all interfaces with auth disabled",
                        path=str(config_path),
                        recommendation="Either enable auth or bind to localhost only",
                        auto_fixable=False,
                    )
                )
            else:
                self.result.findings.append(
                    Finding(
                        severity="medium",
                        category="config",
                        title="Server bound to all interfaces",
                        description="Server is accessible from network (0.0.0.0)",
                        path=str(config_path),
                        recommendation="Consider binding to localhost if not needed externally",
                    )
                )

        # Check for debug mode
        if config.get("debug") is True or config.get("server", {}).get("debug") is True:
            self.result.findings.append(
                Finding(
                    severity="medium",
                    category="config",
                    title="Debug mode enabled",
                    description="Debug mode may expose sensitive information",
                    path=str(config_path),
                    recommendation="Disable debug mode in production",
                    auto_fixable=False,
                )
            )

        # Check for insecure TLS settings
        tls_config = config.get("tls", config.get("ssl", {}))
        if tls_config.get("verify") is False or tls_config.get("insecure") is True:
            self.result.findings.append(
                Finding(
                    severity="high",
                    category="config",
                    title="TLS verification disabled",
                    description="TLS/SSL certificate verification is disabled",
                    path=str(config_path),
                    recommendation="Enable TLS verification to prevent MITM attacks",
                    auto_fixable=False,
                )
            )

    def run(self, deep: bool = False) -> AuditResult:
        """Run all security audits."""
        import time

        start = time.time()

        self.scan_secrets(deep=deep)
        self.check_permissions()
        self.check_config()

        self.result.duration_ms = int((time.time() - start) * 1000)
        return self.result


def run_audit(deep: bool = False, openclaw_dir: Path | None = None) -> AuditResult:
    """Convenience function to run a security audit."""
    audit = SecurityAudit(openclaw_dir=openclaw_dir)
    return audit.run(deep=deep)
