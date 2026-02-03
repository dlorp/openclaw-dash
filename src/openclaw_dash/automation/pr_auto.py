"""PR automation: auto-merge and stale branch cleanup."""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class MergeConfig:
    """Configuration for auto-merge behavior."""

    safelist: list[str] = field(default_factory=lambda: ["deps/", "dependabot/", "renovate/"])
    require_ci_pass: bool = True
    require_approval: bool = True
    min_approvals: int = 1
    delete_branch_after_merge: bool = True
    dry_run: bool = False


@dataclass
class CleanupConfig:
    """Configuration for stale branch cleanup."""

    max_age_days: int = 30
    protect_patterns: list[str] = field(
        default_factory=lambda: ["main", "master", "develop", "release/*"]
    )
    only_merged: bool = True
    dry_run: bool = False


@dataclass
class PRInfo:
    """Information about a pull request."""

    number: int
    title: str
    branch: str
    state: str
    mergeable: bool
    ci_status: str  # success, failure, pending
    approvals: int
    labels: list[str]
    author: str
    created_at: str
    url: str


@dataclass
class BranchInfo:
    """Information about a branch."""

    name: str
    last_commit_date: datetime
    is_merged: bool
    author: str


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[int, str, str]:
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


class PRAutomation:
    """Automate PR management: auto-merge and branch cleanup."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.repo_name = repo_path.name

    def get_open_prs(self) -> list[PRInfo]:
        """Get all open PRs for the repository."""
        code, stdout, stderr = run(
            ["gh", "pr", "list", "--json", "number,title,headRefName,state,mergeable,statusCheckRollup,reviews,labels,author,createdAt,url"],
            cwd=self.repo_path,
        )

        if code != 0:
            raise RuntimeError(f"Failed to list PRs: {stderr}")

        prs = []
        for pr_data in json.loads(stdout or "[]"):
            # Determine CI status
            checks = pr_data.get("statusCheckRollup", []) or []
            if not checks:
                ci_status = "pending"
            elif all(
                c.get("conclusion") == "SUCCESS" or c.get("state") == "SUCCESS" for c in checks
            ):
                ci_status = "success"
            elif any(
                c.get("conclusion") == "FAILURE" or c.get("state") == "FAILURE" for c in checks
            ):
                ci_status = "failure"
            else:
                ci_status = "pending"

            # Count approvals
            reviews = pr_data.get("reviews", []) or []
            approvals = sum(1 for r in reviews if r.get("state") == "APPROVED")

            prs.append(
                PRInfo(
                    number=pr_data["number"],
                    title=pr_data["title"],
                    branch=pr_data["headRefName"],
                    state=pr_data["state"],
                    mergeable=pr_data.get("mergeable", "UNKNOWN") == "MERGEABLE",
                    ci_status=ci_status,
                    approvals=approvals,
                    labels=[lbl.get("name", "") for lbl in (pr_data.get("labels") or [])],
                    author=pr_data.get("author", {}).get("login", "unknown"),
                    created_at=pr_data.get("createdAt", ""),
                    url=pr_data.get("url", ""),
                )
            )

        return prs

    def is_safe_to_merge(self, pr: PRInfo, config: MergeConfig) -> tuple[bool, str]:
        """Check if a PR is safe to auto-merge based on config."""
        # Check if branch matches safelist
        branch_safe = any(pr.branch.startswith(pattern.rstrip("*")) for pattern in config.safelist)
        if not branch_safe:
            return False, f"Branch '{pr.branch}' not in safelist"

        # Check CI status
        if config.require_ci_pass and pr.ci_status != "success":
            return False, f"CI status is '{pr.ci_status}', requires 'success'"

        # Check approvals
        if config.require_approval and pr.approvals < config.min_approvals:
            return False, f"Has {pr.approvals} approvals, requires {config.min_approvals}"

        # Check mergeable status
        if not pr.mergeable:
            return False, "PR is not mergeable (conflicts or other issues)"

        return True, "Ready to merge"

    def auto_merge(self, config: MergeConfig) -> list[dict]:
        """Auto-merge eligible PRs."""
        results = []
        prs = self.get_open_prs()

        for pr in prs:
            safe, reason = self.is_safe_to_merge(pr, config)

            if safe:
                if config.dry_run:
                    results.append(
                        {
                            "pr": pr.number,
                            "title": pr.title,
                            "branch": pr.branch,
                            "status": "would-merge",
                            "reason": reason,
                        }
                    )
                else:
                    # Merge the PR
                    merge_cmd = ["gh", "pr", "merge", str(pr.number), "--merge"]
                    if config.delete_branch_after_merge:
                        merge_cmd.append("--delete-branch")

                    code, stdout, stderr = run(merge_cmd, cwd=self.repo_path)

                    if code == 0:
                        results.append(
                            {
                                "pr": pr.number,
                                "title": pr.title,
                                "branch": pr.branch,
                                "status": "merged",
                                "reason": reason,
                            }
                        )
                    else:
                        results.append(
                            {
                                "pr": pr.number,
                                "title": pr.title,
                                "branch": pr.branch,
                                "status": "failed",
                                "reason": stderr or stdout,
                            }
                        )
            else:
                results.append(
                    {
                        "pr": pr.number,
                        "title": pr.title,
                        "branch": pr.branch,
                        "status": "skipped",
                        "reason": reason,
                    }
                )

        return results

    def get_remote_branches(self) -> list[BranchInfo]:
        """Get all remote branches with their info."""
        # Fetch latest
        run(["git", "fetch", "--prune"], cwd=self.repo_path)

        # Get branches with last commit date
        code, stdout, stderr = run(
            ["git", "for-each-ref", "--sort=-committerdate", "refs/remotes/origin",
             "--format=%(refname:short)|%(committerdate:iso)|%(authorname)"],
            cwd=self.repo_path,
        )

        if code != 0:
            raise RuntimeError(f"Failed to list branches: {stderr}")

        # Get list of merged branches (try main first, fall back to master)
        _, merged_stdout, _ = run(
            ["git", "branch", "-r", "--merged", "origin/main"],
            cwd=self.repo_path,
        )
        if not merged_stdout:
            _, merged_stdout, _ = run(
                ["git", "branch", "-r", "--merged", "origin/master"],
                cwd=self.repo_path,
            )
        merged_branches = {b.strip() for b in merged_stdout.split("\n") if b.strip()}

        branches = []
        for line in stdout.split("\n"):
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) < 3:
                continue

            name = parts[0].replace("origin/", "")
            if name in ("HEAD", "main", "master"):
                continue

            try:
                commit_date = datetime.fromisoformat(
                    parts[1].strip().replace(" ", "T").split("+")[0]
                )
            except ValueError:
                commit_date = datetime.now()

            is_merged = f"origin/{name}" in merged_branches

            branches.append(
                BranchInfo(
                    name=name,
                    last_commit_date=commit_date,
                    is_merged=is_merged,
                    author=parts[2].strip(),
                )
            )

        return branches

    def is_branch_protected(self, branch_name: str, protect_patterns: list[str]) -> bool:
        """Check if a branch matches any protection pattern."""
        import fnmatch

        for pattern in protect_patterns:
            if fnmatch.fnmatch(branch_name, pattern):
                return True
        return False

    def cleanup_branches(self, config: CleanupConfig) -> list[dict]:
        """Clean up stale branches."""
        results = []
        branches = self.get_remote_branches()
        cutoff_date = datetime.now() - timedelta(days=config.max_age_days)

        for branch in branches:
            # Skip protected branches
            if self.is_branch_protected(branch.name, config.protect_patterns):
                results.append(
                    {
                        "branch": branch.name,
                        "status": "protected",
                        "reason": "Matches protection pattern",
                    }
                )
                continue

            # Skip if not merged (when only_merged is True)
            if config.only_merged and not branch.is_merged:
                results.append(
                    {
                        "branch": branch.name,
                        "status": "skipped",
                        "reason": "Not merged into main",
                    }
                )
                continue

            # Skip if not stale
            if branch.last_commit_date > cutoff_date:
                results.append(
                    {
                        "branch": branch.name,
                        "status": "fresh",
                        "reason": f"Last commit {branch.last_commit_date.date()}, cutoff {cutoff_date.date()}",
                    }
                )
                continue

            # Delete the branch
            if config.dry_run:
                results.append(
                    {
                        "branch": branch.name,
                        "status": "would-delete",
                        "reason": f"Merged, stale since {branch.last_commit_date.date()}",
                        "author": branch.author,
                    }
                )
            else:
                code, stdout, stderr = run(
                    ["git", "push", "origin", "--delete", branch.name], cwd=self.repo_path
                )

                if code == 0:
                    results.append(
                        {
                            "branch": branch.name,
                            "status": "deleted",
                            "reason": f"Merged, stale since {branch.last_commit_date.date()}",
                            "author": branch.author,
                        }
                    )
                else:
                    results.append(
                        {
                            "branch": branch.name,
                            "status": "failed",
                            "reason": stderr or stdout,
                            "author": branch.author,
                        }
                    )

        return results


def format_merge_results(results: list[dict], repo_name: str) -> str:
    """Format merge results for display."""
    lines = [f"## 🔀 Auto-Merge Results: {repo_name}", ""]

    merged = [r for r in results if r["status"] == "merged"]
    would_merge = [r for r in results if r["status"] == "would-merge"]
    skipped = [r for r in results if r["status"] == "skipped"]
    failed = [r for r in results if r["status"] == "failed"]

    if merged:
        lines.append("### ✅ Merged")
        for r in merged:
            lines.append(f"- PR #{r['pr']}: {r['title']}")
        lines.append("")

    if would_merge:
        lines.append("### 🔄 Would Merge (dry-run)")
        for r in would_merge:
            lines.append(f"- PR #{r['pr']}: {r['title']}")
        lines.append("")

    if failed:
        lines.append("### ❌ Failed")
        for r in failed:
            lines.append(f"- PR #{r['pr']}: {r['title']}")
            lines.append(f"  - {r['reason']}")
        lines.append("")

    if skipped:
        lines.append("### ⏭️ Skipped")
        for r in skipped:
            lines.append(f"- PR #{r['pr']}: {r['reason']}")
        lines.append("")

    lines.append(
        f"**Summary:** {len(merged)} merged, {len(would_merge)} would-merge, {len(skipped)} skipped, {len(failed)} failed"
    )

    return "\n".join(lines)


def format_cleanup_results(results: list[dict], repo_name: str) -> str:
    """Format cleanup results for display."""
    lines = [f"## 🧹 Branch Cleanup: {repo_name}", ""]

    deleted = [r for r in results if r["status"] == "deleted"]
    would_delete = [r for r in results if r["status"] == "would-delete"]
    protected = [r for r in results if r["status"] == "protected"]
    skipped = [r for r in results if r["status"] == "skipped"]
    fresh = [r for r in results if r["status"] == "fresh"]
    failed = [r for r in results if r["status"] == "failed"]

    if deleted:
        lines.append("### 🗑️ Deleted")
        for r in deleted:
            lines.append(f"- `{r['branch']}` ({r.get('author', 'unknown')})")
        lines.append("")

    if would_delete:
        lines.append("### 🔄 Would Delete (dry-run)")
        for r in would_delete:
            lines.append(f"- `{r['branch']}` ({r.get('author', 'unknown')})")
        lines.append("")

    if failed:
        lines.append("### ❌ Failed")
        for r in failed:
            lines.append(f"- `{r['branch']}`: {r['reason']}")
        lines.append("")

    summary_parts = []
    if deleted:
        summary_parts.append(f"{len(deleted)} deleted")
    if would_delete:
        summary_parts.append(f"{len(would_delete)} would-delete")
    if protected:
        summary_parts.append(f"{len(protected)} protected")
    if fresh:
        summary_parts.append(f"{len(fresh)} fresh")
    if skipped:
        summary_parts.append(f"{len(skipped)} not-merged")

    lines.append(f"**Summary:** {', '.join(summary_parts)}")

    return "\n".join(lines)
