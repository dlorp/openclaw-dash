"""Tests for PR workflow orchestration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from openclaw_dash.pr_orchestrator import PROrchestrator
from openclaw_dash.pr_workflow import PRWorkflow
from openclaw_dash.services.gateway_client import GatewayError


def create_workflow(tmp_path: Path) -> PRWorkflow:
    """Create a workflow backed by a temporary state file."""
    return PRWorkflow(tmp_path / ".pr-workflow-state.json")


def create_pr(workflow: PRWorkflow, pr_key: str = "openclaw-dash#123") -> None:
    """Create a standard test PR entry."""
    workflow.create_pr(
        pr_key,
        pr_url="https://github.com/dlorp/openclaw-dash/pull/123",
        pr_number=123,
        repo="dlorp/openclaw-dash",
        repo_short="openclaw-dash",
        base_branch="main",
        head_branch="feature/test",
        local_branch="feature/test",
        title="feat: test workflow",
        description="Test orchestration",
        created=1_717_171_717,
        created_commit="abc123",
        latest_commit="abc123",
    )


def completed(stdout: str, returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    """Create a completed subprocess result."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def build_orchestrator(tmp_path: Path) -> tuple[PROrchestrator, PRWorkflow, MagicMock]:
    """Create an orchestrator with a temporary repo and mocked gateway."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    gateway = MagicMock()
    workflow = create_workflow(tmp_path)
    create_pr(workflow)
    orchestrator = PROrchestrator(workflow=workflow, gateway_client=gateway, repo_path=repo_path)
    return orchestrator, workflow, gateway


def test_process_created_blocks_on_critical_static_analysis(tmp_path):
    orchestrator, workflow, gateway = build_orchestrator(tmp_path)

    audit_output = json.dumps(
        {"summary": {"critical": 2, "high": 1, "medium": 0, "low": 0}, "issues": [], "total_issues": 3}
    )
    with patch("openclaw_dash.pr_orchestrator.subprocess.run", return_value=completed(audit_output)):
        orchestrator.process_created("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "CREATED"
    assert pr_state.validations["security_review"].static_analysis is not None
    assert pr_state.validations["security_review"].static_analysis.critical_issues == 2
    gateway.spawn_agent.assert_not_called()


def test_process_security_review_waits_for_agent_and_advances(tmp_path):
    orchestrator, workflow, gateway = build_orchestrator(tmp_path)
    review_file = orchestrator.workspace_path / "reviews" / "PR-123-security.md"
    review_file.parent.mkdir(parents=True, exist_ok=True)
    review_file.write_text("Result: PASS\nIssues found: 0\n")

    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        status="running",
        agent_spawned=True,
        agent_session="sess-1",
        file=str(review_file),
    )

    orchestrator.process_security_review("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "CODE_REVIEW"
    assert pr_state.validations["security_review"].result == "pass"
    gateway.wait_for_agent.assert_called_once_with("sess-1", timeout=1800)


def test_process_security_review_marks_failure_on_timeout(tmp_path):
    orchestrator, workflow, gateway = build_orchestrator(tmp_path)
    review_file = orchestrator.workspace_path / "reviews" / "PR-123-security.md"
    review_file.parent.mkdir(parents=True, exist_ok=True)

    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        status="running",
        agent_spawned=True,
        agent_session="sess-1",
        file=str(review_file),
    )
    gateway.wait_for_agent.side_effect = GatewayError("timeout")

    orchestrator.process_security_review("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "SECURITY_REVIEW"
    assert pr_state.validations["security_review"].status == "completed"
    assert pr_state.validations["security_review"].result == "fail"


def test_process_code_review_spawns_waits_and_advances(tmp_path):
    orchestrator, workflow, gateway = build_orchestrator(tmp_path)
    review_file = orchestrator.workspace_path / "reviews" / "PR-123-code.md"
    review_file.parent.mkdir(parents=True, exist_ok=True)
    review_file.write_text("Result: FAIL\nIssues found: 3\n")

    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        status="completed",
        file=str(orchestrator.workspace_path / "reviews" / "PR-123-security.md"),
        file_exists=True,
        result="pass",
    )
    workflow.transition("openclaw-dash#123", "CODE_REVIEW")
    gateway.spawn_agent.return_value = "sess-2"

    orchestrator.process_code_review("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "FIXES_APPLIED"
    assert pr_state.validations["code_review"].agent_session == "sess-2"
    assert pr_state.validations["code_review"].issues_found == 3
    gateway.wait_for_agent.assert_called_once_with("sess-2", timeout=1800)


def test_process_fixes_applied_transitions_when_new_commit_detected(tmp_path):
    orchestrator, workflow, _gateway = build_orchestrator(tmp_path)
    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        status="completed",
        file="reviews/PR-123-security.md",
        file_exists=True,
        result="pass",
    )
    workflow.transition("openclaw-dash#123", "CODE_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "code_review",
        status="completed",
        file="reviews/PR-123-code.md",
        file_exists=True,
        result="fail",
    )
    workflow.transition("openclaw-dash#123", "FIXES_APPLIED")

    with patch(
        "openclaw_dash.pr_orchestrator.subprocess.run",
        return_value=completed("def456\n"),
    ):
        orchestrator.process_fixes_applied("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "CI_RUNNING"
    assert pr_state.latest_commit == "def456"
    assert pr_state.validations["ci"].status == "running"


def test_process_ci_running_moves_to_ready_when_checks_pass(tmp_path):
    orchestrator, workflow, _gateway = build_orchestrator(tmp_path)
    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        status="completed",
        file="reviews/PR-123-security.md",
        file_exists=True,
        result="pass",
    )
    workflow.transition("openclaw-dash#123", "CODE_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "code_review",
        status="completed",
        file="reviews/PR-123-code.md",
        file_exists=True,
        result="pass",
    )
    workflow.transition("openclaw-dash#123", "FIXES_APPLIED")
    workflow.transition("openclaw-dash#123", "CI_RUNNING")

    checks = json.dumps([{"name": "test", "state": "SUCCESS"}, {"name": "lint", "state": "PASS"}])
    with patch("openclaw_dash.pr_orchestrator.subprocess.run", return_value=completed(checks)):
        orchestrator.process_ci_running("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "READY"
    assert pr_state.validations["ci"].result == "pass"


def test_process_ci_running_loops_back_on_failure(tmp_path):
    orchestrator, workflow, _gateway = build_orchestrator(tmp_path)
    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        status="completed",
        file="reviews/PR-123-security.md",
        file_exists=True,
        result="pass",
    )
    workflow.transition("openclaw-dash#123", "CODE_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "code_review",
        status="completed",
        file="reviews/PR-123-code.md",
        file_exists=True,
        result="pass",
    )
    workflow.transition("openclaw-dash#123", "FIXES_APPLIED")
    workflow.transition("openclaw-dash#123", "CI_RUNNING")

    checks = json.dumps([{"name": "test", "state": "FAILURE"}, {"name": "lint", "state": "SUCCESS"}])
    with patch("openclaw_dash.pr_orchestrator.subprocess.run", return_value=completed(checks)):
        orchestrator.process_ci_running("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "FIXES_APPLIED"
    assert pr_state.validations["ci"].result == "fail"
    assert pr_state.validations["ci"].issues_found == 1


def test_agent_timeout_detection(tmp_path):
    orchestrator, workflow, gateway = build_orchestrator(tmp_path)
    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW")
    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        status="running",
        agent_spawned=True,
        agent_session="sess-timeout",
        spawned_at=100,
        file=str(orchestrator.workspace_path / "reviews" / "PR-123-security.md"),
    )

    with patch("openclaw_dash.pr_orchestrator.time.time", return_value=2_000):
        with patch.object(orchestrator, "batch_check_ci_status", return_value={}):
            with patch.object(orchestrator, "cleanup_completed_prs"):
                orchestrator.check_all_active_prs()

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    validation = pr_state.validations["security_review"]
    assert validation.status == "not_started"
    assert validation.result == "timeout"
    assert validation.retry_count == 1
    assert validation.agent_spawned is False
    gateway.wait_for_agent.assert_not_called()


def test_race_condition_protection(tmp_path):
    orchestrator, workflow, _gateway = build_orchestrator(tmp_path)
    workflow_data = workflow.load()
    workflow_data["active_prs"]["openclaw-dash#123"]["in_progress"] = True
    workflow.save(workflow_data)

    with patch.object(orchestrator, "run_workflow") as run_workflow:
        with patch.object(orchestrator, "batch_check_ci_status", return_value={}):
            with patch.object(orchestrator, "cleanup_completed_prs"):
                orchestrator.check_all_active_prs()

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.in_progress is True
    run_workflow.assert_not_called()


def test_idempotent_state_transitions(tmp_path):
    orchestrator, workflow, gateway = build_orchestrator(tmp_path)
    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        static_analysis={"critical_issues": 0, "high_issues": 0, "medium_issues": 0, "low_issues": 0, "passed": True},
    )

    with patch("openclaw_dash.pr_orchestrator.subprocess.run") as run_static_analysis:
        orchestrator.process_created("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "SECURITY_REVIEW"
    run_static_analysis.assert_not_called()

    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        status="running",
        agent_spawned=True,
        agent_session="sess-1",
        file=str(orchestrator.workspace_path / "reviews" / "PR-123-security.md"),
    )

    with patch.object(gateway, "spawn_agent") as spawn_agent:
        with patch.object(gateway, "wait_for_agent", side_effect=GatewayError("timeout")):
            orchestrator.process_security_review("openclaw-dash#123")

    spawn_agent.assert_not_called()


def test_error_state_handling(tmp_path):
    orchestrator, workflow, _gateway = build_orchestrator(tmp_path)

    with patch.object(orchestrator, "_run_static_analysis", side_effect=RuntimeError("boom")):
        orchestrator.run_workflow("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "CREATED"
    assert pr_state.error_info is not None
    assert pr_state.error_info["retry_count"] == 1
    assert pr_state.error_info["state_when_errored"] == "CREATED"

    with patch.object(orchestrator, "_run_static_analysis", side_effect=RuntimeError("boom again")):
        orchestrator.run_workflow("openclaw-dash#123")

    pr_state = workflow.get_pr_state("openclaw-dash#123")
    assert pr_state is not None
    assert pr_state.state == "ERROR"
    assert pr_state.error_info is not None
    assert pr_state.error_info["retry_count"] == 2


def test_pr_cleanup(tmp_path):
    orchestrator, workflow, _gateway = build_orchestrator(tmp_path)
    stale_timestamp = 10
    workflow_data = workflow.load()
    workflow_data["completed_prs"]["openclaw-dash#122"] = {
        "state": "READY",
        "pr_url": "https://github.com/dlorp/openclaw-dash/pull/122",
        "pr_number": 122,
        "repo": "dlorp/openclaw-dash",
        "repo_short": "openclaw-dash",
        "base_branch": "main",
        "head_branch": "feature/old",
        "local_branch": "feature/old",
        "title": "old",
        "description": "",
        "created": 1,
        "created_commit": "old",
        "latest_commit": "old",
        "last_checked_commit": "old",
        "in_progress": False,
        "last_heartbeat_processed": None,
        "error_info": None,
        "transitions": [],
        "validations": {},
        "completed_at": stale_timestamp,
    }
    workflow.save(workflow_data)

    with patch("openclaw_dash.pr_orchestrator.time.time", return_value=stale_timestamp + (31 * 24 * 60 * 60)):
        with patch.object(orchestrator, "_get_pr_lifecycle", return_value={"state": "CLOSED", "mergedAt": None}):
            orchestrator.cleanup_completed_prs()

    state = workflow.load()
    assert "openclaw-dash#123" not in state["active_prs"]
    assert "openclaw-dash#123" in state["completed_prs"]
    assert "openclaw-dash#122" not in state["completed_prs"]
