"""PR workflow orchestration for automated review and validation."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from openclaw_dash.pr_workflow import PRWorkflow, PRWorkflowState, StaticAnalysisResult
from openclaw_dash.services.gateway_client import GatewayClient, GatewayError

logger = logging.getLogger(__name__)


class PROrchestrator:
    """Drive PRs through the workflow state machine."""

    SECURITY_AGENT_ID = "security-reviewer"
    CODE_REVIEW_AGENT_ID = "code-reviewer"

    def __init__(self, workflow: PRWorkflow, gateway_client: GatewayClient, repo_path: Path):
        self.workflow = workflow
        self.gateway_client = gateway_client
        self.repo_path = repo_path
        workspace = os.environ.get("OPENCLAW_WORKSPACE") or str(repo_path)
        self.workspace_path = Path(workspace)

    def run_workflow(self, pr_key: str) -> None:
        """Advance a PR until it reaches a waiting point or READY."""
        while True:
            pr_state = self._require_pr(pr_key)
            previous_state = pr_state.state

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

            current_state = self._require_pr(pr_key).state
            if current_state in {"READY", previous_state}:
                return

    def process_created(self, pr_key: str) -> None:
        """Run static analysis and spawn the security reviewer."""
        pr_state = self._require_pr(pr_key)
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
            status="running",
            static_analysis=analysis,
        )

        if analysis.critical_issues > 0:
            logger.info(
                "Blocking PR %s at CREATED due to %s critical issues",
                pr_key,
                analysis.critical_issues,
            )
            return

        self._transition(pr_key, "SECURITY_REVIEW")
        review_file = self._review_file(pr_state, "security")
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
            file=str(review_file),
        )
        logger.info("Spawned security review agent for %s: %s", pr_key, session_key)

    def process_security_review(self, pr_key: str) -> None:
        """Wait for the security review and advance if it passed."""
        pr_state = self._require_pr(pr_key)
        validation = pr_state.validations["security_review"]
        review_file = Path(validation.file) if validation.file else self._review_file(pr_state, "security")

        if not validation.agent_session:
            self.workflow.update_validation(pr_key, "security_review", result="fail", status="completed")
            logger.warning("Security review missing agent session for %s", pr_key)
            return

        try:
            self.gateway_client.wait_for_agent(validation.agent_session, timeout=1800)
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
            self.gateway_client.wait_for_agent(validation.agent_session or "", timeout=1800)
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
        checks = self._get_ci_checks(pr_state.pr_number)
        status = self._summarize_ci_checks(checks)

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
        for pr_key in data.get("active_prs", {}):
            try:
                self.run_workflow(pr_key)
            except Exception:
                logger.exception("Failed to process PR workflow for %s", pr_key)

    def _run_static_analysis(self) -> dict[str, Any]:
        result = subprocess.run(
            ["python", "-m", "openclaw_dash.tools.audit", "--json"],
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

    def _require_pr(self, pr_key: str) -> PRWorkflowState:
        pr_state = self.workflow.get_pr_state(pr_key)
        if not pr_state:
            raise KeyError(f"PR not found in workflow: {pr_key}")
        return pr_state
