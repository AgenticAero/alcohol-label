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

Pillow 13.0.0 is a dev-group dependency used only by the fixture rendering script and manifest tests. Add Streamlit, Pydantic, an OCR/vision provider, and hosting only when actually used. Proposed tools are documented in the engineering plan.

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

### 2026-10-22 — AL-5 AC4 starter fixtures and manifest

- **Tool / version:** GitHub Copilot (VS Code agent); exact model/version not recorded. Pillow 13.0.0.
- **Purpose:** Create four starter fixtures with expected values, expected outcomes and provenance.
- **Inputs:** AL-5 acceptance criterion 4, the engineering plan and evaluation docs, the AL-28 serialization format, and source URLs supplied by the developer for the existing images. The developer chose synthetic rendering, a JSON manifest and an offline manifest test.
- **Output used:** `tests/fixtures/render_starter_labels.py`, `labels/starter-clear.png`, `labels/starter-warning-changed.png`, `tests/fixtures/manifest.json`, `tests/test_fixtures.py`, and the README, evaluation and engineering-plan notes. `poetry add --group dev pillow` changed `pyproject.toml` and `poetry.lock`.
- **Human review / changes:** The assistant viewed both rendered PNGs and annotated what is visible: a bold uppercase heading, a regular-weight body, and the single changed word. Developer review of the annotations is pending. Provenance for the reference images is as reported by the developer; permission is not confirmed.
- **Checks performed:** Rendering twice gave identical SHA-256 hashes; `poetry run pytest` (95 passed); `poetry run ruff check .` (passed); `poetry run ruff format --check .` (passed); `git diff --check` (clean).
- **Pending checks / limitations:** Offline schema and manifest checks only; no extraction was run on these images, so they say nothing about extraction accuracy or boldness detection. Rendering depends on the installed DejaVu fonts, so the committed PNGs are the source of truth. The reference images are unannotated and their permitted use is unconfirmed.

### 2026-10-23 — AL-6 extraction and hosting feasibility

- **Tool / version:** OpenAI Responses API, model `gpt-6-luna`; Azure App Service Linux B1 (Python 3.11, `centralus`), Azure CLI 2.83.0; GitHub Copilot (VS Code agent), exact model/version not recorded.
- **Purpose:** Choose an extraction path and hosting target and measure accuracy and latency on the starter fixtures.
- **Inputs:** AL-6 and sub-tasks AL-29 to AL-32, the starter fixtures and manifest, and the developer's API key and Azure subscription. The extraction prompt and schema are in `scripts/al6_extraction_spike.py`.
- **Output used:** The spike script, the `OPENAI_*` variable names in `.env.example`, a throwaway Streamlit check app deployed to `alcohol-label-staging`, and the decision entry in the engineering plan.
- **Human review / changes:** The developer supplied the key and model, chose App Service B1 and Streamlit, ran extra spike attempts, and confirmed the hosted call result in a browser.
- **Checks performed:** Spike runs recorded in [evaluation.md](evaluation.md); `poetry run ruff check scripts` and `ruff format --check scripts` passed; hosted call returned HTTP 200 in 4.13 s.
- **Pending checks / limitations:** Not a live evaluation: few attempts, no held-out images, no negative bold example, no cost measurement. The check app and Azure resources are temporary.

### 2026-10-23 — AL-8 image-only extraction implementation

- **Tool / version:** GitHub Copilot (VS Code agent); exact model/version not recorded. OpenAI Responses API adapter implemented from the AL-6 spike pattern; no provider SDK dependency added.
- **Purpose:** Extract structured, image-linked observations for one application's supplied label images while preserving raw text, uncertainty, conflicts and processing failures.
- **Inputs:** Live AL-8 acceptance criteria, AL-6 provider decision and spike, existing schemas/intake/review path, starter fixture manifest, and repository instructions.
- **Output used:** `src/alcohol_label/extraction.py`, Verify integration and pending-review behavior, equal-observation schema update, concurrent per-image extraction (maximum two workers), focused extraction/review/schema tests, and setup/architecture/evaluation documentation.
- **Human review / changes:** User confirmed the AL-6 merged PR indicator referred to AL-7. The implementation does not send expected application values to the provider and does not implement comparisons or visual-style checks.
- **Checks performed:** `poetry run pytest` (126 passed, 0 failed, 0 skipped); `poetry run ruff check .` (passed); `poetry run ruff format --check .` (passed); live single- and two-image adapter smoke calls. The two-image run completed in 14.09 seconds without errors and preserved the warning conflict. A blank `OPENAI_BASE_URL` fallback bug was fixed and covered offline; malformed-response-envelope tests verify invalid output items and content parts map to controlled provider errors.
- **Pending checks / limitations:** The 14.09-second two-image smoke exceeds the five-second target and is one run, not a p95 evaluation. Broader accuracy and hosted performance evaluation remain pending. Rotate the local credential if it is the same value surfaced in the earlier diagnostic output.

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
