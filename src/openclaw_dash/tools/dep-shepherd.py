#!/usr/bin/env python3
"""
dep-shepherd.py — Dependency audit and update tool for dlorp's repos.

Features:
- Scan repos for outdated/vulnerable dependencies
- Support pip (requirements.txt, pyproject.toml) and npm (package.json)
- Security audits via pip-audit, safety (Python) and npm audit (JS)
- Create one PR per dependency update (clean rollbacks)
- Run tests before creating PR (skip if tests fail)
- Prioritize security updates over version bumps

Usage:
    python3 dep-shepherd.py                    # Scan all repos, human readable
    python3 dep-shepherd.py --json             # Output as JSON
    python3 dep-shepherd.py --report           # Detailed human readable report
    python3 dep-shepherd.py --update           # Create PRs for updates
    python3 dep-shepherd.py --digest           # Weekly digest summary
    python3 dep-shepherd.py --repo synapse-engine  # Scan specific repo
"""

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

# Import pr-describe for PR description generation
try:
    from pr_describe import generate_pr_description

    HAS_PR_DESCRIBE = True
except ImportError:
    HAS_PR_DESCRIBE = False

REPOS = ["synapse-engine", "r3LAY", "t3rra1n"]
REPO_BASE = Path.home() / "repos"
STATE_FILE = Path(__file__).parent / ".dep_state.json"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class Vulnerability:
    package: str
    installed_version: str
    fixed_version: str | None
    severity: str
    description: str
    source: str  # pip-audit, safety, npm


@dataclass
class OutdatedDep:
    package: str
    current_version: str
    latest_version: str
    dep_type: str  # pip, npm
    is_security: bool = False


@dataclass
class RepoAudit:
    name: str
    path: str
    vulnerabilities: list
    outdated: list
    dep_files: list
    scanned_at: str
    errors: list


def run(cmd: str, cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def tool_available(tool: str) -> bool:
    """Check if a command-line tool is available."""
    code, _, _ = run(f"which {tool}")
    return code == 0


def find_dep_files(repo_path: Path) -> dict:
    """Find dependency files in a repo."""
    files = {
        "pip": [],
        "npm": [],
    }

    # Python files
    for pattern in ["requirements.txt", "requirements*.txt", "pyproject.toml"]:
        found = list(repo_path.glob(pattern))
        found += list(repo_path.glob(f"**/{pattern}"))
        for f in found:
            if "node_modules" not in str(f) and ".venv" not in str(f):
                if str(f) not in [str(x) for x in files["pip"]]:
                    files["pip"].append(f)

    # NPM files
    for f in repo_path.glob("**/package.json"):
        if "node_modules" not in str(f):
            files["npm"].append(f)

    return files


# --- Python Dependency Auditing ---


def run_pip_audit(repo_path: Path, requirements_file: Path) -> list[Vulnerability]:
    """Run pip-audit on a requirements file."""
    if not tool_available("pip-audit"):
        return []

    vulnerabilities = []
    code, stdout, stderr = run(
        f"pip-audit -r {requirements_file} --format json 2>/dev/null", cwd=repo_path, timeout=180
    )

    if code == 0 or stdout:
        try:
            results = json.loads(stdout) if stdout else []
            for vuln in results:
                vulnerabilities.append(
                    Vulnerability(
                        package=vuln.get("name", "unknown"),
                        installed_version=vuln.get("version", "unknown"),
                        fixed_version=vuln.get("fix_versions", [None])[0]
                        if vuln.get("fix_versions")
                        else None,
                        severity=vuln.get("vulns", [{}])[0].get("severity", "unknown")
                        if vuln.get("vulns")
                        else "unknown",
                        description=vuln.get("vulns", [{}])[0].get("id", "Unknown vulnerability")
                        if vuln.get("vulns")
                        else "Unknown",
                        source="pip-audit",
                    )
                )
        except json.JSONDecodeError:
            pass

    return vulnerabilities


def run_safety_check(repo_path: Path, requirements_file: Path) -> list[Vulnerability]:
    """Run safety check on a requirements file."""
    if not tool_available("safety"):
        return []

    vulnerabilities = []
    code, stdout, stderr = run(
        f"safety check -r {requirements_file} --json 2>/dev/null", cwd=repo_path, timeout=180
    )

    if stdout:
        try:
            # Safety outputs results differently
            results = json.loads(stdout)
            vulns = results.get("vulnerabilities", []) if isinstance(results, dict) else results
            for vuln in vulns:
                if isinstance(vuln, dict):
                    vulnerabilities.append(
                        Vulnerability(
                            package=vuln.get("package_name", "unknown"),
                            installed_version=vuln.get("analyzed_version", "unknown"),
                            fixed_version=vuln.get("fixed_versions", [None])[0]
                            if vuln.get("fixed_versions")
                            else None,
                            severity=vuln.get("severity", {}).get("level", "unknown")
                            if isinstance(vuln.get("severity"), dict)
                            else "unknown",
                            description=vuln.get("vulnerability_id", "Unknown vulnerability"),
                            source="safety",
                        )
                    )
                elif isinstance(vuln, list) and len(vuln) >= 5:
                    # Old safety format: [pkg, version, installed, desc, id]
                    vulnerabilities.append(
                        Vulnerability(
                            package=vuln[0],
                            installed_version=vuln[2],
                            fixed_version=None,
                            severity="unknown",
                            description=vuln[4],
                            source="safety",
                        )
                    )
        except json.JSONDecodeError:
            pass

    return vulnerabilities


def get_pip_outdated(repo_path: Path) -> list[OutdatedDep]:
    """Get outdated pip packages."""
    outdated = []

    # Try pip list --outdated
    code, stdout, stderr = run("pip list --outdated --format json 2>/dev/null", cwd=repo_path)

    if code == 0 and stdout:
        try:
            for pkg in json.loads(stdout):
                outdated.append(
                    OutdatedDep(
                        package=pkg["name"],
                        current_version=pkg["version"],
                        latest_version=pkg["latest_version"],
                        dep_type="pip",
                    )
                )
        except json.JSONDecodeError:
            pass

    return outdated


# --- NPM Dependency Auditing ---


def run_npm_audit(package_dir: Path) -> list[Vulnerability]:
    """Run npm audit on a package.json directory."""
    vulnerabilities = []

    # Check if package-lock.json exists (required for npm audit)
    if not (package_dir / "package-lock.json").exists():
        return vulnerabilities

    code, stdout, stderr = run("npm audit --json 2>/dev/null", cwd=package_dir, timeout=180)

    if stdout:
        try:
            results = json.loads(stdout)
            vulns = results.get("vulnerabilities", {})
            for pkg_name, vuln_data in vulns.items():
                severity = vuln_data.get("severity", "unknown")
                vulnerabilities.append(
                    Vulnerability(
                        package=pkg_name,
                        installed_version=vuln_data.get("range", "unknown"),
                        fixed_version=vuln_data.get("fixAvailable", {}).get("version")
                        if isinstance(vuln_data.get("fixAvailable"), dict)
                        else None,
                        severity=severity,
                        description=f"{vuln_data.get('via', ['Unknown'])[0] if isinstance(vuln_data.get('via', ['Unknown'])[0], str) else vuln_data.get('via', [{}])[0].get('title', 'Unknown')}",
                        source="npm",
                    )
                )
        except json.JSONDecodeError:
            pass

    return vulnerabilities


def get_npm_outdated(package_dir: Path) -> list[OutdatedDep]:
    """Get outdated npm packages."""
    outdated = []

    code, stdout, stderr = run("npm outdated --json 2>/dev/null", cwd=package_dir)

    # npm outdated returns exit code 1 if there are outdated packages
    if stdout:
        try:
            for pkg, info in json.loads(stdout).items():
                outdated.append(
                    OutdatedDep(
                        package=pkg,
                        current_version=info.get("current", "unknown"),
                        latest_version=info.get("latest", "unknown"),
                        dep_type="npm",
                    )
                )
        except json.JSONDecodeError:
            pass

    return outdated


# --- Repo Scanning ---


def scan_repo(repo: str) -> RepoAudit:
    """Scan a single repo for dependency issues."""
    repo_path = REPO_BASE / repo
    errors = []

    if not repo_path.exists():
        return RepoAudit(
            name=repo,
            path=str(repo_path),
            vulnerabilities=[],
            outdated=[],
            dep_files=[],
            scanned_at=datetime.now().isoformat(),
            errors=[f"Repo not found: {repo_path}"],
        )

    # Find dependency files
    dep_files = find_dep_files(repo_path)
    all_dep_files = []

    vulnerabilities = []
    outdated = []

    # Scan Python dependencies
    for req_file in dep_files["pip"]:
        all_dep_files.append(str(req_file.relative_to(repo_path)))

        # Run pip-audit
        try:
            vulnerabilities.extend(run_pip_audit(repo_path, req_file))
        except Exception as e:
            errors.append(f"pip-audit failed on {req_file.name}: {e}")

        # Run safety
        try:
            vulnerabilities.extend(run_safety_check(repo_path, req_file))
        except Exception as e:
            errors.append(f"safety check failed on {req_file.name}: {e}")

    # Get pip outdated (once per repo)
    if dep_files["pip"]:
        try:
            outdated.extend(get_pip_outdated(repo_path))
        except Exception as e:
            errors.append(f"pip outdated check failed: {e}")

    # Scan NPM dependencies
    for pkg_json in dep_files["npm"]:
        pkg_dir = pkg_json.parent
        all_dep_files.append(str(pkg_json.relative_to(repo_path)))

        # Run npm audit
        try:
            vulnerabilities.extend(run_npm_audit(pkg_dir))
        except Exception as e:
            errors.append(f"npm audit failed in {pkg_dir}: {e}")

        # Get npm outdated
        try:
            outdated.extend(get_npm_outdated(pkg_dir))
        except Exception as e:
            errors.append(f"npm outdated check failed in {pkg_dir}: {e}")

    # Deduplicate vulnerabilities (pip-audit and safety may overlap)
    seen_vulns = set()
    unique_vulns = []
    for v in vulnerabilities:
        key = (v.package, v.installed_version, v.description)
        if key not in seen_vulns:
            seen_vulns.add(key)
            unique_vulns.append(v)

    # Mark security-related outdated deps
    vuln_packages = {v.package.lower() for v in unique_vulns}
    for dep in outdated:
        if dep.package.lower() in vuln_packages:
            dep.is_security = True

    return RepoAudit(
        name=repo,
        path=str(repo_path),
        vulnerabilities=[asdict(v) for v in unique_vulns],
        outdated=[asdict(d) for d in outdated],
        dep_files=all_dep_files,
        scanned_at=datetime.now().isoformat(),
        errors=errors,
    )


# --- PR Creation ---


def run_tests(repo_path: Path) -> tuple[bool, str]:
    """Run tests in a repo. Returns (passed, output)."""
    # Try common test commands
    test_commands = [
        "pytest -x -q",
        "python -m pytest -x -q",
        "npm test",
        "make test",
    ]

    for cmd in test_commands:
        # Check if test framework exists
        if (
            "pytest" in cmd
            and not (repo_path / "pytest.ini").exists()
            and not list(repo_path.glob("test_*.py"))
            and not list(repo_path.glob("**/test_*.py"))
        ):
            continue
        if "npm test" in cmd and not (repo_path / "package.json").exists():
            continue
        if "make test" in cmd and not (repo_path / "Makefile").exists():
            continue

        code, stdout, stderr = run(cmd, cwd=repo_path, timeout=300)
        if code == 0:
            return True, f"Tests passed: {cmd}"
        elif code != 127:  # 127 = command not found
            return False, f"Tests failed ({cmd}): {stderr or stdout}"

    # No tests found - consider it a pass
    return True, "No test suite found"


def create_update_pr(repo: str, dep: OutdatedDep) -> tuple[bool, str]:
    """Create a PR for a single dependency update."""
    repo_path = REPO_BASE / repo
    branch_name = f"deps/update-{dep.package}-{dep.latest_version}".replace(".", "-")

    # Check if branch already exists
    code, _, _ = run(f"git branch --list {branch_name}", cwd=repo_path)
    _, existing, _ = run(f"git branch --list {branch_name}", cwd=repo_path)
    if existing.strip():
        return False, f"Branch {branch_name} already exists"

    # Create branch
    code, _, stderr = run(f"git checkout -b {branch_name}", cwd=repo_path)
    if code != 0:
        return False, f"Failed to create branch: {stderr}"

    try:
        # Update the dependency
        if dep.dep_type == "pip":
            # Update requirements.txt
            req_file = repo_path / "requirements.txt"
            if req_file.exists():
                content = req_file.read_text()
                # Try various patterns
                import re

                patterns = [
                    rf"^{re.escape(dep.package)}==.*$",
                    rf"^{re.escape(dep.package)}>=.*$",
                    rf"^{re.escape(dep.package)}~=.*$",
                    rf"^{re.escape(dep.package)}\s*$",
                ]
                updated = False
                for pattern in patterns:
                    new_content, count = re.subn(
                        pattern,
                        f"{dep.package}=={dep.latest_version}",
                        content,
                        flags=re.MULTILINE | re.IGNORECASE,
                    )
                    if count > 0:
                        req_file.write_text(new_content)
                        updated = True
                        break
                if not updated:
                    raise Exception(f"Could not find {dep.package} in requirements.txt")

        elif dep.dep_type == "npm":
            code, _, stderr = run(
                f"npm install {dep.package}@{dep.latest_version} --save", cwd=repo_path, timeout=180
            )
            if code != 0:
                raise Exception(f"npm install failed: {stderr}")

        # Run tests
        tests_passed, test_output = run_tests(repo_path)
        if not tests_passed:
            # Revert and return
            run("git checkout -- .", cwd=repo_path)
            run("git checkout main", cwd=repo_path)
            run(f"git branch -D {branch_name}", cwd=repo_path)
            return False, f"Tests failed, skipping PR: {test_output}"

        # Commit
        security_tag = "🔒 " if dep.is_security else ""
        commit_msg = (
            f"{security_tag}Update {dep.package} from {dep.current_version} to {dep.latest_version}"
        )

        run("git add -A", cwd=repo_path)
        code, _, stderr = run(f'git commit -m "{commit_msg}"', cwd=repo_path)
        if code != 0:
            raise Exception(f"Commit failed: {stderr}")

        # Push
        code, _, stderr = run(f"git push -u origin {branch_name}", cwd=repo_path)
        if code != 0:
            raise Exception(f"Push failed: {stderr}")

        # Create PR description
        if HAS_PR_DESCRIBE:
            try:
                pr_body = generate_pr_description(repo_path, "main", branch_name)
                # Append dep-specific context
                extra_notes = []
                if dep.is_security:
                    extra_notes.append(
                        "⚠️ **Security update** - This package has known vulnerabilities in the current version."
                    )
                extra_notes.append(f"### Test Results\n{test_output}")
                extra_notes.append("---\n*Created by dep-shepherd.py* 🐑")
                pr_body += "\n\n" + "\n\n".join(extra_notes)
            except Exception:
                # Fall back to simple body
                pr_body = f"""## Dependency Update

Updates **{dep.package}** from `{dep.current_version}` to `{dep.latest_version}`

{"⚠️ **Security update** - This package has known vulnerabilities in the current version." if dep.is_security else ""}

### Test Results
{test_output}

---
*Created by dep-shepherd.py* 🐑
"""
        else:
            pr_body = f"""## Dependency Update

Updates **{dep.package}** from `{dep.current_version}` to `{dep.latest_version}`

{"⚠️ **Security update** - This package has known vulnerabilities in the current version." if dep.is_security else ""}

### Test Results
{test_output}

---
*Created by dep-shepherd.py* 🐑
"""

        code, stdout, stderr = run(
            f'gh pr create --title "{commit_msg}" --body "{pr_body}" --base main', cwd=repo_path
        )
        if code != 0:
            raise Exception(f"PR creation failed: {stderr}")

        return True, f"Created PR: {stdout}"

    except Exception as e:
        # Cleanup on failure
        run("git checkout -- .", cwd=repo_path)
        run("git checkout main", cwd=repo_path)
        run(f"git branch -D {branch_name}", cwd=repo_path)
        return False, str(e)

    finally:
        # Always return to main
        run("git checkout main", cwd=repo_path)


def create_update_prs(results: list[RepoAudit], dry_run: bool = False) -> list[dict]:
    """Create PRs for all updates, prioritizing security."""
    pr_results = []

    for audit in results:
        if audit.errors:
            continue

        # Sort: security first, then by severity
        all_deps = sorted(
            audit.outdated, key=lambda x: (not x.get("is_security", False), x.get("package", ""))
        )

        for dep_dict in all_deps:
            dep = OutdatedDep(**dep_dict) if isinstance(dep_dict, dict) else dep_dict

            if dry_run:
                pr_results.append(
                    {
                        "repo": audit.name,
                        "package": dep.package,
                        "from": dep.current_version,
                        "to": dep.latest_version,
                        "is_security": dep.is_security,
                        "status": "dry-run",
                    }
                )
            else:
                success, message = create_update_pr(audit.name, dep)
                pr_results.append(
                    {
                        "repo": audit.name,
                        "package": dep.package,
                        "from": dep.current_version,
                        "to": dep.latest_version,
                        "is_security": dep.is_security,
                        "status": "created" if success else "failed",
                        "message": message,
                    }
                )

    return pr_results


# --- Output Formatting ---


def severity_emoji(severity: str) -> str:
    """Get emoji for severity level."""
    return {
        "critical": "🔴",
        "high": "🟠",
        "moderate": "🟡",
        "low": "🟢",
        "unknown": "⚪",
    }.get(severity.lower(), "⚪")


def format_report(results: list[RepoAudit]) -> str:
    """Format results as a detailed human-readable report."""
    lines = ["## 🐑 Dependency Shepherd Report", ""]
    lines.append(f"**Scanned:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    total_vulns = 0
    total_outdated = 0

    for audit in results:
        if audit.errors and not audit.vulnerabilities and not audit.outdated:
            lines.append(f"### ❌ {audit.name}")
            for err in audit.errors:
                lines.append(f"- Error: {err}")
            lines.append("")
            continue

        vuln_count = len(audit.vulnerabilities)
        outdated_count = len(audit.outdated)
        total_vulns += vuln_count
        total_outdated += outdated_count

        # Status emoji
        if vuln_count > 0:
            status = "🚨"
        elif outdated_count > 10:
            status = "🟡"
        elif outdated_count > 0:
            status = "🟢"
        else:
            status = "✨"

        lines.append(f"### {status} {audit.name}")
        lines.append(f"**Dep files:** {', '.join(audit.dep_files) or 'None found'}")
        lines.append("")

        # Vulnerabilities
        if audit.vulnerabilities:
            lines.append("#### 🔒 Security Vulnerabilities")
            for v in sorted(
                audit.vulnerabilities,
                key=lambda x: ["critical", "high", "moderate", "low", "unknown"].index(
                    x.get("severity", "unknown").lower()
                )
                if x.get("severity", "unknown").lower()
                in ["critical", "high", "moderate", "low", "unknown"]
                else 4,
            ):
                sev = v.get("severity", "unknown")
                emoji = severity_emoji(sev)
                fix = (
                    f" → {v.get('fixed_version')}"
                    if v.get("fixed_version")
                    else " (no fix available)"
                )
                lines.append(f"- {emoji} **{v.get('package')}** {v.get('installed_version')}{fix}")
                lines.append(f"  - {v.get('description')} ({v.get('source')})")
            lines.append("")

        # Outdated (show top 10)
        if audit.outdated:
            security_outdated = [d for d in audit.outdated if d.get("is_security")]
            regular_outdated = [d for d in audit.outdated if not d.get("is_security")]

            if security_outdated:
                lines.append("#### ⚠️ Security-Related Updates")
                for d in security_outdated[:10]:
                    lines.append(
                        f"- **{d.get('package')}**: {d.get('current_version')} → {d.get('latest_version')} ({d.get('dep_type')})"
                    )
                lines.append("")

            if regular_outdated:
                lines.append(f"#### 📦 Outdated Packages ({len(regular_outdated)} total)")
                for d in regular_outdated[:10]:
                    lines.append(
                        f"- {d.get('package')}: {d.get('current_version')} → {d.get('latest_version')} ({d.get('dep_type')})"
                    )
                if len(regular_outdated) > 10:
                    lines.append(f"- ... and {len(regular_outdated) - 10} more")
                lines.append("")

        # Errors
        if audit.errors:
            lines.append("#### ⚠️ Scan Errors")
            for err in audit.errors:
                lines.append(f"- {err}")
            lines.append("")

    lines.append("---")
    lines.append(f"**Summary:** {total_vulns} vulnerabilities | {total_outdated} outdated packages")

    return "\n".join(lines)


def format_digest(results: list[RepoAudit]) -> str:
    """Format a weekly digest summary."""
    lines = ["## 📊 Weekly Dependency Digest", ""]
    lines.append(f"**Week of:** {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    # Aggregate stats
    total_vulns = sum(len(a.vulnerabilities) for a in results)
    total_outdated = sum(len(a.outdated) for a in results)
    repos_scanned = len([a for a in results if not a.errors or a.vulnerabilities or a.outdated])

    # Critical/high vulns
    critical_high = []
    for audit in results:
        for v in audit.vulnerabilities:
            if v.get("severity", "").lower() in ["critical", "high"]:
                critical_high.append((audit.name, v))

    # Summary table (as list for Discord compatibility)
    lines.append("### Summary")
    lines.append(f"- **Repos scanned:** {repos_scanned}")
    lines.append(f"- **Total vulnerabilities:** {total_vulns}")
    lines.append(f"- **Critical/High:** {len(critical_high)}")
    lines.append(f"- **Outdated packages:** {total_outdated}")
    lines.append("")

    # Health score
    if total_vulns == 0 and total_outdated < 10:
        health = "🟢 Excellent"
    elif len(critical_high) == 0 and total_vulns < 5:
        health = "🟡 Good"
    elif len(critical_high) < 3:
        health = "🟠 Needs Attention"
    else:
        health = "🔴 Critical"

    lines.append(f"### Overall Health: {health}")
    lines.append("")

    # Action items
    if critical_high:
        lines.append("### 🚨 Immediate Action Required")
        for repo, v in critical_high:
            lines.append(f"- **{repo}**: {v.get('package')} ({v.get('severity')})")
        lines.append("")

    # Per-repo summary
    lines.append("### Per-Repo Status")
    for audit in results:
        vuln_count = len(audit.vulnerabilities)
        outdated_count = len(audit.outdated)

        if audit.errors and vuln_count == 0 and outdated_count == 0:
            emoji = "❓"
        elif vuln_count > 0:
            emoji = "🚨"
        elif outdated_count > 10:
            emoji = "🟡"
        else:
            emoji = "✅"

        lines.append(f"- {emoji} **{audit.name}**: {vuln_count} vulns, {outdated_count} outdated")

    lines.append("")
    lines.append("---")
    lines.append("*Run `dep-shepherd.py --report` for details or `--update` to create PRs*")

    return "\n".join(lines)


def save_state(results: list[RepoAudit]):
    """Save scan results for trending."""
    state = {
        "scanned_at": datetime.now().isoformat(),
        "results": [
            asdict(r)
            if hasattr(r, "__dataclass_fields__")
            else r.__dict__
            if hasattr(r, "__dict__")
            else r
            for r in results
        ],
    }
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def main():
    # Parse arguments
    output_json = "--json" in sys.argv
    output_digest = "--digest" in sys.argv
    do_update = "--update" in sys.argv
    dry_run = "--dry-run" in sys.argv

    # Specific repo filter
    target_repos = REPOS
    if "--repo" in sys.argv:
        idx = sys.argv.index("--repo")
        if idx + 1 < len(sys.argv):
            target_repos = [sys.argv[idx + 1]]

    # Check for required tools
    missing_tools = []
    for tool in ["pip-audit", "safety", "npm", "gh"]:
        if not tool_available(tool):
            missing_tools.append(tool)

    if missing_tools and not output_json:
        print(
            f"⚠️  Missing tools (some checks will be skipped): {', '.join(missing_tools)}",
            file=sys.stderr,
        )

    # Scan repos
    results = []
    for repo in target_repos:
        print(f"Scanning {repo}...", file=sys.stderr)
        audit = scan_repo(repo)
        results.append(audit)

    # Save state
    save_state(results)

    # Handle update mode
    if do_update:
        print("Creating update PRs...", file=sys.stderr)
        pr_results = create_update_prs(results, dry_run=dry_run)

        if output_json:
            print(json.dumps(pr_results, indent=2))
        else:
            print("\n## 🔄 Update Results\n")
            for pr in pr_results:
                status_emoji = (
                    "✅"
                    if pr["status"] == "created"
                    else "⏭️"
                    if pr["status"] == "dry-run"
                    else "❌"
                )
                security_tag = "🔒 " if pr.get("is_security") else ""
                print(
                    f"{status_emoji} {security_tag}**{pr['repo']}** {pr['package']}: {pr['from']} → {pr['to']}"
                )
                if pr.get("message"):
                    print(f"   {pr['message']}")
        return

    # Output results
    if output_json:
        output = [asdict(r) if hasattr(r, "__dataclass_fields__") else r.__dict__ for r in results]
        print(json.dumps(output, indent=2, default=str))
    elif output_digest:
        print(format_digest(results))
    else:
        print(format_report(results))


if __name__ == "__main__":
    main()
