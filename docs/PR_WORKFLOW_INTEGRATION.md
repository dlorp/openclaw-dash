# PR Workflow Integration Design

## Overview

Integration of OpenClaw LLM agent workflow into openclaw-dash for automated PR review.

**Goal:** Add LLM-powered security and code reviews to the existing PR automation pipeline.

## Architecture

### Two-Layer Security Review

1. **Static Analysis** (existing `audit` tool)
   - Dependency vulnerabilities (`pip-audit`, `npm audit`)
   - Hardcoded secrets (regex patterns)
   - Dangerous code patterns (`eval`, `pickle`, `shell=True`)
   - **Runs first, blocks if critical issues found**

2. **LLM Agent Review** (new, via OpenClaw gateway)
   - Context-aware code analysis
   - Logic vulnerabilities (command injection, auth gaps)
   - Produces review file: `reviews/PR-{number}-security.md`
   - **Only runs if static analysis passes**

### State Machine

```
CREATED 
  ↓ (run audit, spawn @security-specialist)
SECURITY_REVIEW (static + LLM review)
  ↓ (spawn @code-reviewer)
CODE_REVIEW (LLM review)
  ↓ (apply fixes, commit, push)
FIXES_APPLIED
  ↓ (CI runs)
CI_RUNNING
  ↓ (all checks pass)
READY ✅ (can auto-merge)
```

## Files Modified

### New Files

**src/openclaw_dash/pr_workflow.py** (created)
- `PRWorkflow` class — state machine
- State validation gates
- Transition checking
- `is_ready_for_merge()` — validation gate for auto-merge

**docs/PR_WORKFLOW_INTEGRATION.md** (this file)

### Modified Files

**src/openclaw_dash/automation/pr_auto.py**
- Add workflow validation gate before auto-merge
- Check `workflow.is_ready_for_merge(pr_key)` before calling `gh pr merge`
- Fall back to existing logic if PR not in workflow

**src/openclaw_dash/services/gateway_client.py**
- Add `spawn_agent(agent_id, task)` method
- Add `get_agent_status(session_key)` method
- Add `list_sessions()` method

**src/openclaw_dash/tools/.pr-state.json** (schema extension)
- Keep existing CI tracking
- Add `workflow_state` field (optional, for PRs using LLM workflow)

**src/openclaw_dash/widgets/pr_workflow_panel.py** (optional TUI panel)
- Show PR workflow progress in dashboard
- Display current state, validation gates
- Agent status (spawned, running, completed)

### Documentation Updates

**docs/TOOLS.md**
- Add section: "LLM Agent Workflow"
- Document `pr_workflow.py` API
- Usage examples

**README.md**
- Update features list
- Add "LLM-powered PR reviews" bullet
- Link to workflow docs

**docs/ARCHITECTURE.md**
- Add workflow state machine diagram
- Document OpenClaw gateway integration

## Implementation Phases

### Phase 1: Core State Machine ✅ DONE
- Created `pr_workflow.py`
- State definitions
- Transition validation
- `is_ready_for_merge()` gate

### Phase 2: Gateway Integration (TODO)
- Extend `gateway_client.py`
- Add agent spawn/track methods
- Handle timeouts (30 min max)
- Poll for completion

### Phase 3: Auto-Merge Integration (TODO)
- Modify `pr_auto.py`
- Add workflow check before merge
- Backward compatible (no workflow = use existing logic)

### Phase 4: Static Analysis Integration (TODO)
- Call `audit` tool before spawning LLM agent
- Block if `critical_issues > 0`
- Store results in workflow state

### Phase 5: TUI Panel (TODO, optional)
- Visual workflow progress
- Agent status display
- Review file links

### Phase 6: Testing (TODO)
- Unit tests for state machine
- Integration test with mock gateway
- Backward compat test (existing tools unaffected)

## Configuration

**~/.config/openclaw-dash/config.toml**

```toml
[pr_workflow]
enabled = true  # Enable LLM workflow
gateway_host = "localhost"
gateway_port = 18789
timeout_seconds = 1800  # 30 min agent timeout
static_analysis_first = true  # Run audit before spawning agents
block_on_critical = true  # Block if audit finds critical issues

[pr_workflow.agents]
security_specialist = "security-specialist"  # Agent ID
code_reviewer = "code-reviewer"  # Agent ID
```

## API

### PRWorkflow

```python
from openclaw_dash.pr_workflow import PRWorkflow

workflow = PRWorkflow(state_file=Path(".pr-workflow-state.json"))

# Check if PR is ready for merge
ready, reason = workflow.is_ready_for_merge("openclaw-dash#123")
if ready:
    # Safe to auto-merge
    gh_pr_merge(...)
else:
    print(f"Not ready: {reason}")
```

### GatewayClient (extended)

```python
from openclaw_dash.services.gateway_client import GatewayClient

client = GatewayClient(host="localhost", port=18789)

# Spawn security review agent
session_key = client.spawn_agent(
    agent_id="security-specialist",
    task=f"Review PR {pr_number} for security issues"
)

# Poll for completion
while True:
    status = client.get_agent_status(session_key)
    if status["completed"]:
        break
    time.sleep(10)
```

## Backward Compatibility

**Existing tools unaffected:**
- `pr-tracker` — continues CI tracking
- `pr-auto` — falls back to old logic if workflow not enabled
- `audit` — can be used standalone

**Opt-in:** LLM workflow only activates if:
1. `pr_workflow.enabled = true` in config
2. OpenClaw gateway is running
3. PR created with workflow flag

## Security Considerations

1. **Agent timeout:** 30 min max (prevent hung agents)
2. **Secrets:** Review files may contain sensitive info (store in `.audit/`, gitignore)
3. **Cost:** LLM reviews cost money (track via OpenClaw metrics)
4. **False positives:** Static analysis may block valid PRs (allow override)

## Testing Plan

**Unit Tests:**
- State machine transitions
- Validation gates
- `is_ready_for_merge()` logic

**Integration Tests:**
- Mock gateway responses
- Agent spawn/track/complete cycle
- Audit → agent → review workflow

**Manual Testing:**
- Create real PR
- Watch workflow progress in dashboard
- Verify auto-merge blocked until READY

## Next Steps

1. ✅ Create `pr_workflow.py` (DONE)
2. ⏳ Extend `gateway_client.py` (IN PROGRESS)
3. ⏳ Modify `pr_auto.py` (TODO)
4. ⏳ Add config section (TODO)
5. ⏳ Write tests (TODO)
6. ⏳ Update docs (TODO)

## Questions / Risks

**Q:** What if OpenClaw gateway is down?  
**A:** Fall back to existing pr-auto logic (no workflow enforcement)

**Q:** What if agent times out?  
**A:** Mark validation as failed, require manual review

**Q:** What about concurrent PRs?  
**A:** Each PR has separate state in `active_prs` (no conflicts)

**Q:** Can we disable for specific repos?  
**A:** Yes, config per-repo in `pr_workflow.repos_allowlist`
