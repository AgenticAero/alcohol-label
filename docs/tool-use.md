# Tools and AI assistance

This file records tools actually used, their purpose, and how their outputs were checked. Architecture and selection rationale belong in [engineering-plan.md](engineering-plan.md); measured application results belong in [evaluation.md](evaluation.md). Jira tracks implementation work.

Record meaningful uses and decisions, not every command or chat message. Group related work into one entry. Label checks as pending until performed, and link to commits, tests or evaluation results when available. Do not include credentials, private data or full conversation transcripts.

## Development tools

The project setup below is based on developer-reported use; versions and setup checks still need to be recorded.

| Tool | Purpose | Version / configuration | Verification or evidence |
| --- | --- | --- | --- |
| Python | Application runtime | Python 3.11 indicated by the local environment; exact version pending | Pending: record `poetry run python --version` and confirm the project interpreter. |
| Poetry | Dependency and virtual environment management | Pending: `poetry --version` | Pending: verify installation from the committed dependency files in a clean environment. |
| VS Code | Editing and local development | Pending: version and relevant extensions | Pending: confirm the selected interpreter belongs to this project's virtual environment. |
| Git / GitHub | Version control and remote repository | Pending: repository URL | Pending: confirm the intended remote and pushed commit. |
| Jira | Sprint and backlog tracking | Pending: project link | Pending: check imported hierarchy and work items against the intended backlog. |

Add Streamlit, Pydantic, Pillow, an OCR/vision provider, pytest, Ruff and hosting only when actually used. Proposed tools are documented in the engineering plan.

## AI assistance

### Assignment analysis and planning — October 21–22, 2026

- **Tool:** ChatGPT; exact model/version not recorded.
- **Purpose:** Interpret the assignment, propose a feasible three-day scope, decompose work for Jira, and consolidate engineering documentation.
- **Inputs:** Assignment instructions, developer constraints, and the supplied planning documents.
- **Outputs used:** Draft engineering approach, scope and assumptions, sprint/backlog package, and consolidated engineering plan. These are planning artifacts; implementation remains to be verified.
- **Checks performed:** The assistant compared the supplied planning documents during consolidation and reviewed the resulting diff for conflicting scope and duplicate planning content. The developer reviewed the documentation structure and requested consolidation.
- **Checks still needed:** Developer review of the final scope and assumptions against the assignment, confirmation of Jira contents, and validation of technical choices through implementation and measurement.
- **Limitations:** Planning assistance and document checks do not establish application correctness, extraction accuracy, deployment success or five-second performance.

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
