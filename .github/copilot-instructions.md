# Repository guidance for Copilot

- This is a Python/Poetry alcohol-label verification prototype. Inspect `pyproject.toml`, the existing package layout, and any repository instructions before editing. Use the project's Python environment through `poetry run`.
- Read `README.md` for setup and the current implementation status; `docs/engineering-plan.md` for scope, assumptions and architecture; `docs/evaluation.md` for evaluation methods and evidence; and `docs/tool-use.md` for tools and AI usage. These paths are relative to the repository root.
- Jira owns the backlog and acceptance criteria. Use the work item supplied in the chat as the current task. Implement a small, reviewable change and preserve unrelated work.
- The planned core is one distilled-spirit application with manual expected values and one or two label images. A second image is optional. Confirm current scope in the engineering plan before extending it.
- Keep expected application values separate from image observations. Preserve raw text, evidence references, uncertainty and conflicting observations. Keep processing failures separate from extraction states and check outcomes. Unresolved checks must not become successful verification.
- Follow the existing naming and package conventions. Prefer standard-library types and small modules; add a dependency only when the current task requires it.
- Document meaningful contract and architecture decisions in the existing engineering plan.  Avoid new planning documents or copies of the Jira backlog.
- Run checks appropriate to the change and report the actual commands and results. Add focused tests for project-specific behavior or contract regressions when warranted; avoid tests that merely repeat standard-library behavior. Mark skipped or blocked checks explicitly. Distinguish schema checks from live extraction and hosted performance evaluation.
- Propose Conventional Commit messages with the Jira key. Summarize changed files, acceptance-criteria coverage and remaining uncertainty. Commit and push only when requested.

## Python verification

- Use pytest for automated tests and Ruff for linting and formatting.
- Run commands through Poetry:
  - `poetry run pytest`
  - `poetry run ruff check .`
  - `poetry run ruff format --check .`
- During focused development, run checks against the affected files/tests.
  Before completing a change, run the relevant repository checks.
- Add tests for meaningful application behavior, validation rules and failure
  paths. Avoid tests that merely repeat Python standard-library behavior.
- Report the commands actually run and their results. Explicitly identify
  checks that were skipped, blocked or collected no tests.
- Review formatting changes before including them; avoid unrelated rewrites.