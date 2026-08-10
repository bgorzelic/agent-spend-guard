# agent-spend-guard

## What this is

`agent-spend-guard` is a dependency-free Python 3.11+ library and CLI that classifies agent tool calls as `ALLOW`, `FLAG`, or `STOP`, refuses unknown tools by default, and can append redacted JSONL audit records. Its policy is loaded from `spend-guard.toml`. (Sources: `README.md`, `pyproject.toml`, and `src/spend_guard/`, inspected 2026-08-05.)

## Setup / install

From a clone of the repository, use either documented installation command:

```sh
pip install .
```

or:

```sh
uv pip install -e .
```

The package requires Python 3.11 or newer. It exposes the `spend-guard` command; `spend-guard explain` verifies the installation and displays the active policy discovered from the working directory upward. (Sources: `README.md` and `pyproject.toml`, inspected 2026-08-05.)

## Build / test / lint

- Test: `pytest`
- Build: no standalone build command is documented. Packaging uses Hatchling.
- Lint: no lint command is documented. Ruff configuration exists in `pyproject.toml`, but invocation is not yet established.

Pytest is configured to collect from `tests/`. (Sources: `README.md` and `pyproject.toml`, inspected 2026-08-05.)

## Code style / conventions

- Use the `src/spend_guard/` package layout and keep tests under `tests/`.
- Target Python 3.11 and a 100-character line length, as configured for Ruff.
- Existing modules use `from __future__ import annotations`, type annotations, module and public API docstrings, standard-library imports, and explicit exceptions for policy/configuration errors.
- Keep the core classification path deterministic and fail closed: unknown tools classify as `STOP`. Preserve key-based redaction for audit data.

These conventions were observed in `pyproject.toml`, `src/spend_guard/`, and `tests/` on 2026-08-05; no separate contributing or style guide was present at the repository top level.

## Working with multiple agents here

This repository can be worked on by multiple parallel Claude Code or Codex agents launched through this machine's `launch-agents` tool. Each agent receives its own git worktree automatically; do not create a manual branch merely to support that orchestration.

For a multi-agent task, check the shared coordination database for file claims before editing any file another agent might be touching. Claim work through the installed orchestration workflow, keep changes within the assigned scope, and coordinate before modifying an already-claimed file.

Use conventional commit messages. The observed history uses forms including `feat:` and `docs(readme):` (source: repository git log, inspected 2026-08-05).

Never commit secrets, API keys, credentials, or sensitive audit output. Confirm ignore coverage before creating any such local file: as inspected on 2026-08-05, `.gitignore` covers virtual environments, Python caches, package build output, and `var/`, but does **not** list `.env` or credential-file patterns. Do not assume those files are safe from Git tracking.
