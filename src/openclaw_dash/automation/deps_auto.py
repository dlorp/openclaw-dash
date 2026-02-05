"""Scheduled dependency updates using dep-shepherd."""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class DepsConfig:
    """Configuration for dependency automation."""

    repos: list[str] = field(default_factory=lambda: ["synapse-engine", "r3LAY", "t3rra1n"])
    repo_base: Path = field(default_factory=lambda: Path.home() / "repos")
    max_prs_per_run: int = 5
    security_only: bool = False
    dry_run: bool = False
    state_file: Path | None = None

    def __post_init__(self) -> None:
        if self.state_file is None:
            self.state_file = Path.home() / ".openclaw" / "deps_auto_state.json"


@dataclass
class UpdateResult:
    """Result of a dependency update attempt."""

    repo: str
    package: str
    from_version: str
    to_version: str
    dep_type: str
    is_security: bool
    status: str  # created, failed, skipped, dry-run
    message: str
    pr_url: str | None = None


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr).

    Uses stdin=DEVNULL to prevent hanging when subprocesses prompt for input.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


class DepsAutomation:
    """Automate dependency updates via dep-shepherd."""

    def __init__(self, config: DepsConfig | None = None):
        self.config = config or DepsConfig()
        self._ensure_state_dir()

    def _ensure_state_dir(self):
        """Ensure state directory exists."""
        if self.config.state_file:
            self.config.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict:
        """Load automation state."""
        if self.config.state_file and self.config.state_file.exists():
            try:
                return json.loads(self.config.state_file.read_text())
            except (OSError, json.JSONDecodeError):
                pass
        return {"last_run": None, "updates": []}

    def _save_state(self, state: dict):
        """Save automation state."""
        if self.config.state_file:
            self.config.state_file.write_text(json.dumps(state, indent=2, default=str))

    def should_run_weekly(self) -> tuple[bool, str]:
        """Check if enough time has passed since last run."""
        state = self._load_state()
        last_run = state.get("last_run")

        if not last_run:
            return True, "First run"

        try:
            last_dt = datetime.fromisoformat(last_run)
            days_since = (datetime.now() - last_dt).days

            if days_since >= 7:
                return True, f"Last run {days_since} days ago"
            else:
                return False, f"Last run {days_since} days ago, next run in {7 - days_since} days"
        except ValueError:
            return True, "Invalid last run date"

    def find_dep_shepherd(self) -> Path | None:
        """Find the dep-shepherd script."""
        # Check common locations
        candidates = [
            Path(__file__).parent.parent / "tools" / "dep-shepherd.py",
            Path.home()
            / "repos"
            / "openclaw-dash"
            / "src"
            / "openclaw_dash"
            / "tools"
            / "dep-shepherd.py",
        ]

        for path in candidates:
            if path.exists():
                return path

        return None

    def scan_repos(self) -> list[dict]:
        """Scan repos for dependency updates."""
        dep_shepherd = self.find_dep_shepherd()

        if not dep_shepherd:
            raise FileNotFoundError("dep-shepherd.py not found")

        results = []
        for repo in self.config.repos:
            code, stdout, stderr = run(
                [sys.executable, str(dep_shepherd), "--repo", repo, "--json"], timeout=300
            )

            if code == 0 and stdout:
                try:
                    repo_results = json.loads(stdout)
                    if isinstance(repo_results, list):
                        results.extend(repo_results)
                    else:
                        results.append(repo_results)
                except json.JSONDecodeError:
                    pass

        return results

    def create_update_pr(self, repo: str, dep: dict) -> UpdateResult:
        """Create a PR for a single dependency update."""
        repo_path = self.config.repo_base / repo
        package = dep.get("package", "unknown")
        current = dep.get("current_version", "unknown")
        latest = dep.get("latest_version", "unknown")
        dep_type = dep.get("dep_type", "pip")
        is_security = dep.get("is_security", False)

        branch_name = f"deps/update-{package}-{latest}".replace(".", "-").replace("@", "-")

        # Check if branch already exists
        code, existing, _ = run(["git", "branch", "--list", branch_name], cwd=repo_path)
        if existing.strip():
            return UpdateResult(
                repo=repo,
                package=package,
                from_version=current,
                to_version=latest,
                dep_type=dep_type,
                is_security=is_security,
                status="skipped",
                message=f"Branch {branch_name} already exists",
            )

        # Also check remote
        _, remote_branches, _ = run(
            ["git", "ls-remote", "--heads", "origin", branch_name], cwd=repo_path
        )
        if remote_branches.strip():
            return UpdateResult(
                repo=repo,
                package=package,
                from_version=current,
                to_version=latest,
                dep_type=dep_type,
                is_security=is_security,
                status="skipped",
                message=f"Remote branch {branch_name} already exists",
            )

        if self.config.dry_run:
            return UpdateResult(
                repo=repo,
                package=package,
                from_version=current,
                to_version=latest,
                dep_type=dep_type,
                is_security=is_security,
                status="dry-run",
                message="Would create PR",
            )

        # Create and checkout branch
        # Try main first, fall back to master
        code, _, _ = run(["git", "checkout", "main"], cwd=repo_path)
        if code != 0:
            run(["git", "checkout", "master"], cwd=repo_path)
        run(["git", "pull"], cwd=repo_path)
        code, _, stderr = run(["git", "checkout", "-b", branch_name], cwd=repo_path)

        if code != 0:
            return UpdateResult(
                repo=repo,
                package=package,
                from_version=current,
                to_version=latest,
                dep_type=dep_type,
                is_security=is_security,
                status="failed",
                message=f"Failed to create branch: {stderr}",
            )

        try:
            # Update the dependency
            if dep_type == "pip":
                updated = self._update_pip_dep(repo_path, package, latest)
            elif dep_type == "npm":
                updated = self._update_npm_dep(repo_path, package, latest)
            else:
                updated = False

            if not updated:
                raise Exception(f"Failed to update {package}")

            # Run tests
            tests_passed, test_output = self._run_tests(repo_path)
            if not tests_passed:
                raise Exception(f"Tests failed: {test_output}")

            # Commit and push
            security_tag = " " if is_security else ""
            commit_msg = f"{security_tag}Update {package} from {current} to {latest}"

            run(["git", "add", "-A"], cwd=repo_path)
            code, _, stderr = run(["git", "commit", "-m", commit_msg], cwd=repo_path)
            if code != 0:
                raise Exception(f"Commit failed: {stderr}")

            code, _, stderr = run(["git", "push", "-u", "origin", branch_name], cwd=repo_path)
            if code != 0:
                raise Exception(f"Push failed: {stderr}")

            # Create PR
            pr_body = self._generate_pr_body(package, current, latest, is_security, test_output)
            code, stdout, stderr = run(
                ["gh", "pr", "create", "--title", commit_msg, "--body", pr_body, "--base", "main"],
                cwd=repo_path,
            )

            if code != 0:
                raise Exception(f"PR creation failed: {stderr}")

            # Extract PR URL from output
            pr_url = stdout.strip() if stdout else None

            return UpdateResult(
                repo=repo,
                package=package,
                from_version=current,
                to_version=latest,
                dep_type=dep_type,
                is_security=is_security,
                status="created",
                message="PR created successfully",
                pr_url=pr_url,
            )

        except Exception as e:
            # Cleanup on failure
            run(["git", "checkout", "--", "."], cwd=repo_path)
            code, _, _ = run(["git", "checkout", "main"], cwd=repo_path)
            if code != 0:
                run(["git", "checkout", "master"], cwd=repo_path)
            run(["git", "branch", "-D", branch_name], cwd=repo_path)

            return UpdateResult(
                repo=repo,
                package=package,
                from_version=current,
                to_version=latest,
                dep_type=dep_type,
                is_security=is_security,
                status="failed",
                message=str(e),
            )

        finally:
            code, _, _ = run(["git", "checkout", "main"], cwd=repo_path)
            if code != 0:
                run(["git", "checkout", "master"], cwd=repo_path)

    def _update_pip_dep(self, repo_path: Path, package: str, version: str) -> bool:
        """Update a pip dependency in requirements.txt or pyproject.toml."""
        import re

        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text()
            patterns = [
                rf"^({re.escape(package)})==.*$",
                rf"^({re.escape(package)})>=.*$",
                rf"^({re.escape(package)})~=.*$",
                rf"^({re.escape(package)})\s*$",
            ]
            for pattern in patterns:
                new_content, count = re.subn(
                    pattern, rf"\1=={version}", content, flags=re.MULTILINE | re.IGNORECASE
                )
                if count > 0:
                    req_file.write_text(new_content)
                    return True

        # Try pyproject.toml
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            # Match dependency patterns in pyproject.toml
            patterns = [
                rf'"{re.escape(package)}[><=~!]*[^"]*"',
                rf"'{re.escape(package)}[><=~!]*[^']*'",
            ]
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    new_content = re.sub(
                        pattern, f'"{package}>={version}"', content, flags=re.IGNORECASE
                    )
                    pyproject.write_text(new_content)
                    return True

        return False

    def _update_npm_dep(self, repo_path: Path, package: str, version: str) -> bool:
        """Update an npm dependency."""
        code, _, stderr = run(
            ["npm", "install", f"{package}@{version}", "--save"], cwd=repo_path, timeout=180
        )
        return code == 0

    def _run_tests(self, repo_path: Path) -> tuple[bool, str]:
        """Run tests in a repo."""
        test_commands = [
            (["pytest", "-x", "-q"], "pytest"),
            (["python", "-m", "pytest", "-x", "-q"], "pytest"),
            (["npm", "test"], "npm test"),
            (["make", "test"], "make test"),
        ]

        for cmd, cmd_name in test_commands:
            if "pytest" in cmd_name and not list(repo_path.glob("**/test_*.py")):
                continue
            if "npm test" in cmd_name and not (repo_path / "package.json").exists():
                continue
            if "make test" in cmd_name and not (repo_path / "Makefile").exists():
                continue

            code, stdout, stderr = run(cmd, cwd=repo_path, timeout=300)
            if code == 0:
                return True, f"Tests passed: {cmd_name}"
            elif code != 127:
                return False, f"Tests failed ({cmd_name}): {stderr or stdout}"

        return True, "No test suite found"

    def _generate_pr_body(
        self, package: str, current: str, latest: str, is_security: bool, test_output: str
    ) -> str:
        """Generate PR body text."""
        body = f"""## Dependency Update

Updates **{package}** from `{current}` to `{latest}`

"""
        if is_security:
            body += " **Security update** - This package has known vulnerabilities in the current version.\n\n"

        body += f"""### Test Results
{test_output}

---
*Created automatically by openclaw-dash deps automation* 
"""
        return body.replace('"', '\\"')

    def run_updates(self, force: bool = False) -> list[UpdateResult]:
        """Run dependency updates."""
        # Check if we should run
        if not force:
            should_run, reason = self.should_run_weekly()
            if not should_run:
                return [
                    UpdateResult(
                        repo="",
                        package="",
                        from_version="",
                        to_version="",
                        dep_type="",
                        is_security=False,
                        status="skipped",
                        message=reason,
                    )
                ]

        # Scan for updates
        scan_results = self.scan_repos()

        results = []
        pr_count = 0

        for audit in scan_results:
            if not isinstance(audit, dict):
                continue

            repo_name = audit.get("name", "unknown")
            outdated = audit.get("outdated", [])

            # Sort: security first
            sorted_deps = sorted(
                outdated, key=lambda x: (not x.get("is_security", False), x.get("package", ""))
            )

            for dep in sorted_deps:
                # Check limits
                if pr_count >= self.config.max_prs_per_run:
                    results.append(
                        UpdateResult(
                            repo=repo_name,
                            package=dep.get("package", "unknown"),
                            from_version=dep.get("current_version", ""),
                            to_version=dep.get("latest_version", ""),
                            dep_type=dep.get("dep_type", ""),
                            is_security=dep.get("is_security", False),
                            status="skipped",
                            message="Max PRs per run reached",
                        )
                    )
                    continue

                # Skip non-security if security_only
                if self.config.security_only and not dep.get("is_security", False):
                    continue

                result = self.create_update_pr(repo_name, dep)
                results.append(result)

                if result.status == "created":
                    pr_count += 1

        # Save state
        state = self._load_state()
        state["last_run"] = datetime.now().isoformat()
        state["updates"].extend(
            [
                {
                    "repo": r.repo,
                    "package": r.package,
                    "version": r.to_version,
                    "status": r.status,
                    "timestamp": datetime.now().isoformat(),
                }
                for r in results
                if r.status in ("created", "failed")
            ]
        )

        # Keep only last 100 updates
        state["updates"] = state["updates"][-100:]
        self._save_state(state)

        return results


def format_deps_results(results: list[UpdateResult]) -> str:
    """Format dependency update results for display."""
    lines = ["##  Dependency Update Results", ""]

    created = [r for r in results if r.status == "created"]
    dry_run = [r for r in results if r.status == "dry-run"]
    failed = [r for r in results if r.status == "failed"]
    skipped = [r for r in results if r.status == "skipped"]

    if created:
        lines.append("### ✓ PRs Created")
        for r in created:
            security = " " if r.is_security else ""
            lines.append(f"- {security}**{r.repo}**: {r.package} {r.from_version} → {r.to_version}")
            if r.pr_url:
                lines.append(f"  - <{r.pr_url}>")
        lines.append("")

    if dry_run:
        lines.append("###  Would Create (dry-run)")
        for r in dry_run:
            security = " " if r.is_security else ""
            lines.append(f"- {security}**{r.repo}**: {r.package} {r.from_version} → {r.to_version}")
        lines.append("")

    if failed:
        lines.append("### ✗ Failed")
        for r in failed:
            lines.append(f"- **{r.repo}**: {r.package}")
            lines.append(f"  - {r.message}")
        lines.append("")

    if skipped and len(skipped) <= 10:
        lines.append("###  Skipped")
        for r in skipped:
            if r.repo:
                lines.append(f"- {r.repo}/{r.package}: {r.message}")
            else:
                lines.append(f"- {r.message}")
        lines.append("")
    elif skipped:
        lines.append(f"###  Skipped ({len(skipped)} items)")
        lines.append("")

    lines.append(
        f"**Summary:** {len(created)} created, {len(dry_run)} dry-run, {len(failed)} failed, {len(skipped)} skipped"
    )

    return "\n".join(lines)
