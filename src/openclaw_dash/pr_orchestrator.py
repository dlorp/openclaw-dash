"""PR workflow orchestration for automated review and validation."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from openclaw_dash.pr_workflow import PRWorkflow, PRWorkflowState, StaticAnalysisResult
from openclaw_dash.services.gateway_client import GatewayClient, GatewayError

logger = logging.getLogger(__name__)


class PROrchestrator:
    """Drive PRs through the workflow state machine."""

    SECURITY_AGENT_ID = "security-reviewer"
    CODE_REVIEW_AGENT_ID = "code-reviewer"

    def __init__(
        self,
        workflow: PRWorkflow,
        gateway_client: GatewayClient,
        repo_path: Path,
        *,
        agent_timeout_seconds: int = 1800,
    ):
        self.workflow = workflow
        self.gateway_client = gateway_client
        self.repo_path = repo_path
        self.agent_timeout_seconds = agent_timeout_seconds
        self._batched_ci_status: dict[str, dict[str, Any]] = {}
        workspace = os.environ.get("OPENCLAW_WORKSPACE") or str(repo_path)
        self.workspace_path = Path(workspace)

    def run_workflow(self, pr_key: str) -> None:
        """Advance a PR until it reaches a waiting point or READY."""
        while True:
            pr_state = self._require_pr(pr_key)
            previous_state = pr_state.state

            try:
                if pr_state.state == "CREATED":
                    self.process_created(pr_key)
                elif pr_state.state == "SECURITY_REVIEW":
                    self.process_security_review(pr_key)
                elif pr_state.state == "CODE_REVIEW":
                    self.process_code_review(pr_key)
                elif pr_state.state == "FIXES_APPLIED":
                    self.process_fixes_applied(pr_key)
                elif pr_state.state == "CI_RUNNING":
                    self.process_ci_running(pr_key)
                else:
                    return
            except Exception as exc:
                self._handle_processing_error(pr_key, previous_state, exc)
                return

            current_state = self._require_pr(pr_key).state
            if current_state in {"READY", "ERROR", previous_state}:
                return

    def process_created(self, pr_key: str) -> None:
        """Run static analysis and advance to security review."""
        pr_state = self._require_pr(pr_key)
        validation = pr_state.validations["security_review"]
        if validation.static_analysis is not None:
            logger.info("Static analysis already recorded for %s", pr_key)
            if validation.static_analysis.critical_issues == 0:
                self._transition(pr_key, "SECURITY_REVIEW")
            return

        audit_data = self._run_static_analysis()
        analysis = StaticAnalysisResult(
            run_at=int(time.time()),
            critical_issues=audit_data["summary"].get("critical", 0),
            high_issues=audit_data["summary"].get("high", 0),
            medium_issues=audit_data["summary"].get("medium", 0),
            low_issues=audit_data["summary"].get("low", 0),
            passed=audit_data["summary"].get("critical", 0) == 0,
        )
        self.workflow.update_validation(
            pr_key,
            "security_review",
            status="completed" if analysis.critical_issues > 0 else "not_started",
            static_analysis=analysis,
            completed_at=int(time.time()),
            result="fail" if analysis.critical_issues > 0 else None,
        )

        if analysis.critical_issues > 0:
            logger.info(
                "Blocking PR %s at CREATED due to %s critical issues",
                pr_key,
                analysis.critical_issues,
            )
            return

        self._transition(pr_key, "SECURITY_REVIEW")

    def process_security_review(self, pr_key: str) -> None:
        """Wait for the security review and advance if it passed."""
        pr_state = self._require_pr(pr_key)
        validation = pr_state.validations["security_review"]
        review_file = Path(validation.file) if validation.file else self._review_file(pr_state, "security")

        if validation.status == "completed":
            logger.info("Security review already completed for %s", pr_key)
            if validation.file_exists and validation.result == "pass":
                self._transition(pr_key, "CODE_REVIEW")
            return

        if not validation.agent_spawned:
            task = (
                f"Review PR #{pr_state.pr_number} for security issues in {self.repo_path}. "
                f"Write the report to {review_file}. Include a clear 'Result: PASS' or "
                f"'Result: FAIL' line and 'Issues found: <n>'."
            )
            session_key = self.gateway_client.spawn_agent(self.SECURITY_AGENT_ID, task)
            self.workflow.update_validation(
                pr_key,
                "security_review",
                status="running",
                agent_spawned=True,
                agent_session=session_key,
                spawned_at=int(time.time()),
                completed_at=None,
                file=str(review_file),
            )
            validation = self._require_pr(pr_key).validations["security_review"]
            logger.info("Spawned security review agent for %s: %s", pr_key, session_key)

        if not validation.agent_session:
            self.workflow.update_validation(pr_key, "security_review", result="fail", status="completed")
            logger.warning("Security review missing agent session for %s", pr_key)
            return

        try:
            self.gateway_client.wait_for_agent(validation.agent_session, timeout=self.agent_timeout_seconds)
        except GatewayError as exc:
            self.workflow.update_validation(
                pr_key,
                "security_review",
                status="completed",
                completed_at=int(time.time()),
                result="fail",
                file=str(review_file),
                file_exists=review_file.exists(),
            )
            logger.warning("Security review agent failed for %s: %s", pr_key, exc)
            return

        result = self._parse_review_file(review_file)
        self.workflow.update_validation(
            pr_key,
            "security_review",
            status="completed",
            completed_at=int(time.time()),
            file=str(review_file),
            file_exists=result["file_exists"],
            result=result["result"],
            issues_found=result["issues_found"],
        )
        logger.info("Completed security review for %s with result=%s", pr_key, result["result"])

        if result["file_exists"] and result["result"] == "pass":
            self._transition(pr_key, "CODE_REVIEW")

    def process_code_review(self, pr_key: str) -> None:
        """Spawn and wait for the code review agent."""
        pr_state = self._require_pr(pr_key)
        validation = pr_state.validations["code_review"]
        review_file = Path(validation.file) if validation.file else self._review_file(pr_state, "code")

        if validation.status == "completed":
            logger.info("Code review already completed for %s", pr_key)
            if validation.file_exists:
                self._transition(pr_key, "FIXES_APPLIED")
            return

        if not validation.agent_spawned:
            task = (
                f"Review PR #{pr_state.pr_number} for code quality and correctness in {self.repo_path}. "
                f"Write the report to {review_file}. Include a clear 'Result: PASS' or "
                f"'Result: FAIL' line and 'Issues found: <n>'."
            )
            session_key = self.gateway_client.spawn_agent(self.CODE_REVIEW_AGENT_ID, task)
            self.workflow.update_validation(
                pr_key,
                "code_review",
                status="running",
                agent_spawned=True,
                agent_session=session_key,
                spawned_at=int(time.time()),
                file=str(review_file),
            )
            validation = self._require_pr(pr_key).validations["code_review"]
            logger.info("Spawned code review agent for %s: %s", pr_key, session_key)

        try:
            self.gateway_client.wait_for_agent(validation.agent_session or "", timeout=self.agent_timeout_seconds)
        except GatewayError as exc:
            self.workflow.update_validation(
                pr_key,
                "code_review",
                status="completed",
                completed_at=int(time.time()),
                result="fail",
                file=str(review_file),
                file_exists=review_file.exists(),
            )
            logger.warning("Code review agent failed for %s: %s", pr_key, exc)
            return

        result = self._parse_review_file(review_file)
        self.workflow.update_validation(
            pr_key,
            "code_review",
            status="completed",
            completed_at=int(time.time()),
            file=str(review_file),
            file_exists=result["file_exists"],
            result=result["result"],
            issues_found=result["issues_found"],
        )
        logger.info("Completed code review for %s with result=%s", pr_key, result["result"])

        if result["file_exists"]:
            self._transition(pr_key, "FIXES_APPLIED")

    def process_fixes_applied(self, pr_key: str) -> None:
        """Advance once new commits have been pushed after review feedback."""
        pr_state = self._require_pr(pr_key)
        latest_commit = self._get_head_commit(pr_state.local_branch)
        if latest_commit == pr_state.latest_commit:
            logger.info("No new commits detected for %s", pr_key)
            return

        self._update_pr_fields(pr_key, latest_commit=latest_commit)
        self.workflow.update_validation(pr_key, "ci", status="running", result=None)
        self._transition(pr_key, "CI_RUNNING")
        logger.info("Detected new commits for %s: %s", pr_key, latest_commit)

    def process_ci_running(self, pr_key: str) -> None:
        """Poll GitHub check status and move to READY or back to FIXES_APPLIED."""
        pr_state = self._require_pr(pr_key)
        batch_status = self._batched_ci_status.get(pr_key, {}).get("ci_status")
        status = batch_status or self._summarize_ci_checks(self._get_ci_checks(pr_state.pr_number))

        self.workflow.update_validation(
            pr_key,
            "ci",
            status=status["validation_status"],
            completed_at=int(time.time()) if status["terminal"] else None,
            result=status["result"],
            issues_found=status["failed_checks"],
        )

        if status["result"] == "pass":
            self._transition(pr_key, "READY")
        elif status["result"] == "fail":
            self._transition(pr_key, "FIXES_APPLIED")

        logger.info("CI status for %s: %s", pr_key, status["result"] or "pending")

    def check_all_active_prs(self) -> None:
        """Process each active PR once."""
        data = self.workflow.load()
        pr_keys = list(data.get("active_prs", {}))
        self._batched_ci_status = self.batch_check_ci_status(pr_keys)
        heartbeat_at = int(time.time())

        for pr_key in pr_keys:
            pr_data = self.workflow.load().get("active_prs", {}).get(pr_key)
            if not pr_data:
                continue
            if pr_data.get("in_progress"):
                logger.info("Skipping %s because it is already in progress", pr_key)
                continue

            self._update_pr_fields(
                pr_key,
                in_progress=True,
                last_heartbeat_processed=heartbeat_at,
            )
            try:
                batch_data = self._batched_ci_status.get(pr_key, {})
                if batch_data.get("latest_commit"):
                    self._update_pr_fields(pr_key, latest_commit=batch_data["latest_commit"])

                if self._handle_agent_timeout(pr_key):
                    continue

                pr_state = self._require_pr(pr_key)
                if self._should_skip_unchanged(pr_state):
                    logger.info("Skipping unchanged PR %s", pr_key)
                    continue

                self.run_workflow(pr_key)
                current = self._require_pr(pr_key)
                if current.state != "ERROR" and current.error_info is not None:
                    self._update_pr_fields(pr_key, error_info=None)
                self._update_pr_fields(pr_key, last_checked_commit=current.latest_commit)
            except Exception:
                logger.exception("Failed to process PR workflow for %s", pr_key)
            finally:
                if self.workflow.get_pr_state(pr_key) is not None:
                    self._update_pr_fields(pr_key, in_progress=False)

        self.cleanup_completed_prs()

    def batch_check_ci_status(self, pr_keys: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch PR metadata in batches and derive CI state when possible."""
        grouped: dict[str, list[str]] = defaultdict(list)
        for pr_key in pr_keys:
            pr_state = self.workflow.get_pr_state(pr_key)
            if pr_state:
                grouped[pr_state.repo].append(pr_key)

        results: dict[str, dict[str, Any]] = {}
        for repo, repo_pr_keys in grouped.items():
            pulls = self._get_repo_pulls(repo)
            pulls_by_number = {pull.get("number"): pull for pull in pulls}

            for pr_key in repo_pr_keys:
                pr_state = self.workflow.get_pr_state(pr_key)
                if not pr_state:
                    continue
                pull = pulls_by_number.get(pr_state.pr_number, {})
                results[pr_key] = {
                    "latest_commit": pull.get("head", {}).get("sha"),
                    "ci_status": self._summarize_batch_pull_ci(pull),
                }

        return results

    def cleanup_completed_prs(self) -> None:
        """Move merged or closed PRs out of the active set and prune old completions."""
        data = self.workflow.load()
        now = int(time.time())

        for pr_key, pr_data in list(data.get("active_prs", {}).items()):
            status = self._get_pr_lifecycle(pr_data["pr_number"])
            state = status.get("state")
            merged_at = status.get("mergedAt")
            if not merged_at and state != "CLOSED":
                continue

            completed = data.setdefault("completed_prs", {})
            completed[pr_key] = {
                **pr_data,
                "completed_at": now,
                "completion_reason": "merged" if merged_at else "closed",
                "merged_at": merged_at,
            }
            del data["active_prs"][pr_key]

        cutoff = now - (30 * 24 * 60 * 60)
        for pr_key, pr_data in list(data.get("completed_prs", {}).items()):
            completed_at = pr_data.get("completed_at", pr_data.get("created", 0))
            if completed_at < cutoff:
                del data["completed_prs"][pr_key]

        self.workflow.save(data)

    def _run_static_analysis(self) -> dict[str, Any]:
        result = subprocess.run(
            ["python3", "-m", "openclaw_dash.tools.audit", "--json"],
            capture_output=True,
            text=True,
            cwd=self.repo_path,
            timeout=600,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Static analysis failed")

        payload = json.loads(result.stdout)
        if isinstance(payload, list):
            if not payload:
                raise RuntimeError("Static analysis returned no results")
            payload = payload[0]
        return payload

    def _get_head_commit(self, branch: str) -> str:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", branch],
            capture_output=True,
            text=True,
            cwd=self.repo_path,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Failed to read git log")
        return result.stdout.strip()

    def _get_ci_checks(self, pr_number: int) -> Any:
        result = subprocess.run(
            ["gh", "pr", "checks", str(pr_number), "--json", "name,state,link,bucket"],
            capture_output=True,
            text=True,
            cwd=self.repo_path,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Failed to fetch CI checks")
        return json.loads(result.stdout or "[]")

    def _get_repo_pulls(self, repo: str) -> list[dict[str, Any]]:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls"],
            capture_output=True,
            text=True,
            cwd=self.repo_path,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Failed to fetch PR list")
        payload = json.loads(result.stdout or "[]")
        return payload if isinstance(payload, list) else []

    def _get_pr_lifecycle(self, pr_number: int) -> dict[str, Any]:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "state,mergedAt"],
            capture_output=True,
            text=True,
            cwd=self.repo_path,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Failed to fetch PR lifecycle")
        payload = json.loads(result.stdout or "{}")
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _summarize_ci_checks(checks: Any) -> dict[str, Any]:
        if isinstance(checks, dict):
            checks = checks.get("checks", [])

        failing_states = {"fail", "failed", "failure", "error", "cancelled", "timed_out"}
        pending_states = {"pending", "queued", "in_progress", "waiting", "requested"}
        passing_states = {"pass", "passed", "success", "successful", "completed", "skipping", "skip"}

        failed_checks = 0
        pending = False

        for check in checks:
            raw_state = str(check.get("state") or check.get("bucket") or "").lower()
            if raw_state in failing_states:
                failed_checks += 1
            elif raw_state in pending_states or raw_state == "":
                pending = True
            elif raw_state not in passing_states:
                pending = True

        if failed_checks:
            return {
                "validation_status": "completed",
                "terminal": True,
                "result": "fail",
                "failed_checks": failed_checks,
            }
        if pending:
            return {
                "validation_status": "running",
                "terminal": False,
                "result": None,
                "failed_checks": 0,
            }
        return {
            "validation_status": "completed",
            "terminal": True,
            "result": "pass",
            "failed_checks": 0,
        }

    @classmethod
    def _summarize_batch_pull_ci(cls, pull: dict[str, Any]) -> dict[str, Any] | None:
        checks = pull.get("checks")
        if checks is not None:
            return cls._summarize_ci_checks(checks)

        mergeable_state = str(pull.get("mergeable_state") or "").lower()
        if not mergeable_state:
            return None
        if mergeable_state == "clean":
            return {
                "validation_status": "completed",
                "terminal": True,
                "result": "pass",
                "failed_checks": 0,
            }
        if mergeable_state in {"dirty", "blocked"}:
            return {
                "validation_status": "completed",
                "terminal": True,
                "result": "fail",
                "failed_checks": 1,
            }
        return {
            "validation_status": "running",
            "terminal": False,
            "result": None,
            "failed_checks": 0,
        }

    def _review_file(self, pr_state: PRWorkflowState, review_kind: str) -> Path:
        return self.workspace_path / "reviews" / f"PR-{pr_state.pr_number}-{review_kind}.md"

    @staticmethod
    def _parse_review_file(review_file: Path) -> dict[str, Any]:
        if not review_file.exists():
            return {"file_exists": False, "result": "fail", "issues_found": 0}

        content = review_file.read_text()
        normalized = content.lower()

        result_match = re.search(r"result:\s*(pass|fail)", normalized)
        if result_match:
            result = result_match.group(1)
        elif "pass" in normalized and "fail" not in normalized:
            result = "pass"
        else:
            result = "fail"

        issues_match = re.search(r"issues\s+found:\s*(\d+)", normalized)
        if issues_match:
            issues_found = int(issues_match.group(1))
        else:
            issues_found = len(re.findall(r"^- ", content, flags=re.MULTILINE))

        return {"file_exists": True, "result": result, "issues_found": issues_found}

    def _transition(self, pr_key: str, to_state: str) -> None:
        current = self._require_pr(pr_key)
        allowed, reason = self.workflow.can_transition(pr_key, current.state, to_state)  # type: ignore[arg-type]
        if not allowed:
            raise ValueError(reason)
        self.workflow.transition(pr_key, to_state, at=int(time.time()))
        logger.info("Transitioned %s: %s -> %s", pr_key, current.state, to_state)

    def _update_pr_fields(self, pr_key: str, **changes: Any) -> None:
        data = self.workflow.load()
        pr_data = data.get("active_prs", {}).get(pr_key)
        if not pr_data:
            raise KeyError(f"PR not found in workflow: {pr_key}")
        pr_data.update(changes)
        self.workflow.save(data)

    def _handle_agent_timeout(self, pr_key: str) -> bool:
        pr_state = self._require_pr(pr_key)
        now = int(time.time())
        for validation_name in ("security_review", "code_review"):
            validation = pr_state.validations.get(validation_name)
            if not validation or validation.status != "running" or not validation.spawned_at:
                continue
            if now - validation.spawned_at <= self.agent_timeout_seconds:
                continue

            retry_count = validation.retry_count + 1
            terminal = retry_count > 1
            self.workflow.update_validation(
                pr_key,
                validation_name,
                status="completed" if terminal else "not_started",
                result="timeout",
                retry_count=retry_count,
                completed_at=now,
                agent_spawned=False if not terminal else validation.agent_spawned,
                agent_session=None if not terminal else validation.agent_session,
                spawned_at=None if not terminal else validation.spawned_at,
            )
            if terminal:
                logger.error("Agent timeout exceeded retry budget for %s (%s)", pr_key, validation_name)
            else:
                logger.warning("Retrying %s after timeout for %s", validation_name, pr_key)
            return True
        return False

    def _should_skip_unchanged(self, pr_state: PRWorkflowState) -> bool:
        if pr_state.state in {"CI_RUNNING", "READY", "ERROR"}:
            return False
        if pr_state.last_checked_commit != pr_state.latest_commit:
            return False
        return all(validation.status != "running" for validation in pr_state.validations.values())

    def _handle_processing_error(self, pr_key: str, previous_state: str, exc: Exception) -> None:
        now = int(time.time())
        data = self.workflow.load()
        pr_data = data.get("active_prs", {}).get(pr_key)
        if not pr_data:
            raise KeyError(f"PR not found in workflow: {pr_key}") from exc

        error_info = pr_data.get("error_info") or {}
        retry_count = int(error_info.get("retry_count", 0)) + 1
        pr_data["error_info"] = {
            "message": str(exc),
            "timestamp": now,
            "retry_count": retry_count,
            "state_when_errored": previous_state,
        }
        pr_data.setdefault("transitions", []).append(
            {"from": previous_state, "to": "ERROR", "at": now, "metadata": {"message": str(exc)}}
        )

        if retry_count < 2:
            pr_data["state"] = previous_state
            pr_data["transitions"].append(
                {"from": "ERROR", "to": previous_state, "at": now, "metadata": {"retry": retry_count}}
            )
            logger.warning("Retrying %s after orchestrator error on %s: %s", previous_state, pr_key, exc)
        else:
            pr_data["state"] = "ERROR"
            logger.exception("PR workflow requires human attention for %s", pr_key, exc_info=exc)

        self.workflow.save(data)

    def _require_pr(self, pr_key: str) -> PRWorkflowState:
        pr_state = self.workflow.get_pr_state(pr_key)
        if not pr_state:
            raise KeyError(f"PR not found in workflow: {pr_key}")
        return pr_state
