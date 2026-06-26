---
name: git-workflow
description: >-
  Enforces Git conventions for this Python data science and AI agent project.
  Use when the user mentions commit, git, push, branch, version control, save
  my work, checkpoint work, merge, or asks to preserve or version their changes.
---

# Git Workflow — Python Data Science & Agentic Systems

This project treats version control as part of shipping production-ready agent code. Follow these conventions exactly — do not fall back to generic Git advice.

## When to Commit

Commit **proactively**, not only when a feature is finished:

- **End of every working session** — always commit before stopping, even if work is in progress
- **Before switching tasks or components** — e.g., moving from `cleaning-agent` to `mcp-server`
- **After each logical unit of work** — one agent capability, one bug fix, one refactor

If the user is wrapping up, switching context, or says "save my work", run the commit workflow below without being asked twice.

## Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`

### Types

| Type | Use for |
|------|---------|
| `feat` | New agent functionality, tools, or capabilities |
| `fix` | Bug fixes |
| `refactor` | Restructuring without behavior change |
| `docs` | README, docstrings, comments |
| `chore` | Config, dependencies, `.gitignore`, CI |

### Scope

Reference the **component** being changed — agent name, service, or config area:

- `feat(mcp-server): add query tool`
- `fix(cleaning-agent): handle empty dataframe edge case`
- `chore(env): add new API key to .env.example`
- `refactor(orchestrator): extract tool routing logic`

Common scopes in this project: agent names (`cleaning-agent`, `slackbot`), infrastructure (`mcp-server`, `orchestrator`), config (`env`, `deps`), notebooks (`eda`).

### Description rules

- Lowercase
- Imperative mood ("add", "fix", "remove" — not "added" or "adds")
- Under 72 characters
- **No "and"** — if you need "and", split into two commits

## What to Never Commit

Reject or unstaged before committing:

| Category | Examples |
|----------|----------|
| Secrets | `.env`, API keys, database credentials, tokens |
| Data | Large datasets, CSV/Parquet dumps, model weights — add to `.gitignore` |
| Python artifacts | `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `env/` |
| Notebook noise | `.ipynb_checkpoints/` |

If a secret was accidentally staged, **do not commit**. Remove it from the index, verify `.gitignore`, and warn the user to rotate the credential.

Ensure `.gitignore` covers at minimum:

```
.env
*.pyc
__pycache__/
.venv/
venv/
.ipynb_checkpoints/
data/
*.parquet
*.csv
```

Adjust paths to match the project layout; never commit raw data that belongs in `data/` or external storage.

## Pre-Commit Checklist

Run this sequence before every commit:

```
Pre-Commit:
- [ ] Run the project's main script or entry point (e.g., python main.py, python -m agents)
- [ ] git diff — review every staged and unstaged change
- [ ] Confirm no secrets, credentials, or large data files in staged files
- [ ] Commit message follows type(scope): description
- [ ] One logical change — split if message needs "and"
```

If no entry point exists yet, run relevant tests or `python -m py_compile` on changed modules. The goal is: **nothing broken gets committed**.

## Branch Conventions

| Rule | Detail |
|------|--------|
| Feature branches | All new work branches from `main` |
| Naming | `feature/descriptive-name` |
| Examples | `feature/data-cleaning-agent`, `feature/slackbot-integration` |
| Main branch | Keep stable — never commit broken code directly to `main` |
| Cleanup | Delete feature branches after merging |

### Starting new work

```bash
git checkout main
git pull
git checkout -b feature/descriptive-name
```

### Finishing work

```bash
# After PR is merged
git checkout main
git pull
git branch -d feature/descriptive-name
```

Only push or create PRs when the user explicitly asks.

## Commit Workflow

When committing at end of session or before a context switch:

1. **Review** — `git status` and `git diff` (staged + unstaged)
2. **Validate** — run entry point / smoke test
3. **Stage** — `git add` only files that belong in this atomic commit
4. **Scan** — re-check staged diff for secrets and data files
5. **Commit** — conventional message, imperative, under 72 chars
6. **Confirm** — `git status` to verify clean or intentional remaining changes

### Splitting commits

If changes span multiple components or types, split:

```bash
git add path/to/cleaning-agent/
git commit -m "fix(cleaning-agent): handle empty dataframe edge case"

git add path/to/mcp-server/
git commit -m "feat(mcp-server): add query tool"
```

### Good vs bad messages

```
✅ feat(mcp-server): add query tool
✅ fix(cleaning-agent): handle empty dataframe edge case
✅ chore(env): add new API key to .env.example
✅ refactor(orchestrator): extract tool routing logic

❌ updated stuff
❌ fix bug and add new agent
❌ Feat(MCP-Server): Added Query Tool
❌ feat: various improvements to the cleaning agent and mcp server
```

## General Principles

- **Atomic commits** — one logical change per commit; easy to review and revert
- **Clean history** — a readable git log is part of production-ready agent code
- **Commit often** — small, frequent commits beat large end-of-week dumps
- **Main stays green** — feature branches absorb experimentation; `main` always runs

When in doubt: review the diff, run the entry point, write a scoped conventional message, and commit.
