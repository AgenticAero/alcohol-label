# Alcohol Label Verification

A Python prototype that helps a reviewer compare alcohol label images with expected application values and identify discrepancies, missing evidence and checks that need human review.

**Status:** AL-8 extraction is implemented locally with offline tests. Live extraction accuracy, comparison behavior and hosted performance remain unevaluated.

**Deployed application:** Pending deployment.

## Project overview

The intended workflow is:

1. Enter the expected application values.
2. Upload one or two label images for the same application.
3. Select **Verify**.
4. Review expected versus observed values, check outcomes, explanations and source evidence.

OCR or vision-based extraction will capture observations from the images. Separate Python comparison and rule functions will evaluate those observations. Ambiguous, unsupported or incomplete checks must remain visible and cannot produce an all-clear result. The reviewer retains responsibility for the final decision.

The goal is a working, deployed prototype within three working days, with reproducible setup and documented correctness and performance evidence.

## Prototype scope

### Planned core

- One application per review, with manually entered expected values.
- English-language U.S. distilled-spirit labels, supplied as one or two clear JPEG/PNG images.
- Comparisons for brand, class/type, alcohol content, net contents, producer/bottler name and address, and country of origin for imports.
- Separate checks for warning wording, uppercase heading and supported font-weight assessment.
- Explained results with source evidence, explicit uncertainty and recoverable input/processing errors.
- A deployed URL, focused tests and measured evaluation results.

The proposed performance target is **p95 Verify-to-visible-result at or below five seconds** for the supported single-application profile. This target has not been measured or achieved. Measurement conditions and results will be recorded in [Evaluation](docs/evaluation.md).

### Limitations and deferred work

- Wine/beer-specific rules, advanced correction of glare/blur/perspective and durable processing of 200–300 applications are outside the core commitment.
- A batch of up to five applications is optional stretch work, only after the core is ready.
- Warning font-weight automation remains unproven. Unsupported or ambiguous style checks will require explicit visual review; that fallback does not count as automated verification.
- Arbitrary images cannot establish physical type size or complete container-wide placement.
- This is a standalone reviewer aid with a limited set of checks, not a comprehensive regulatory compliance certification or a COLA integration.

See [Engineering plan](docs/engineering-plan.md) for authoritative scope, assumptions and technical decisions.

## Technology

Python and Poetry are the selected runtime and dependency-management foundation. The UI framework, extraction provider and hosting path will be confirmed through a bounded feasibility experiment.

| Item | Status |
| --- | --- |
| Supported Python version | 3.11 (verified 3.11.11 via `poetry run python --version`); `pyproject.toml` allows `>=3.11,<4.0` |
| Poetry version | 2.2.1 (verified with `poetry --version`) |
| UI framework | Streamlit |
| Extraction provider/model | OpenAI Responses API; `OPENAI_MODEL` defaults to `gpt-6-luna` |
| Hosting platform | Pending selection |
| Native dependencies and required network endpoints | Pending confirmation |

Actual tools and AI assistance are documented in [Tool use](docs/tool-use.md).

## Setup

**Partly verified.** Commands marked verified were run in the existing local environment on 2026-10-22; a fully clean-environment run is still pending.

| Step | Instructions |
| --- | --- |
| Obtain the source | `git clone https://github.com/AgenticAero/alcohol-label.git && cd alcohol-label` |
| Install prerequisites | Python 3.11 and Poetry 2.2.x. No native dependencies are needed so far. |
| Install dependencies | `poetry install` (includes the `dev` group: pytest, Ruff, pre-commit, commitizen). Verified as a dry run against the existing environment. |
| Configure extraction | Set `OPENAI_API_KEY` and `OPENAI_MODEL` in the environment or in a Git-ignored `.env` based on [`.env.example`](.env.example). Optional settings: `OPENAI_BASE_URL` and `OPENAI_REASONING_EFFORT` (default `low`). The app sends uploaded label images to the configured provider over HTTPS; expected application values are not sent. |
| Confirm the environment | `poetry run python -c "import sys, alcohol_label; print(sys.version.split()[0], alcohol_label.__file__)"` prints `3.11.11` and the `src/alcohol_label` path (verified). |

Keep credentials outside version control. Document which image data is sent to an external service, if applicable, and how uploaded data is retained or cleaned up.

## Run locally

**Startup command:**

    poetry run streamlit run src/alcohol_label/app.py

**Local URL and expected startup behavior:** Streamlit serves http://localhost:8501. The page shows the expected-value form, an image upload (one or two JPEG/PNG files), **Verify** and **Clear form**. Verify sends each supplied image to the configured extraction provider and shows raw observed fields, their state and source image ID. Verification checks remain not evaluated until comparison is implemented; extraction alone is not a pass. If provider settings are missing or a request fails, the app shows a processing error and leaves checks unresolved.

**Sample review:** Four starter scenarios with expected application values,
expected outcomes and provenance are in
[`tests/fixtures/manifest.json`](tests/fixtures/manifest.json):
a clear match (`S01`), a case-only brand variation (`S02`),
an ABV mismatch (`S03`) and a changed warning word (`S04`).
They use `tests/fixtures/labels/starter-clear.png` and
`tests/fixtures/labels/starter-warning-changed.png`.
Annotations are pending developer review.

**Regenerating starter images (optional):** The committed PNGs are the
authoritative fixtures. Using them does not require DejaVu fonts.

Regeneration requires Pillow in the Poetry environment and these font files:
`DejaVuSans.ttf`, `DejaVuSans-Bold.ttf`, `DejaVuSerif.ttf` and
`DejaVuSerif-Bold.ttf`.

The script defaults to `/usr/share/fonts/truetype/dejavu`:

    poetry run python tests/fixtures/render_starter_labels.py

If the fonts are installed elsewhere, supply their directory:

    poetry run python tests/fixtures/render_starter_labels.py --font-dir "/path/to/fonts"

Rendering can vary with font versions, Pillow and the rendering environment.
After regeneration, visually inspect both images and confirm that they match
their annotations and differ only in the intended warning word. Update the
manifest hashes only after accepting any changes; investigate unexpected
differences before committing.

## Tests and code checks

| Check | Verified command | Current evidence |
| --- | --- | --- |
| Unit and adapter tests | `poetry run pytest` | 126 passed (offline; includes AL-8 parsing, aggregation and error cases) |
| Formatting/linting | `poetry run ruff check .` and `poetry run ruff format --check .` | Both pass |
| Intake form, manual browser check (AL-44) | `poetry run streamlit run src/alcohol_label/app.py` | Passed 2026-10-23 locally: valid single image, two images, missing values, imported product without country, Clear form |
| Live extraction evaluation | `poetry run python -c '...'` | Single-image and two-image adapter smoke calls succeeded; one two-image run took 14.09 s, so the five-second target is not demonstrated |
| Hosted performance evaluation | TODO | Not run |

Keep tests that require live credentials separate from offline rule/parsing tests. Passing mocked tests does not establish extraction accuracy. See [Evaluation](docs/evaluation.md) for planned scenarios, methods, actual results and known failures.

## Deployment

| Item | Value |
| --- | --- |
| Application URL | Pending deployment |
| Evaluator access instructions | Pending confirmation |
| Deployed commit/release | Not recorded |
| Fresh-session access check | Not performed |

Record deployment configuration and any cold-start or availability limitations once the hosting path is selected. Verify that the evaluator can access both the application and source repository.

## Documentation and delivery tracking

| Location | Purpose |
| --- | --- |
| [Engineering plan](docs/engineering-plan.md) | Scope, requirements, assumptions, architecture and technical decisions. |
| [Tool use](docs/tool-use.md) | Tools and AI assistance actually used, their purpose and how outputs were checked. |
| [Evaluation](docs/evaluation.md) | Test data, methods, measured results, known failures and limitations. |
| Jira project — link pending | Sprints, epics, stories, tasks, acceptance criteria, dependencies and status. |

Maintain detailed work tracking in Jira and measured evidence in the evaluation document. Update this README as commands and features are verified so it describes the submitted application accurately.
