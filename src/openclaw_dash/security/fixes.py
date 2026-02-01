"""Auto-fix capabilities for security issues."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_dash.security.audit import AuditResult
from openclaw_dash.security.deps import DependencyScanResult


@dataclass
class FixAction:
    """A fix action taken or suggested."""

    finding_title: str
    action: str  # applied, suggested, failed
    command: str | None = None
    description: str = ""
    error: str | None = None


@dataclass
class FixResult:
    """Result of applying fixes."""

    actions: list[FixAction] = field(default_factory=list)
    applied_count: int = 0
    suggested_count: int = 0
    failed_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "applied": self.applied_count,
            "suggested": self.suggested_count,
            "failed": self.failed_count,
            "actions": [
                {
                    "finding": a.finding_title,
                    "action": a.action,
                    "command": a.command,
                    "description": a.description,
                    "error": a.error,
                }
                for a in self.actions
            ],
        }


class SecurityFixer:
    """Applies security fixes."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.result = FixResult()

    def fix_permission(self, path: Path, target_mode: int) -> FixAction:
        """Fix file or directory permissions."""
        action = FixAction(
            finding_title=f"Fix permissions on {path.name}",
            action="pending",
            command=f"chmod {oct(target_mode)[2:]} {path}",
        )

        if self.dry_run:
            action.action = "suggested"
            action.description = f"Would change permissions to {oct(target_mode)}"
            self.result.suggested_count += 1
        else:
            try:
                os.chmod(path, target_mode)
                action.action = "applied"
                action.description = f"Changed permissions to {oct(target_mode)}"
                self.result.applied_count += 1
            except (PermissionError, OSError) as e:
                action.action = "failed"
                action.error = str(e)
                self.result.failed_count += 1

        self.result.actions.append(action)
        return action

    def fix_permissions_from_audit(self, audit_result: AuditResult) -> None:
        """Apply permission fixes from audit findings."""
        for finding in audit_result.findings:
            if finding.category != "permissions" or not finding.auto_fixable:
                continue

            if not finding.path:
                continue

            path = Path(finding.path)
            if not path.exists():
                continue

            # Determine target mode based on file vs directory
            if path.is_dir():
                target_mode = 0o700
            else:
                target_mode = 0o600

            self.fix_permission(path, target_mode)

    def suggest_dependency_updates(self, scan_result: DependencyScanResult) -> list[dict[str, Any]]:
        """Generate suggested dependency updates."""
        updates: dict[str, dict[str, Any]] = {}

        for vuln in scan_result.vulnerabilities:
            if not vuln.fix_version:
                continue

            key = f"{vuln.source}:{vuln.package}"
            if key not in updates:
                updates[key] = {
                    "package": vuln.package,
                    "current_version": vuln.installed_version,
                    "target_version": vuln.fix_version,
                    "source": vuln.source,
                    "vulnerabilities_fixed": [],
                }
            updates[key]["vulnerabilities_fixed"].append(vuln.vulnerability_id)

            # Update to highest fix version if multiple vulns
            if vuln.fix_version > updates[key]["target_version"]:
                updates[key]["target_version"] = vuln.fix_version

        suggestions = []
        for update in updates.values():
            cmd = self._get_update_command(update)
            action = FixAction(
                finding_title=f"Update {update['package']}",
                action="suggested",
                command=cmd,
                description=(
                    f"Update from {update['current_version']} to {update['target_version']} "
                    f"(fixes: {', '.join(update['vulnerabilities_fixed'][:3])})"
                ),
            )
            self.result.actions.append(action)
            self.result.suggested_count += 1

            suggestions.append(
                {
                    **update,
                    "command": cmd,
                }
            )

        return suggestions

    def _get_update_command(self, update: dict[str, Any]) -> str:
        """Get the appropriate update command for a package."""
        pkg = update["package"]
        version = update["target_version"]
        source = update["source"]

        if source == "npm-audit":
            return f"npm install {pkg}@{version}"
        else:
            return f"pip install '{pkg}>={version}'"

    def apply_dependency_update(self, package: str, version: str, source: str = "pip") -> FixAction:
        """Apply a specific dependency update."""
        if source == "npm-audit" or source == "npm":
            cmd = ["npm", "install", f"{package}@{version}"]
        else:
            cmd = ["pip", "install", f"{package}>={version}"]

        action = FixAction(
            finding_title=f"Update {package} to {version}",
            command=" ".join(cmd),
        )

        if self.dry_run:
            action.action = "suggested"
            action.description = f"Would run: {' '.join(cmd)}"
            self.result.suggested_count += 1
        else:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    action.action = "applied"
                    action.description = f"Successfully updated {package}"
                    self.result.applied_count += 1
                else:
                    action.action = "failed"
                    action.error = result.stderr[:500] if result.stderr else "Unknown error"
                    self.result.failed_count += 1
            except subprocess.TimeoutExpired:
                action.action = "failed"
                action.error = "Update timed out"
                self.result.failed_count += 1
            except Exception as e:
                action.action = "failed"
                action.error = str(e)
                self.result.failed_count += 1

        self.result.actions.append(action)
        return action

    def fix_all(
        self,
        audit_result: AuditResult | None = None,
        dep_result: DependencyScanResult | None = None,
        apply_dep_updates: bool = False,
    ) -> FixResult:
        """Apply all possible fixes."""
        if audit_result:
            self.fix_permissions_from_audit(audit_result)

        if dep_result:
            suggestions = self.suggest_dependency_updates(dep_result)

            if apply_dep_updates and not self.dry_run:
                for sug in suggestions:
                    # Only apply high/critical by default
                    self.apply_dependency_update(
                        sug["package"],
                        sug["target_version"],
                        sug["source"],
                    )

        return self.result


def fix_security_issues(
    audit_result: AuditResult | None = None,
    dep_result: DependencyScanResult | None = None,
    dry_run: bool = True,
) -> FixResult:
    """Convenience function to fix security issues."""
    fixer = SecurityFixer(dry_run=dry_run)
    return fixer.fix_all(audit_result=audit_result, dep_result=dep_result)
