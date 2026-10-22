# Tools and AI assistance

This file records tools actually used, their purpose, and how their outputs were checked. Architecture and selection rationale belong in [engineering-plan.md](engineering-plan.md); measured application results belong in [evaluation.md](evaluation.md). Jira tracks implementation work.

Record meaningful uses and decisions, not every command or chat message. Group related work into one entry. Label checks as pending until performed, and link to commits, tests or evaluation results when available. Do not include credentials, private data or full conversation transcripts.

## Development tools

Versions below were reported by the developer and re-checked on 2026-10-22 with `poetry run python --version`, `poetry --version`, `poetry run pytest --version` and `poetry run ruff --version`. Clean-environment installation is still pending.

| Tool | Purpose | Version / configuration |
| --- | --- | --- |
| Python | Application runtime | Python 3.11.11 .venv/bin/python |
| pytest | test | pytest 9.1.1 |
| Poetry | Dependency and virtual environment management | version 2.2.1 |
| VS Code | Editing and local development | 1.143.0 |
| Git / GitHub | Version control and remote repository | https://github.com/AgenticAero/alcohol-label |
| Jira | Sprint and backlog tracking | https://agentic-team.atlassian.net/jira/software/projects/AL/boards/67/backlog |
| Ruff | lint, format | ruff 0.17.1 |

Add Streamlit, Pydantic, Pillow, an OCR/vision provider, and hosting only when actually used. Proposed tools are documented in the engineering plan.

## AI assistance

### Assignment analysis and planning — October 21–22, 2026

- **Tool:** ChatGPT; exact model/version not recorded.
- **Purpose:** Interpret the assignment, propose a feasible three-day scope, decompose work for Jira, and consolidate engineering documentation.
- **Inputs:** Assignment instructions, developer constraints, and the supplied planning documents.
- **Outputs used:** Draft engineering approach, scope and assumptions, sprint/backlog package, and consolidated engineering plan. These are planning artifacts; implementation remains to be verified.
- **Checks performed:** The assistant compared the supplied planning documents during consolidation and reviewed the resulting diff for conflicting scope and duplicate planning content. The developer reviewed the documentation structure and requested consolidation.
- **Checks still needed:** Developer review of the final scope and assumptions against the assignment, confirmation of Jira contents, and validation of technical choices through implementation and measurement.
- **Limitations:** Planning assistance and document checks do not establish application correctness, extraction accuracy, deployment success or five-second performance.

### 2026-10-22 — AL-23 shared identifiers and states

- **Tool / version:** GitHub Copilot (VS Code agent); model reported as Claude Sonnet 5.5.
- **Purpose:** Implement AL-23 enums and document state meanings.
- **Inputs:** AL-23/AL-5 acceptance criteria, README, engineering plan, `pyproject.toml`.
- **Output used:** `src/alcohol_label/schemas.py`, `tests/test_schemas.py`, Data contracts section of the engineering plan.
- **Human review / changes:** Developer chose separate `producer_name`/`producer_address` and no style fields in `FieldId`; diff pending developer review.
- **Checks performed:** See the commands recorded in the AL-23 completion summary; offline enum and contract tests only.
- **Pending checks / limitations:** No live extraction, UI or performance testing occurred.

### 2026-10-22 — AL-24 application data structure

- **Tool / version:** GitHub Copilot (VS Code agent); exact model/version not recorded.
- **Purpose:** Define the application input record using the AL-23 identifiers.
- **Inputs:** AL-24 and AL-5 retrieved from Jira, shared schemas, and Data contracts section of the engineering plan.
- **Output used:** `ApplicationData`, `Measurement`, `ImageReference`, related enums, focused schema tests, and documented required/conditional inputs.
- **Human review / changes:** An initial draft written before Jira was reachable (FieldId-keyed mapping) was reworked against the actual acceptance criteria: decimal values with explicit units, one or two images, `None` for unsupplied values, import-conditional country of origin.
- **Checks performed:** `poetry run pytest` (16 passed); `poetry run ruff check .` (passed after fixing 5 FURB157 findings); `poetry run ruff format .` (no changes).
- **Pending checks / limitations:** Offline schema checks only; no live extraction, UI or performance testing.

### 2026-10-22 — AL-25 ExtractedField and source evidence

- **Tool / version:** GitHub Copilot (VS Code agent); exact model/version not recorded.
- **Purpose:** Define extraction output records that preserve source, raw text and uncertainty.
- **Inputs:** AL-25 acceptance criteria from Jira, existing schemas, Data contracts section; developer chose record shape, parsed-value types, normalized bounding box and candidates for uncertain fields.
- **Output used:** `Observation`, `ExtractedField`, `EvidenceLocation`, `BoundingBox`, schema tests, Data contracts documentation.
- **Human review / changes:** Diff pending developer review.
- **Checks performed:** `poetry run pytest` (34 passed); `poetry run ruff check .` (passed); `poetry run ruff format --check .` (10 files already formatted); `git diff --check` (clean).
- **Pending checks / limitations:** Offline schema checks only; no live extraction, UI or performance testing.

### 2026-10-22 — AL-26 CheckResult structure

- **Tool / version:** GitHub Copilot (VS Code agent); exact model/version not recorded.
- **Purpose:** Define the check outcome record and document schema versus comparison-logic invariants.
- **Inputs:** AL-26 acceptance criteria from Jira, existing schemas, Data contracts section; developer chose index-based evidence references, value types, field rules, explanation and discrepancy-evidence requirements.
- **Output used:** `EvidenceRef`, `CheckResult`, schema tests, Data contracts documentation. Also fixed one existing Ruff TRY004 finding and one unformatted test line left by the AL-25 follow-up so repository checks pass.
- **Human review / changes:** Diff pending developer review.
- **Checks performed:** `poetry run pytest` (54 passed); `poetry run ruff check .` (passed); `poetry run ruff format --check .` (10 files already formatted); `git diff --check` (clean).
- **Pending checks / limitations:** No live extraction, UI or performance testing; evidence references are not resolved against real observations or images yet.

### 2026-10-23 — AL-27 processing errors and review response

- **Tool / version:** GitHub Copilot (VS Code agent); exact model/version not recorded.
- **Purpose:** Define processing errors and a review response that cannot look all-clear when incomplete or failed.
- **Inputs:** AL-27 acceptance criteria from Jira, existing schemas, Data contracts section; developer chose stages, codes, derived status and all-clear rules.
- **Output used:** `ProcessingStage`, `ErrorCode`, `ProcessingError`, `ReviewStatus`, `ReviewResponse`, schema tests, Data contracts documentation. Also fixed an indentation error in `EvidenceRef` and a misplaced bool-index test case on `main`, both of which blocked test collection.
- **Human review / changes:** Diff pending developer review.
- **Checks performed:** `poetry run pytest` (64 passed); `poetry run ruff check .` (passed); `poetry run ruff format --check .` (10 files already formatted); `git diff --check` (clean).
- **Pending checks / limitations:** Offline schema checks only; no live extraction, UI or performance testing. Message safety is the producer's responsibility.

### 2026-10-22 — AL-28 contract examples, serialization and boundary validation

- **Tool / version:** GitHub Copilot (VS Code agent); exact model/version not recorded.
- **Purpose:** Demonstrate the contracts by example, add JSON round-tripping and validate evidence references at the response boundary.
- **Inputs:** AL-28 acceptance criteria from Jira, existing schemas and Data contracts section. The developer was unavailable for design questions, so the assistant chose stdlib serialization, a raising boundary validator and Python example builders.
- **Output used:** `*_to_dict` / `*_from_dict`, `validate_review_evidence`, five contract examples with round-trip, invalid-combination and boundary tests, Data contracts documentation.
- **Human review / changes:** Diff pending developer review; the unattended design choices need confirming.
- **Checks performed:** `poetry run pytest` (82 passed); `poetry run ruff check .` (passed); `poetry run ruff format --check .` (10 files already formatted); `git diff --check` (clean).
- **Pending checks / limitations:** Offline schema checks only; no live extraction, UI or performance testing.

### 2026-10-22 — AL-5 AC3 setup verification and `.env.example`

- **Tool / version:** GitHub Copilot (VS Code agent); exact model/version not recorded.
- **Purpose:** Verify recorded tool versions and local commands, add a secret-free `.env.example`, and replace verified README setup TODOs.
- **Inputs:** AL-5 acceptance criterion 3, README, the developer's version table above.
- **Output used:** `.env.example` (comments only, no variables, since nothing reads the environment yet), README setup and checks rows. Versions matched the table: Python 3.11.11, Poetry 2.2.1, pytest 9.1.1, Ruff 0.17.1.
- **Human review / changes:** Diff pending developer review.
- **Checks performed:** `poetry install --dry-run` (resolved; packages already installed); `poetry run pytest -q` (82 passed); `poetry run ruff check .` (passed); `poetry run ruff format --check .` (10 files already formatted); `git check-ignore .env` (ignored).
- **Pending checks / limitations:** Not run from a clean checkout or fresh virtual environment; no live extraction, UI or performance testing.

## Entry template

Copy this section for a meaningful use of AI or another tool. Remove unused fields.

### YYYY-MM-DD — Short description

- **Tool / version:**
- **Purpose:** What problem did the tool help solve?
- **Inputs:** Relevant files, requirements, sample data or prompt summary.
- **Output used:** Code, configuration, documentation, extracted data or test fixtures; link to the affected files/commit.
- **Human review / changes:** What was inspected, corrected, rejected or accepted?
- **Checks performed:** Actual commands, test cases or manual checks, with outcomes and evidence links.
- **Pending checks / limitations:** What remains uncertain or unverified?

For AI-generated code, record the relevant tests and review rather than treating successful generation as validation. For generated label fixtures, inspect and annotate the actual image; the prompt is not ground truth. For runtime OCR/vision, record provider/model and prompt/schema identifiers, then link to live extraction evaluation separately from mocked tests.
