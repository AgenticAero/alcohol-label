# Alcohol Label Verification

A Python prototype that helps a reviewer compare alcohol label images with expected application values and identify discrepancies, missing evidence and checks that need human review.

**Deployed application:** https://alcohol-label-staging.azurewebsites.net

> **Please read before testing the deployed app: it can look slow or stuck, but it is working.**
>
> - **First load can take about a minute or more.** The app runs on Azure App Service and sleeps when idle, and it restarts after every deployment. The first request after that has to start the server (a "cold start"). If the page is blank or still loading, wait and then refresh once. After the first load the page opens quickly.
> - **Each Verify takes several seconds.** The label images are read by an external AI service (the OpenAI API). In the deployed smoke check the OpenAI request alone took 4.68 to 6.45 seconds on four runs (local requests ranged from about 3.5 to 8.5 seconds, with one slower run at about 17 seconds), so a Verify takes at least that long, and a spinner ("Reading text from label images...") shows while it works. Do not click Verify again until the result appears. The five-second target is not met; see [Evaluation](docs/evaluation.md).
> - **Results can differ between runs.** The reading is done by an AI model, so a blurry label may be flagged "needs review" in one run and read in another. The sample labels and what to expect are in [Try it](#try-it-sample-labels-and-what-to-expect).
> - **If you see an error,** the app tells you what happened and what to do. A temporary failure offers a **Retry** button that keeps your entries and images.

**Status:** Jira AL-8 extraction and the Jira AL-9 through Jira AL-15 work are implemented and merged to `main` (pull requests 16 to 19); the deploy workflow succeeded for the AL-14 and AL-15 merges, and the developer confirmed on 2026-10-25 that the AL-12 to AL-14 changes, including the warning boldness checks, work in the deployed app. A fresh-session smoke check of commit `1beb0b8` on 2026-10-25 behaved as expected for six checks (see [Evaluation](docs/evaluation.md)); the OpenAI request took 4.68 to 6.45 s on four runs (Verify-to-result time was not recorded and is longer), so the five-second target is not met. The results screen now shows a summary of discrepancies and unresolved checks, next actions, and a Retry button for retryable failures (Jira AL-14). Warning heading and body font weight are judged visually from the image in the same extraction request; they are validated only on three clear synthetic fixtures. Live extraction accuracy beyond those checks and hosted performance remain unevaluated.

## Project overview

The intended workflow is:

1. Enter the expected application values.
2. Upload one or two label images for the same application.
3. Select **Verify**.
4. Review expected versus observed values, check outcomes, explanations and source evidence.

**How it works.** A vision-capable model (the OpenAI Responses API) reads each uploaded image. It only transcribes what is printed (brand, class/type, alcohol content, net contents, producer, origin and the government warning) and judges whether the warning heading and body look bold. It is never given the expected values and makes no pass or fail decision. Separate, deterministic Python functions then compare those observations with the expected values and with 27 CFR 16.21, and each check ends as match, discrepancy, needs review, not applicable or not evaluated. Ambiguous, unreadable or incomplete evidence stays visible as needs review, and an incomplete review is never reported as all clear. The reviewer retains responsibility for the final decision.

## Prototype scope

### Supported scope

- One application per review, with manually entered expected values.
- English-language U.S. distilled-spirit labels, supplied as one or two clear JPEG/PNG images.
- Comparisons for brand, class/type, alcohol content, net contents, producer/bottler name and address, and country of origin for imports.
- Separate checks for warning wording, uppercase heading and supported font-weight assessment.
- Explained results with source evidence, explicit uncertainty and recoverable input/processing errors. Warning wording and uppercase heading are checked independently against 27 CFR 16.21; heading and body font weight are judged visually from the image, and an unclear or missing judgement is shown as needs review with the original image. Each needs-review check says what to do next, for example upload a clearer image; provider and extraction details are in a collapsed Technical details section.
- A deployed URL, focused tests and measured evaluation results.

The proposed performance target is **p95 Verify-to-visible-result at or below five seconds** for the supported single-application profile. Results so far are in [Evaluation](docs/evaluation.md); the target is not met (see the limitations below).

### Limitations and deferred work

- Wine/beer-specific rules, advanced correction of glare/blur/perspective and durable processing of 200–300 applications are outside the core commitment.
- A batch of up to five applications is optional stretch work, only after the core is ready.
- Warning font-weight automation is validated only on three clear synthetic fixtures. Unclear, missing or disagreeing style judgements require explicit visual review; that fallback does not count as automated verification.
- Arbitrary images cannot establish physical type size or complete container-wide placement.
- This is a standalone reviewer aid with a limited set of checks, not a comprehensive regulatory compliance certification or a COLA integration.
- **Speed:** the five-second target is not met. On the deployed app the OpenAI request alone took 4.68 to 6.45 s on four runs, and Verify-to-result time was not recorded. No p95 was measured, and the hosted correctness and performance evaluation (Jira AL-17) was not run.
- **Correctness evidence is small and synthetic:** automated checks use 30 fictional labels annotated by the developer's assistant (review pending), and live extraction was checked on a few clear and blurred images. There is no real-world or photographed label result, and the two held-out layouts have not yet been run live.
- **Image quality:** heavily blurred or smudged labels are flagged as needs review rather than corrected. EXIF orientation is not corrected and there is no perspective or glare correction. The live model's readings can vary between runs and may differ from the annotated expectations.
- **Error handling (AL-16, partially implemented):** JPEG/PNG uploads are checked for file size, pixel count and corrupt data; extraction has a 60-second request deadline and maps provider timeouts, network blocks, rate limits and malformed responses to explicit errors. The form is retained across retryable failures, and Retry is offered when appropriate. Remaining AL-16 work includes correcting EXIF orientation and fully verifying upload/session cleanup and failure-path behavior. Batch processing (AL-20, AL-21) and CI for pull requests are deferred.

See [Engineering plan](docs/engineering-plan.md) for authoritative scope, assumptions and technical decisions.

## Technology

Python and Poetry are the selected runtime and dependency-management foundation. The UI framework (Streamlit), extraction provider (OpenAI Responses API) and hosting (Azure App Service) were chosen after a bounded feasibility experiment; see [Evaluation](docs/evaluation.md).

| Item | Status |
| --- | --- |
| Supported Python version | 3.11; `pyproject.toml` allows `>=3.11,<4.0` |
| Poetry version | 2.2.1  |
| UI framework | Streamlit |
| Extraction provider/model | OpenAI Responses API. `OPENAI_MODEL` must be set; the app has no built-in default. We used `gpt-6-luna`, the value in `.env.example`. |
| Hosting platform | Azure App Service Linux B1, Python 3.11, Central US |
| Native dependencies and required network endpoints | No native dependencies. The host needs outbound HTTPS to `api.openai.com`. |

Actual tools and AI assistance are documented in [Tool use](docs/tool-use.md).

## Setup

**Verified from a clean checkout on 2026-10-26.** The repository was cloned with `git clone https://github.com/AgenticAero/alcohol-label.git` into an empty directory (commit `b2c81a5`), with Python 3.11.11, Poetry 2.2.1, no `.env` and no `OPENAI_*` variables. `poetry install`, the environment check, `poetry run pytest` (495 passed), `poetry run ruff check .` and `poetry run ruff format --check .` all succeeded, and `poetry run streamlit run src/alcohol_label/app.py` started and answered its health check. Extraction itself needs the settings below and was not exercised by this check.

| Step | Instructions |
| --- | --- |
| Obtain the source | `git clone https://github.com/AgenticAero/alcohol-label.git && cd alcohol-label` |
| Install prerequisites | Python 3.11 and Poetry 2.2.x. No native dependencies are needed. |
| Install dependencies | `poetry install` (includes the `dev` group: pytest, Ruff, pre-commit, commitizen).  |
| Configure extraction | Copy [`.env.example`](.env.example) to a Git-ignored `.env` and add your `OPENAI_API_KEY`, or set the variables in the environment. The example sets `OPENAI_MODEL=gpt-6-luna` and `OPENAI_REASONING_EFFORT=low`; the model has no built-in default, and the app shows a clear "not configured" error if `OPENAI_API_KEY` or `OPENAI_MODEL` is missing. `OPENAI_BASE_URL` is optional and defaults to the OpenAI API; `OPENAI_REASONING_EFFORT` is optional and omitted from the request when unset. The app sends uploaded label images to the configured provider over HTTPS; expected application values are not sent. |
| Confirm the environment | `poetry run python -c "import sys, alcohol_label; print(sys.version.split()[0], alcohol_label.__file__)"` prints `3.11.11` and the `src/alcohol_label` path (verified). |

Keep credentials outside version control.

**Data handling.** Uploaded images are held in memory for the review and sent over HTTPS to the OpenAI Responses API with `store: false`; the expected application values are not sent. The application code does not write uploads to disk and does not log image contents or credentials (checked by searching `src/`). Streamlit keeps uploaded files in the server's memory for the browser session, and no separate cleanup step is implemented. Use synthetic or non-sensitive labels only.

## Run locally

**Startup command:**

    poetry run streamlit run src/alcohol_label/app.py

**Local URL and expected startup behavior:** Streamlit serves http://localhost:8501. The page shows the expected-value form, an image upload (one or two JPEG/PNG files), **Verify** and **Clear form**. Verify sends each supplied image to the configured extraction provider. The results show a summary (Pass or Not a pass, with counts for matched, discrepancy, needs review, not evaluated and not applicable, and the checks named), what to do next, a table with expected value, observed value, status and reason for every check, and the label images with their IDs. The checks are brand, class/type, alcohol content, net contents, producer name and address, country of origin for imports, warning wording, uppercase heading, and warning heading and body font weight. Font weight is judged visually from the image, and physical type size is not checked. Unclear or unreadable evidence is shown as needs review with a next step, such as uploading a clearer image; a retryable provider failure offers a Retry button that keeps the form and images. Extraction alone is never a pass, and an incomplete review is never reported as all clear. If provider settings are missing or a request fails, the app shows a processing error and leaves the checks not evaluated. Provider, model, request latency and the raw observed fields are in a collapsed Technical details section.

## Try it: sample labels and what to expect

All sample labels are synthetic and fictional. They are in [`tests/fixtures/labels/`](tests/fixtures/labels/). The values to type into the form and the expected result for each are in [`tests/fixtures/manifest.json`](tests/fixtures/manifest.json) (each scenario's `application` and `expected_outcomes`) and summarized below.

**To try one:** type the values into the form (any Application ID), upload the image or images listed (two images are the front and back of one label), and click **Verify**. The summary at the top says **Pass** only if every applicable check matches; anything else is **Not a pass** with the checks named.

- **Set A** (used by most scenarios): Brand `OLD TOM`; Class/type `Straight Bourbon Whiskey`; ABV `45.0`; Net contents `750 mL`; Producer `Example Distillery`; Address `Louisville, KY`; not imported.
- **Set B** (imported): Brand `HIGHLAND REEL`; Class/type `Single Malt Scotch Whisky`; ABV `43.0`; Net contents `700 mL`; Producer `Example Imports`; Address `New York, NY`; Imported on; Country `Scotland`.

| Scenario | Image(s) | Enter these values | Expected result |
| --- | --- | --- | --- |
| `S01-clear-match` | [starter-clear.png](tests/fixtures/labels/starter-clear.png) | Set A | Pass: all applicable checks match |
| `S02-brand-case-only` | [starter-clear.png](tests/fixtures/labels/starter-clear.png) | Set A with Brand: Old Tom | Pass: all applicable checks match |
| `S03-abv-mismatch` | [starter-clear.png](tests/fixtures/labels/starter-clear.png) | Set A with ABV: 40.0 | Not a pass: alcohol content: discrepancy |
| `S04-warning-text-changed` | [starter-warning-changed.png](tests/fixtures/labels/starter-warning-changed.png) | Set A | Not a pass: warning wording: discrepancy |
| `S05-import-origin-prefix` | [import-product-of.png](tests/fixtures/labels/import-product-of.png) | Set B | Pass: all applicable checks match |
| `S06-import-origin-differs` | [import-product-of.png](tests/fixtures/labels/import-product-of.png) | Set B with Country: Ireland | Not a pass: country of origin: discrepancy |
| `S07-import-origin-not-observed` | [import-no-origin.png](tests/fixtures/labels/import-no-origin.png) | Set B | Not a pass: country of origin: needs review |
| `S08-net-metric-and-floz` | [net-metric-and-floz.png](tests/fixtures/labels/net-metric-and-floz.png) | Set A | Pass: all applicable checks match |
| `S09-net-floz-only` | [net-floz-only.png](tests/fixtures/labels/net-floz-only.png) | Set A | Not a pass: net contents: needs review |
| `S10-net-litres-expected` | [starter-clear.png](tests/fixtures/labels/starter-clear.png) | Set A with Net contents: 0.75 L | Pass: all applicable checks match |
| `S11-abv-proof-only` | [abv-proof-only.png](tests/fixtures/labels/abv-proof-only.png) | Set A | Not a pass: alcohol content: needs review |
| `S12-address-within-street-line` | [producer-street.png](tests/fixtures/labels/producer-street.png) | Set A | Pass: all applicable checks match |
| `S13-address-street-abbreviation` | [producer-street.png](tests/fixtures/labels/producer-street.png) | Set A with Address: 123 Main Street, Louisville, KY | Pass: all applicable checks match |
| `S14-address-different-city` | [producer-street.png](tests/fixtures/labels/producer-street.png) | Set A with Address: Bardstown, KY | Not a pass: producer address: discrepancy |
| `S15-address-longer-city-name` | [producer-new-louisville.png](tests/fixtures/labels/producer-new-louisville.png) | Set A | Not a pass: producer address: discrepancy |
| `S16-warning-heading-title-case` | [starter-warning-title-case.png](tests/fixtures/labels/starter-warning-title-case.png) | Set A | Not a pass: warning wording: discrepancy; warning heading case: discrepancy |
| `S17-warning-heading-not-bold` | [warning-heading-regular.png](tests/fixtures/labels/warning-heading-regular.png) | Set A | Not a pass: warning heading bold: discrepancy |
| `S18-warning-all-bold` | [warning-all-bold.png](tests/fixtures/labels/warning-all-bold.png) | Set A | Not a pass: warning body not bold: discrepancy |
| `S19-front-back-warning-on-back` | [front-no-warning.png](tests/fixtures/labels/front-no-warning.png) (front)<br>[back-warning-only.png](tests/fixtures/labels/back-warning-only.png) (back) | Set A | Pass: all applicable checks match |
| `S20-front-back-warning-conflict` | [starter-clear.png](tests/fixtures/labels/starter-clear.png) (front)<br>[starter-warning-changed.png](tests/fixtures/labels/starter-warning-changed.png) (back) | Set A | Not a pass: warning wording: needs review; warning heading case: needs review |
| `S21-warning-absent` | [front-no-warning.png](tests/fixtures/labels/front-no-warning.png) | Set A | Not a pass: warning wording: needs review; warning heading case: needs review; warning heading bold: needs review; warning body not bold: needs review |
| `S22-blur-mild-legible` | [starter-clear-blur-r4.png](tests/fixtures/labels/starter-clear-blur-r4.png) | Set A | Pass: all applicable checks match |
| `S23-blur-heavy-unreadable` | [starter-clear-blur-r8.png](tests/fixtures/labels/starter-clear-blur-r8.png) | Set A | Not a pass: alcohol content: needs review; warning wording: needs review; warning heading case: needs review; warning heading bold: needs review; warning body not bold: needs review |
| `S24-warning-heading-smudged` | [warn-heading-blurry.png](tests/fixtures/labels/warn-heading-blurry.png) | Set A | Not a pass: warning wording: needs review; warning heading case: needs review; warning heading bold: needs review; warning body not bold: needs review |
| `S25-provider-timeout` | [starter-clear.png](tests/fixtures/labels/starter-clear.png) | Set A | Not a pass: provider failure `provider_timeout`, all checks not evaluated. Simulated in the offline tests; cannot be reproduced by uploading |
| `S26-provider-rate-limited` | [starter-clear.png](tests/fixtures/labels/starter-clear.png) | Set A | Not a pass: provider failure `rate_limited`, all checks not evaluated. Simulated in the offline tests; cannot be reproduced by uploading |
| `S27-provider-invalid-response` | [starter-clear.png](tests/fixtures/labels/starter-clear.png) | Set A | Not a pass: provider failure `invalid_provider_response`, all checks not evaluated. Simulated in the offline tests; cannot be reproduced by uploading |
| `S28-provider-failure-one-of-two-images` | [front-no-warning.png](tests/fixtures/labels/front-no-warning.png) (front)<br>[back-warning-only.png](tests/fixtures/labels/back-warning-only.png) (back) | Set A | Not a pass: provider failure `endpoint_blocked`, all checks not evaluated. Simulated in the offline tests; cannot be reproduced by uploading |
| `S29-held-out-wide-two-column` (held out) | [held-out-wide-two-column.png](tests/fixtures/labels/held-out-wide-two-column.png) | Own values: Brand: BLACK HEATH; Class/type: Rye Whiskey; ABV: 50.0; Net contents: 1 L; Producer: Heath Spirits Co.; Address: Frankfort, KY | Pass: all applicable checks match |
| `S30-held-out-tall-narrow` (held out) | [held-out-tall-narrow.png](tests/fixtures/labels/held-out-tall-narrow.png) | Own values: Brand: Northgate; Class/type: Blended Scotch Whisky; ABV: 40.0; Net contents: 700 mL; Producer: Northgate Imports; Address: Chicago, IL; Imported: yes; Country: Scotland | Not a pass: warning heading bold: discrepancy |

**How to read the expected results**
- They are the annotated ground truth for what is visible on each label, written from the pixels (annotations are pending developer review). They are not a promise about the live model: the blurred and smudged labels (`S22` to `S24`) are the likeliest to differ, and the model may flag more fields as needs review than listed.
- Country of origin is not applicable for domestic products (all of Set A), so it never blocks a pass.
- `S29` and `S30` are held out for the Day 3 evaluation: they were never used to tune the prompt or rules.
- Scenarios `S25` to `S28` simulate provider failures for the offline regression tests; they can't be triggered by uploading an image.
- The offline regression suite (`poetry run pytest tests/test_regression.py`) checks every development scenario against these expectations without credentials. It does not measure live extraction accuracy.

### Regenerating the sample images (optional)

The committed PNGs are the authoritative fixtures. Using them does not require DejaVu fonts.

Regeneration requires Pillow in the Poetry environment and these font files:
`DejaVuSans.ttf`, `DejaVuSans-Bold.ttf`, `DejaVuSerif.ttf` and
`DejaVuSerif-Bold.ttf`.

The script defaults to `/usr/share/fonts/truetype/dejavu`:

    poetry run python tests/fixtures/render_starter_labels.py

If the fonts are installed elsewhere, supply their directory:

    poetry run python tests/fixtures/render_starter_labels.py --font-dir "/path/to/fonts"

Rendering can vary with font versions, Pillow and the rendering environment.
After regeneration, visually inspect each image and confirm that it matches
its annotation and differs from the starter label only as intended. Update the
manifest hashes only after accepting any changes; investigate unexpected
differences before committing.

## Tests and code checks

| Check | Verified command | Current evidence |
| --- | --- | --- |
| Unit and adapter tests | `poetry run pytest` | 495 passed on 2026-10-25, offline: extraction parsing and errors, comparison policies, review wiring, results presentation, fixture manifest and the regression suite below |
| Offline regression over the annotated scenarios | `poetry run pytest tests/test_regression.py` | 36 passed: every development scenario runs through the real extraction parsing and review with a fake provider built from the annotations, including multi-image evidence and processing failures. Needs no credentials or network; validates parsing, aggregation and rules, not live accuracy |
| Formatting/linting | `poetry run ruff check .` and `poetry run ruff format --check .` | Both pass (27 files formatted) on 2026-10-25 |
| Intake form, manual browser check (Jira AL-44) | `poetry run streamlit run src/alcohol_label/app.py` | Passed 2026-10-23 locally: valid single image, two images, missing values, imported product without country, Clear form |
| Live extraction checks (need credentials) | `poetry run python scripts/al13_style_eval.py --runs 3` | Jira AL-13: 18 of 18 warning-style outcomes matched the annotations on three clear synthetic fixtures; other live smoke results are in [Evaluation](docs/evaluation.md) |
| Deployed smoke check | Manual, in a fresh browser session | Passed 2026-10-25 on commit `1beb0b8`: six checks behaved as expected; OpenAI request latency 4.68 to 6.45 s on four runs, so the five-second target is not met. No p95 or hosted correctness evaluation was run. |

Pull requests and feature branches have no automated CI yet (moved to the backlog); the deploy workflow runs the same ruff and pytest commands only on pushes to `main`. Run them locally before committing. Keep tests that require live credentials separate from offline rule/parsing tests. Passing mocked tests does not establish extraction accuracy. See [Evaluation](docs/evaluation.md) for planned scenarios, methods, actual results and known failures.

## Deployment

| Item | Value |
| --- | --- |
| Application URL | https://alcohol-label-staging.azurewebsites.net |
| Evaluator access instructions | Open the URL in any browser; no login. Enter the expected values, upload one or two JPEG/PNG label images, and select **Verify**. All field comparisons, the warning wording, heading-case and font-weight checks, and the results summary with next steps are deployed. Evaluators are given access to this repository, which holds the sample labels and the expected results (see Try it). |
| Deployed commit/release | Smoke-checked: `1beb0b8` on `main` (2026-10-25). The latest deploy run (`dc55197`) differs from it only by license header comments and author metadata, verified by diff, and was not re-smoke-checked. Later documentation-only commits do not redeploy. |
| Fresh-session access check | Passed 2026-10-25 by the developer in a fresh browser session on `1beb0b8`: six checks (load, input errors, match, discrepancy, warning-style discrepancy, unresolved) behaved as expected. First load (cold start) took about a minute; OpenAI request latency was 4.68 to 6.45 s on four runs. Details in [Evaluation](docs/evaluation.md). |

**How it is deployed.** `.github/workflows/main_alcohol-label-staging.yml` runs on pushes to `main` and manual dispatch. In one job it runs ruff and pytest, vendors runtime dependencies from `poetry.lock` into `.python_packages` (no server-side Oryx build, so `SCM_DO_BUILD_DURING_DEPLOYMENT` is unset), and deploys `src`, `.python_packages` and `pyproject.toml`. Recent runs took about 3.5 to 4 minutes. Pushes that change only Markdown or `docs/` files do not trigger a deploy. The startup command sets `PYTHONPATH` to `.python_packages` and `src` and runs Streamlit on port 8000. `OPENAI_API_KEY`, `OPENAI_MODEL` and `OPENAI_REASONING_EFFORT` are App Service application settings only.

**Known limitations.** Azure Login uses a federated credential, so deploys run only from `main`. A single-job workflow is used because the repository hit its Actions artifact storage quota. An app that previously had an Oryx build must have `oryx-manifest.toml` and `output.tar.zst` removed from `wwwroot`, or its startup script runs the stale build output.


## Documentation and delivery tracking

| Location | Purpose |
| --- | --- |
| [Engineering plan](docs/engineering-plan.md) | Scope, requirements, assumptions, architecture and technical decisions. |
| [Tool use](docs/tool-use.md) | Tools and AI assistance actually used, their purpose and how outputs were checked. |
| [Evaluation](docs/evaluation.md) | Test data, methods, measured results, known failures and limitations. |
| [Jira project](https://agentic-team.atlassian.net/jira/software/projects/AL/summary) | Sprints, epics, stories, tasks, acceptance criteria, dependencies and status. |

Maintain detailed work tracking in Jira and measured evidence in the evaluation document. Update this README as commands and features are verified so it describes the submitted application accurately.

## Author and contact

Developed by John Michael Egan.

- Primary: [mike@agentic.aero](mailto:mike@agentic.aero)
- Alternate: [j.mike.egan@gmail.com](mailto:j.mike.egan@gmail.com)

## Copyright and permitted use

Copyright © 2026 John Michael Egan. All rights reserved.

Available for hiring evaluation under the terms in [LICENSE](LICENSE).
Other uses require prior written permission.