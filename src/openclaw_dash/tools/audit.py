#!/usr/bin/env python3
from __future__ import annotations

"""Security audit tool for Python and JavaScript projects.

Checks for:
  - Known vulnerabilities in dependencies (pip-audit, npm audit)
  - Hardcoded secrets (basic patterns)
  - Dangerous code patterns (eval, pickle, shell=True)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from config import get_repo_base, get_repos


def run_cmd(
    cmd: list[str], cwd: str | None = None, check: bool = False
) -> subprocess.CompletedProcess:
    """Run a command and return result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check, cwd=cwd)


# Secret patterns to check for
SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']{10,}["\']', "API key"),
    (r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\'][^"\']{6,}["\']', "Secret/password"),
    (r'(?i)(token)\s*[=:]\s*["\'][^"\']{10,}["\']', "Token"),
    (r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}", "Bearer token"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub personal access token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth token"),
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
]

# Dangerous code patterns
DANGEROUS_PATTERNS = [
    (r"\beval\s*\(", "eval() usage"),
    (r"\bexec\s*\(", "exec() usage"),
    (r"pickle\.loads?\s*\(", "pickle usage (insecure deserialization)"),
    (r"shell\s*=\s*True", "subprocess shell=True"),
    (r"__import__\s*\(", "dynamic import"),
    (r"os\.system\s*\(", "os.system() usage"),
    (r"subprocess\.call\([^)]*shell\s*=\s*True", "subprocess with shell=True"),
    (r"yaml\.load\s*\([^)]*\)", "yaml.load without Loader (use safe_load)"),
]


def check_pip_audit(path: Path) -> list[dict]:
    """Run pip-audit if available."""
    issues = []

    # Check if pip-audit is available
    result = run_cmd(["pip-audit", "--version"])
    if result.returncode != 0:
        return [{"type": "info", "message": "pip-audit not installed (pip install pip-audit)"}]

    # Check for requirements.txt or pyproject.toml
    has_python = (path / "requirements.txt").exists() or (path / "pyproject.toml").exists()
    if not has_python:
        return []

    result = run_cmd(["pip-audit", "--format", "json"], cwd=str(path))
    if result.returncode != 0 and result.stdout:
        try:
            vulns = json.loads(result.stdout)
            for vuln in vulns:
                issues.append(
                    {
                        "type": "vulnerability",
                        "severity": "high",
                        "package": vuln.get("name", "unknown"),
                        "version": vuln.get("version", "unknown"),
                        "vulnerability": vuln.get("vulns", [{}])[0].get("id", "unknown"),
                        "description": vuln.get("vulns", [{}])[0].get("description", ""),
                    }
                )
        except json.JSONDecodeError:
            pass

    return issues


def check_npm_audit(path: Path) -> list[dict]:
    """Run npm audit if package.json exists."""
    issues = []

    if not (path / "package.json").exists():
        return []

    result = run_cmd(["npm", "audit", "--json"], cwd=str(path))
    if result.stdout:
        try:
            data = json.loads(result.stdout)
            vulns = data.get("vulnerabilities", {})
            for name, info in vulns.items():
                issues.append(
                    {
                        "type": "vulnerability",
                        "severity": info.get("severity", "unknown"),
                        "package": name,
                        "description": info.get("via", [{}])[0].get("title", "")
                        if isinstance(info.get("via", [{}])[0], dict)
                        else str(info.get("via", "")),
                    }
                )
        except json.JSONDecodeError:
            pass

    return issues


def scan_file_for_secrets(file_path: Path) -> list[dict]:
    """Scan a file for hardcoded secrets."""
    issues = []

    try:
        content = file_path.read_text(errors="ignore")
    except Exception:
        return []

    for line_num, line in enumerate(content.split("\n"), 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue

        for pattern, description in SECRET_PATTERNS:
            if re.search(pattern, line):
                issues.append(
                    {
                        "type": "secret",
                        "severity": "critical",
                        "file": str(file_path),
                        "line": line_num,
                        "description": description,
                        "snippet": line.strip()[:80],
                    }
                )

    return issues


def scan_file_for_dangerous_patterns(file_path: Path) -> list[dict]:
    """Scan a file for dangerous code patterns."""
    issues = []

    try:
        content = file_path.read_text(errors="ignore")
    except Exception:
        return []

    for line_num, line in enumerate(content.split("\n"), 1):
        for pattern, description in DANGEROUS_PATTERNS:
            if re.search(pattern, line):
                issues.append(
                    {
                        "type": "dangerous_pattern",
                        "severity": "medium",
                        "file": str(file_path),
                        "line": line_num,
                        "description": description,
                        "snippet": line.strip()[:80],
                    }
                )

    return issues


def scan_directory(path: Path, skip_dirs: set = None) -> list[dict]:
    """Scan directory for secrets and dangerous patterns."""
    skip_dirs = skip_dirs or {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
    }
    extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".env", ".yaml", ".yml", ".json", ".toml"}

    issues = []

    for file_path in path.rglob("*"):
        if file_path.is_file():
            # Skip certain directories
            if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                continue

            # Only scan relevant files
            if file_path.suffix not in extensions and file_path.name not in {".env", ".env.local"}:
                continue

            issues.extend(scan_file_for_secrets(file_path))

            # Only scan code files for dangerous patterns
            if file_path.suffix in {".py", ".js", ".ts", ".jsx", ".tsx"}:
                issues.extend(scan_file_for_dangerous_patterns(file_path))

    return issues


def run_audit(path: Path, check_deps: bool = True, check_code: bool = True) -> dict:
    """Run full security audit."""
    results = {
        "path": str(path),
        "issues": [],
        "summary": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        },
    }

    if check_deps:
        results["issues"].extend(check_pip_audit(path))
        results["issues"].extend(check_npm_audit(path))

    if check_code:
        results["issues"].extend(scan_directory(path))

    # Update summary
    for issue in results["issues"]:
        severity = issue.get("severity", "info")
        if severity in results["summary"]:
            results["summary"][severity] += 1

    results["total_issues"] = len(results["issues"])

    return results


def format_results(results: dict, verbose: bool = False) -> str:
    """Format audit results for display."""
    lines = []
    path = Path(results["path"]).name

    lines.append(f"## Security Audit: {path}\n")

    summary = results["summary"]
    total = results["total_issues"]

    if total == 0:
        lines.append("No issues found.\n")
        return "\n".join(lines)

    lines.append(f"**Total issues:** {total}")
    lines.append(f"- Critical: {summary['critical']}")
    lines.append(f"- High: {summary['high']}")
    lines.append(f"- Medium: {summary['medium']}")
    lines.append(f"- Low: {summary['low']}")
    lines.append("")

    if verbose:
        # Group by type
        by_type = {}
        for issue in results["issues"]:
            t = issue.get("type", "other")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(issue)

        for issue_type, issues in by_type.items():
            lines.append(f"### {issue_type.replace('_', ' ').title()}\n")
            for issue in issues:
                if "file" in issue:
                    lines.append(
                        f"- **{issue['file']}:{issue.get('line', '?')}** - {issue['description']}"
                    )
                elif "package" in issue:
                    lines.append(
                        f"- **{issue['package']}** ({issue.get('severity', 'unknown')}): {issue.get('description', '')}"
                    )
                else:
                    lines.append(
                        f"- {issue.get('message', issue.get('description', 'Unknown issue'))}"
                    )
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Security audit for Python and JavaScript projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      Audit current directory
  %(prog)s --repo synapse-engine  Audit specific repo
  %(prog)s --all                Audit all configured repos
  %(prog)s --no-deps            Skip dependency checks
  %(prog)s --verbose            Show detailed findings
        """,
    )
    parser.add_argument("--repo", "-r", help="Repository name")
    parser.add_argument("--path", "-p", help="Path to repo (overrides --repo)")
    parser.add_argument("--all", "-a", action="store_true", help="Audit all repos")
    parser.add_argument("--no-deps", action="store_true", help="Skip dependency checks")
    parser.add_argument("--no-code", action="store_true", help="Skip code scanning")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    repo_base = get_repo_base()

    # Determine paths to audit
    paths = []
    if args.all:
        for repo in get_repos():
            p = repo_base / repo
            if p.exists():
                paths.append(p)
    elif args.path:
        paths.append(Path(args.path))
    elif args.repo:
        paths.append(repo_base / args.repo)
    else:
        paths.append(Path.cwd())

    all_results = []
    for path in paths:
        if not path.exists():
            print(f"Warning: Path does not exist: {path}", file=sys.stderr)
            continue

        results = run_audit(
            path,
            check_deps=not args.no_deps,
            check_code=not args.no_code,
        )
        all_results.append(results)

    if args.json:
        print(json.dumps(all_results if len(all_results) > 1 else all_results[0], indent=2))
    else:
        for results in all_results:
            print(format_results(results, verbose=args.verbose))


if __name__ == "__main__":
    main()
