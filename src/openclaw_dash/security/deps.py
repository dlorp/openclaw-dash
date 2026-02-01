"""Dependency vulnerability scanning."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class Vulnerability:
    """A dependency vulnerability."""

    package: str
    installed_version: str
    affected_versions: str
    severity: str  # critical, high, medium, low
    vulnerability_id: str
    description: str
    fix_version: Optional[str] = None
    source: str = ""  # pip-audit, npm, safety


@dataclass
class DependencyScanResult:
    """Result of dependency scanning."""

    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    packages_scanned: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    errors: list[str] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for v in self.vulnerabilities:
            counts[v.severity] = counts.get(v.severity, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "packages_scanned": self.packages_scanned,
            "summary": self.summary,
            "errors": self.errors,
            "vulnerabilities": [
                {
                    "package": v.package,
                    "installed_version": v.installed_version,
                    "affected_versions": v.affected_versions,
                    "severity": v.severity,
                    "vulnerability_id": v.vulnerability_id,
                    "description": v.description,
                    "fix_version": v.fix_version,
                    "source": v.source,
                }
                for v in self.vulnerabilities
            ],
        }


class DependencyScanner:
    """Scans dependencies for known vulnerabilities."""

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path.cwd()
        self.result = DependencyScanResult()

    def _map_severity(self, severity: str) -> str:
        """Normalize severity levels."""
        severity = severity.lower()
        if severity in ("critical", "high", "medium", "low"):
            return severity
        if severity in ("important", "severe"):
            return "high"
        if severity == "moderate":
            return "medium"
        if severity in ("minor", "informational"):
            return "low"
        return "medium"  # Default

    def scan_pip_audit(self) -> None:
        """Run pip-audit for Python vulnerabilities."""
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json", "--progress-spinner", "off"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_dir,
            )

            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    # pip-audit returns a list of dicts
                    if isinstance(data, list):
                        for vuln in data:
                            self.result.packages_scanned += 1
                            for v in vuln.get("vulns", []):
                                fix_versions = v.get("fix_versions", [])
                                self.result.vulnerabilities.append(
                                    Vulnerability(
                                        package=vuln.get("name", "unknown"),
                                        installed_version=vuln.get("version", "unknown"),
                                        affected_versions=v.get("affected_versions", "unknown"),
                                        severity=self._map_severity(
                                            v.get("severity", "medium") or "medium"
                                        ),
                                        vulnerability_id=v.get("id", "unknown"),
                                        description=v.get("description", "")[:500],
                                        fix_version=fix_versions[0] if fix_versions else None,
                                        source="pip-audit",
                                    )
                                )
                except json.JSONDecodeError as e:
                    self.result.errors.append(f"pip-audit JSON parse error: {e}")
        except FileNotFoundError:
            self.result.errors.append("pip-audit not installed (pip install pip-audit)")
        except subprocess.TimeoutExpired:
            self.result.errors.append("pip-audit timed out")
        except Exception as e:
            self.result.errors.append(f"pip-audit error: {e}")

    def scan_safety(self) -> None:
        """Run safety for Python vulnerabilities (alternative to pip-audit)."""
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_dir,
            )

            output = result.stdout or result.stderr
            if output:
                try:
                    # safety can return different JSON structures
                    data = json.loads(output)
                    vulns = data if isinstance(data, list) else data.get("vulnerabilities", [])

                    for vuln in vulns:
                        # Handle both old and new safety formats
                        if isinstance(vuln, list) and len(vuln) >= 4:
                            # Old format: [name, affected, installed, desc, id]
                            self.result.vulnerabilities.append(
                                Vulnerability(
                                    package=vuln[0],
                                    installed_version=vuln[2],
                                    affected_versions=vuln[1],
                                    severity="medium",  # safety doesn't provide severity
                                    vulnerability_id=vuln[4] if len(vuln) > 4 else "unknown",
                                    description=vuln[3][:500] if len(vuln) > 3 else "",
                                    source="safety",
                                )
                            )
                        elif isinstance(vuln, dict):
                            # New format
                            self.result.vulnerabilities.append(
                                Vulnerability(
                                    package=vuln.get("package_name", "unknown"),
                                    installed_version=vuln.get("installed_version", "unknown"),
                                    affected_versions=vuln.get("vulnerable_versions", "unknown"),
                                    severity=self._map_severity(
                                        vuln.get("severity", "medium") or "medium"
                                    ),
                                    vulnerability_id=vuln.get("vulnerability_id", "unknown"),
                                    description=vuln.get("advisory", "")[:500],
                                    fix_version=vuln.get("fixed_versions", [None])[0]
                                    if vuln.get("fixed_versions")
                                    else None,
                                    source="safety",
                                )
                            )
                except json.JSONDecodeError:
                    pass  # safety may return non-JSON on success with no vulns
        except FileNotFoundError:
            pass  # Safety is optional, don't report error
        except subprocess.TimeoutExpired:
            self.result.errors.append("safety timed out")
        except Exception:
            pass  # Safety is optional

    def scan_npm_audit(self) -> None:
        """Run npm audit for Node.js vulnerabilities."""
        package_json = self.project_dir / "package.json"
        if not package_json.exists():
            return

        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_dir,
            )

            # npm audit returns non-zero if vulnerabilities found
            if result.stdout:
                try:
                    data = json.loads(result.stdout)

                    # Handle npm v7+ format
                    if "vulnerabilities" in data:
                        for pkg_name, vuln_data in data.get("vulnerabilities", {}).items():
                            self.result.packages_scanned += 1
                            self.result.vulnerabilities.append(
                                Vulnerability(
                                    package=pkg_name,
                                    installed_version=vuln_data.get("version", "unknown"),
                                    affected_versions=vuln_data.get("range", "unknown"),
                                    severity=self._map_severity(
                                        vuln_data.get("severity", "medium")
                                    ),
                                    vulnerability_id=", ".join(
                                        str(v) for v in vuln_data.get("via", [])[:3]
                                        if isinstance(v, str)
                                    )
                                    or "CVE-unknown",
                                    description=vuln_data.get("title", "")[:500],
                                    fix_version=vuln_data.get("fixAvailable", {}).get("version"),
                                    source="npm-audit",
                                )
                            )
                    # Handle npm v6 format
                    elif "advisories" in data:
                        for advisory_id, advisory in data.get("advisories", {}).items():
                            self.result.packages_scanned += 1
                            self.result.vulnerabilities.append(
                                Vulnerability(
                                    package=advisory.get("module_name", "unknown"),
                                    installed_version=advisory.get("findings", [{}])[0].get(
                                        "version", "unknown"
                                    ),
                                    affected_versions=advisory.get("vulnerable_versions", "unknown"),
                                    severity=self._map_severity(advisory.get("severity", "medium")),
                                    vulnerability_id=f"GHSA-{advisory_id}",
                                    description=advisory.get("overview", "")[:500],
                                    fix_version=advisory.get("patched_versions"),
                                    source="npm-audit",
                                )
                            )
                except json.JSONDecodeError as e:
                    self.result.errors.append(f"npm audit JSON parse error: {e}")
        except FileNotFoundError:
            pass  # npm not installed, skip
        except subprocess.TimeoutExpired:
            self.result.errors.append("npm audit timed out")
        except Exception as e:
            self.result.errors.append(f"npm audit error: {e}")

    def scan(self, include_npm: bool = True) -> DependencyScanResult:
        """Run all dependency scans."""
        self.scan_pip_audit()
        self.scan_safety()

        if include_npm:
            self.scan_npm_audit()

        return self.result


def scan_dependencies(project_dir: Optional[Path] = None) -> DependencyScanResult:
    """Convenience function to scan dependencies."""
    scanner = DependencyScanner(project_dir=project_dir)
    return scanner.scan()
