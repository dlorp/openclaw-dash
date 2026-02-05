# Integrated Tools Reference

openclaw-dash bundles automation tools that work standalone or integrate with the dashboard. This reference covers CLI usage, configuration, and API access.

## Quick Reference

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `pr-describe` | Generate PR descriptions from diffs | PR creation workflow |
| `pr-create` | Create PRs with auto-generated content | Branch → PR automation |
| `version-bump` | Semantic versioning from commits | Release management |
| `repo-scanner` | Repository health metrics | Dashboard panels |
| `smart-todo-scanner` | Context-aware TODO categorization | Code quality tracking |
| `dep-shepherd` | Dependency audit and updates | Security & maintenance |
| `audit` | Security scanning | Vulnerability detection |

---

## pr-describe

Generate structured PR descriptions from git diffs. Analyzes commits, categorizes changes, and flags breaking changes or new dependencies.

### Usage

```bash
# Basic usage - current branch vs main
pr-describe

# Compare specific branch against main
pr-describe feature-xyz

# Compare against different base branch
pr-describe --base develop

# Output formats
pr-describe --format json          # JSON output
pr-describe --format markdown      # Markdown (default)

# Specific outputs
pr-describe --title               # Just the suggested PR title
pr-describe --clipboard           # Copy to clipboard

# Include existing PR discussion
pr-describe --include-comments

# Output styles
pr-describe --style verbose       # Full details (default)
pr-describe --style concise       # Shorter output
pr-describe --style minimal       # Bare minimum
```

### Configuration

Config file: `~/.config/openclaw-dash/pr-describe.yaml`

```yaml
output_style: verbose      # verbose | concise | minimal
include_testing: true      # Include testing suggestions
include_breaking_changes: true
title_format: "{type}: {summary}"
max_files_shown: 15
max_commits_shown: 7
```

### Module API

```python
from openclaw_dash.tools.pr_describe import generate_pr_description

desc = generate_pr_description(
    repo_path="/path/to/repo",
    base_branch="main",
    head_branch="feature-xyz",
    include_comments=False
)

print(desc.title)      # Suggested PR title
print(desc.summary)    # Change summary
print(desc.changes)    # Dict of added/modified/removed files
print(desc.testing)    # Testing suggestions
print(desc.notes)      # Breaking changes, new deps, etc.
print(desc.stats)      # files_changed, additions, deletions, commits
```

### Output Sections

Generated PRs include:

- **What** — Summary of changes from commit messages
- **Why** — Inferred motivation (from commit bodies or change types)
- **How** — Implementation approach based on files changed
- **Changes** — Files added, modified, removed
- **Testing** — Actionable test suggestions based on changed paths
- **Notes** — Breaking changes, new dependencies, config changes

---

## pr-create

Create PRs with auto-generated title and description. Wraps `pr-describe` and `gh pr create`.

### Usage

```bash
# Create PR for current branch
pr-create

# Target different base branch
pr-create --base develop

# Create as draft
pr-create --draft

# Preview without creating
pr-create --dry-run

# Sync workflow: pull latest, create branch, then work
pr-create --sync --branch feat/new-feature
pr-create --sync --branch fix/bug-123 --base develop
```

### Sync Workflow

The `--sync` flag is useful for starting new work:

1. Stashes uncommitted changes
2. Checks out base branch (main/develop)
3. Pulls latest from origin
4. Creates and checks out new branch
5. Restores stashed changes

```bash
# Start new feature from latest main
pr-create --sync --branch feat/my-feature

# Now work on your feature...
# When ready, commit and run:
pr-create
```

### Requirements

- `gh` CLI authenticated (`gh auth login`)
- Git repository with remote configured

---

## version-bump

Semantic version bumping based on conventional commits. Supports monorepos.

### Usage

```bash
# Auto-detect bump type from commits
version-bump

# Force specific bump
version-bump --major
version-bump --minor
version-bump --patch

# Preview changes
version-bump --dry-run

# Create git tag after bump
version-bump --tag

# Monorepo: specify subdirectory
version-bump --path backend
version-bump --path frontend

# Sync all version files in monorepo
version-bump --sync
version-bump --sync --tag
```

### Bump Type Detection

Analyzes commits since last tag:

| Commit Pattern | Bump Type |
|----------------|-----------|
| `feat:` or `feat(scope):` | minor |
| `BREAKING CHANGE` or `type!:` | major |
| Everything else | patch |

### Supported Files

- `pyproject.toml` — `version = "x.y.z"`
- `package.json` — `"version": "x.y.z"`
- `VERSION` — Plain version string

### Monorepo Support

Automatically detects common monorepo structures:

```
repo/
├── backend/pyproject.toml    # Detected
├── frontend/package.json     # Detected
├── packages/*/package.json   # Detected
└── pyproject.toml            # Root (checked first)
```

Use `--sync` to update all version files to the same version.

---

## repo-scanner

Scan repositories for health metrics. Powers the dashboard's repository panel.

### Usage

```bash
# Scan current directory
repo-scanner

# Output formats
repo-scanner --format text      # Human readable (default)
repo-scanner --format json      # JSON output
repo-scanner --format markdown  # Markdown report

# Scan specific path
repo-scanner --path /path/to/repo

# Save results to file
repo-scanner --save

# Skip docstring TODOs (focus on actionable items)
repo-scanner --skip-docstrings
```

### Metrics Collected

- **TODO counts** — Categorized by type (TODO, FIXME, HACK, XXX)
- **Test counts** — Number of test files found
- **Open PRs** — Via `gh pr list` (requires GitHub CLI)
- **Last commit** — Time since last commit
- **CI status** — Latest workflow status

### Configuration

Config file: `~/.config/openclaw-dash/tools.yaml`

```yaml
repos:
  - my-project
  - another-repo

repo_base: ~/repos      # Base directory for repos
github_org: my-org      # GitHub org for PR checks

repo-scanner:
  skip_docstrings: false
  output_format: text
  include_test_counts: true
  git_timeout: 30
```

---

## smart-todo-scanner

Context-aware TODO scanner that distinguishes documentation notes from actionable work items.

### Usage

```bash
# Scan current directory
smart-todo-scanner

# Scan specific path
smart-todo-scanner /path/to/project

# Output formats
smart-todo-scanner --format text      # Human readable
smart-todo-scanner --format json      # JSON output
smart-todo-scanner --format markdown  # Markdown report

# Filter by category
smart-todo-scanner --category COMMENT   # Only code comments
smart-todo-scanner --category INLINE    # Only inline TODOs

# Exclude docstrings (focus on actionable items)
smart-todo-scanner --no-docstrings

# Filter by priority
smart-todo-scanner --min-priority HIGH
```

### TODO Categories

| Category | Description | Priority |
|----------|-------------|----------|
| `INLINE` | TODO inline with code | HIGH |
| `COMMENT` | In code comments | MEDIUM |
| `DOCSTRING` | In docstrings (often notes) | LOW |

### Patterns Detected

- `TODO` — Standard todo marker
- `FIXME` — Needs fixing
- `HACK` — Temporary workaround
- `XXX` — Attention needed

### Configuration

```yaml
smart-todo-scanner:
  show_docstrings: true
  output_format: text
  min_priority: LOW
  patterns:
    - TODO
    - FIXME
    - HACK
```

---

## dep-shepherd

Dependency audit and update tool. Scans for vulnerabilities and outdated packages, creates PRs for updates.

### Usage

```bash
# Scan all configured repos
dep-shepherd

# Output formats
dep-shepherd --json              # JSON output
dep-shepherd --report            # Detailed report
dep-shepherd --digest            # Weekly digest summary

# Scan specific repo
dep-shepherd --repo my-project

# Create update PRs
dep-shepherd --update
dep-shepherd --update --dry-run  # Preview without creating
```

### Audit Sources

**Python:**
- `pip-audit` — PyPI vulnerability database
- `safety` — Safety DB (requires account for full access)
- `pip list --outdated` — Version checks

**JavaScript:**
- `npm audit` — npm advisory database
- `npm outdated` — Version checks

### PR Creation

When using `--update`:

1. Creates one branch per dependency update
2. Runs tests before committing
3. Skips if tests fail (clean rollback)
4. Prioritizes security updates
5. Uses `pr-describe` for PR body generation

### Configuration

Edit the `REPOS` list in the script or use `--repo` flag:

```python
REPOS = ["my-project", "another-repo"]
REPO_BASE = Path.home() / "repos"
```

### Digest Output

Weekly digest includes:
- Overall health score (🟢 Excellent → 🔴 Critical)
- Critical/high vulnerability summary
- Per-repo status
- Action items

---

## audit

Security scanner for Python and JavaScript projects. Checks for vulnerabilities, hardcoded secrets, and dangerous code patterns.

### Usage

```bash
# Audit current directory
audit

# Audit specific repo
audit --repo my-project
audit --path /path/to/repo

# Audit all configured repos
audit --all

# Output options
audit --verbose              # Show all findings
audit --json                 # JSON output

# Selective scanning
audit --no-deps              # Skip dependency checks
audit --no-code              # Skip code scanning
```

### Checks Performed

**Dependency Vulnerabilities:**
- `pip-audit` for Python packages
- `npm audit` for JavaScript packages

**Hardcoded Secrets:**
- API keys and tokens
- Passwords and secrets
- AWS access keys
- GitHub tokens
- OpenAI API keys

**Dangerous Patterns:**
- `eval()` and `exec()` usage
- `pickle.load()` (insecure deserialization)
- `subprocess` with `shell=True`
- `os.system()` calls
- `yaml.load()` without safe loader

### Severity Levels

| Level | Description |
|-------|-------------|
| Critical | Hardcoded secrets, critical CVEs |
| High | High-severity vulnerabilities |
| Medium | Dangerous code patterns |
| Low | Minor issues |

### Example Output

```
## Security Audit: my-project

**Total issues:** 3
- Critical: 1
- High: 0
- Medium: 2
- Low: 0

### Secret
- **src/config.py:42** - API key

### Dangerous Pattern
- **src/utils.py:15** - eval() usage
- **src/loader.py:28** - pickle usage (insecure deserialization)
```

---

## Dashboard Integration

All tools integrate with the openclaw-dash TUI:

| Panel | Data Source |
|-------|-------------|
| Repository Health | `repo-scanner` |
| Security Audit | `audit` |
| Activity Log | `pr-tracker` (internal) |
| Alerts | `dep-shepherd`, `audit` |

### Refresh Behavior

- Tools are called on dashboard startup
- Manual refresh with `r` key
- Auto-refresh based on `refresh_interval` config (default: 30s)

### Caching

Results are cached to reduce API calls:
- Gateway status: 10s
- Repository scans: 60s
- Security audits: 300s

---

## Common Patterns

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Security Audit
  run: |
    pip install openclaw-dash
    openclaw-dash security --json > audit.json
    
- name: Check for Critical Issues
  run: |
    if jq -e '.summary.critical > 0' audit.json; then
      echo "Critical security issues found!"
      exit 1
    fi
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run security audit on staged Python files
openclaw-dash security --no-deps --json | jq -e '.summary.critical == 0' || {
    echo "Security issues detected. Please fix before committing."
    exit 1
}
```

### Weekly Digest Cron

```bash
# Run weekly dependency digest
0 9 * * 1 cd ~/repos && dep-shepherd --digest | mail -s "Dep Digest" team@example.com
```

---

## Requirements

### Python Tools

```bash
pip install openclaw-dash

# Optional for full functionality:
pip install pip-audit safety
```

### External Dependencies

| Tool | Required For |
|------|--------------|
| `gh` | PR creation, GitHub API |
| `git` | All repository operations |
| `npm` | JavaScript dependency scanning |
| `pip-audit` | Python vulnerability scanning |
| `safety` | Additional Python security checks |

### Verification

```bash
# Check tool availability
which gh git npm pip-audit safety

# Verify gh authentication
gh auth status
```
