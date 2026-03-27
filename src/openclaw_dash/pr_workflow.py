"""PR workflow state machine with LLM agent integration.

Manages PR lifecycle through validation gates:
- CREATED → SECURITY_REVIEW → CODE_REVIEW → FIXES_APPLIED → CI_RUNNING → READY

Integrates:
- Static security analysis (audit tool)
- LLM agents via OpenClaw gateway (@security-specialist, @code-reviewer)
- CI status tracking (pr-tracker)
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# PR workflow states
State = Literal["CREATED", "SECURITY_REVIEW", "CODE_REVIEW", "FIXES_APPLIED", "CI_RUNNING", "READY"]

# Validation status
ValidationStatus = Literal["not_started", "running", "completed", "validated"]


@dataclass
class StaticAnalysisResult:
    """Results from openclaw-dash audit tool."""
    
    tool: str = "openclaw-dash audit"
    run_at: int | None = None
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    passed: bool = False
    report_file: str | None = None


@dataclass
class AgentReview:
    """LLM agent review tracking."""
    
    agent_spawned: bool = False
    agent_session: str | None = None
    spawned_at: int | None = None
    completed_at: int | None = None
    file: str | None = None
    file_exists: bool = False
    result: Literal["pass", "fail"] | None = None
    issues_found: int = 0


@dataclass
class Validation:
    """Combined validation (static + agent)."""
    
    status: ValidationStatus = "not_started"
    static_analysis: StaticAnalysisResult | None = None
    agent_spawned: bool = False
    agent_session: str | None = None
    spawned_at: int | None = None
    completed_at: int | None = None
    file: str | None = None
    file_exists: bool = False
    result: Literal["pass", "fail"] | None = None
    issues_found: int = 0


@dataclass
class PRWorkflowState:
    """Complete PR workflow state."""
    
    state: State
    pr_url: str
    pr_number: int
    repo: str
    repo_short: str
    base_branch: str
    head_branch: str
    local_branch: str
    title: str
    description: str
    created: int
    created_commit: str
    latest_commit: str
    transitions: list[dict]
    validations: dict[str, Validation]


class PRWorkflow:
    """PR workflow state machine."""
    
    # Valid state transitions
    TRANSITIONS = {
        "CREATED": ["SECURITY_REVIEW"],
        "SECURITY_REVIEW": ["CODE_REVIEW", "FIXES_APPLIED"],
        "CODE_REVIEW": ["FIXES_APPLIED"],
        "FIXES_APPLIED": ["CI_RUNNING"],
        "CI_RUNNING": ["READY", "FIXES_APPLIED"],
        "READY": []
    }
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.state_file.exists():
            self._init_state_file()
    
    def _init_state_file(self):
        """Initialize empty state file."""
        data = {
            "$schema": "pr-workflow-state-v1",
            "version": "1.1.0",
            "description": "PR workflow state machine - OpenClaw LLM agent integration",
            "active_prs": {},
            "completed_prs": {}
        }
        self.state_file.write_text(json.dumps(data, indent=2))
    
    def load(self) -> dict:
        """Load workflow state from disk."""
        if not self.state_file.exists():
            self._init_state_file()
        return json.loads(self.state_file.read_text())
    
    def save(self, data: dict):
        """Save workflow state to disk."""
        self.state_file.write_text(json.dumps(data, indent=2))
    
    def get_pr_state(self, pr_key: str) -> PRWorkflowState | None:
        """Get workflow state for a specific PR."""
        data = self.load()
        pr_data = data.get("active_prs", {}).get(pr_key)
        if not pr_data:
            return None
        
        # Convert dict to PRWorkflowState
        validations = {}
        for key, val in pr_data.get("validations", {}).items():
            static = val.get("static_analysis")
            validations[key] = Validation(
                status=val.get("status", "not_started"),
                static_analysis=StaticAnalysisResult(**static) if static else None,
                agent_spawned=val.get("agent_spawned", False),
                agent_session=val.get("agent_session"),
                spawned_at=val.get("spawned_at"),
                completed_at=val.get("completed_at"),
                file=val.get("file"),
                file_exists=val.get("file_exists", False),
                result=val.get("result"),
                issues_found=val.get("issues_found", 0)
            )
        
        return PRWorkflowState(
            state=pr_data["state"],
            pr_url=pr_data["pr_url"],
            pr_number=pr_data["pr_number"],
            repo=pr_data["repo"],
            repo_short=pr_data["repo_short"],
            base_branch=pr_data["base_branch"],
            head_branch=pr_data["head_branch"],
            local_branch=pr_data["local_branch"],
            title=pr_data["title"],
            description=pr_data.get("description", ""),
            created=pr_data["created"],
            created_commit=pr_data["created_commit"],
            latest_commit=pr_data["latest_commit"],
            transitions=pr_data.get("transitions", []),
            validations=validations
        )
    
    def can_transition(self, pr_key: str, from_state: State, to_state: State) -> tuple[bool, str]:
        """Check if transition is valid."""
        # Check if transition is allowed by state machine
        if to_state not in self.TRANSITIONS.get(from_state, []):
            return False, f"Invalid transition: {from_state} → {to_state}"
        
        # Check validation gates
        pr_state = self.get_pr_state(pr_key)
        if not pr_state:
            return False, "PR not found in workflow"
        
        # SECURITY_REVIEW → CODE_REVIEW: security must be complete
        if from_state == "SECURITY_REVIEW" and to_state == "CODE_REVIEW":
            sec = pr_state.validations.get("security_review")
            if not sec or sec.status != "completed" or not sec.file_exists:
                return False, "Security review not complete"
        
        # CODE_REVIEW → FIXES_APPLIED: code review must be complete
        if from_state == "CODE_REVIEW" and to_state == "FIXES_APPLIED":
            code = pr_state.validations.get("code_review")
            if not code or code.status != "completed" or not code.file_exists:
                return False, "Code review not complete"
        
        # CI_RUNNING → READY: CI must pass
        if from_state == "CI_RUNNING" and to_state == "READY":
            ci = pr_state.validations.get("ci")
            if not ci or ci.status != "completed":
                return False, "CI not passing"
        
        return True, ""
    
    def is_ready_for_merge(self, pr_key: str) -> tuple[bool, str]:
        """Check if PR is ready for merge (state === READY)."""
        pr_state = self.get_pr_state(pr_key)
        if not pr_state:
            return False, "PR not in workflow"
        
        if pr_state.state != "READY":
            return False, f"PR is at {pr_state.state}, not READY"
        
        return True, ""
