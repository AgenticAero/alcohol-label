# Evaluation

**Status: Not yet evaluated.** This document defines planned checks and provides space for actual evidence. No application test, accuracy or performance result is asserted below.

Scope and technical decisions belong in [engineering-plan.md](engineering-plan.md). Tool and AI usage belong in [tool-use.md](tool-use.md). Jira tracks work and defects; this document records evaluation evidence.

## 1. Evaluation scope

Evaluate one application at a time using English-language U.S. distilled-spirit labels, manual expected application values, and one or two clear JPEG/PNG images. Check the supported common fields and separate warning wording, heading case and visual-style outcomes.

The proposed speed target is p95 Verify-to-result at or below five seconds. This is our operational interpretation of the assignment's approximate five-second expectation, not an independently supplied service-level agreement.

Wine/beer-specific rules, advanced image correction and 200–300 application batches are outside the committed prototype scope. Evaluate optional small-batch support separately if implemented. Any unsupported warning-style check must remain explicit; a manual-review fallback does not establish automated formatting verification.

## 2. Test data — planned

Start with four visually verified scenarios: a clear match, case-only brand variation, ABV mismatch and changed warning text. Grow the set to at least ten annotated scenarios and reserve at least two distinct layouts/examples that were not used to tune extraction.

Store reusable inputs and annotations in `tests/fixtures/`. Keep one fixture manifest alongside them; link it here when created instead of duplicating every annotation in this document.

**Fixture manifest:** [`tests/fixtures/manifest.json`](../tests/fixtures/manifest.json) (`starter-0.2`), checked offline by `tests/test_fixtures.py`. It holds fifteen synthetic scenarios on nine labels: the four starters (`S01` clear match, `S02` case-only brand, `S03` ABV mismatch, `S04` changed warning word) and `S05` to `S15` for origin, net-contents, proof-only and address rules, plus the existing public or vendor images as unannotated reference images with source URLs and unconfirmed permission. An offline test feeds each scenario's annotated label text through the comparison rules and the review and checks the expected outcomes. Annotations are pending developer review. All scenarios are development data; no held-out set exists yet. Expected outcomes are pixel ground truth, not extractor results.

For each scenario, record:

- Stable scenario ID, image filenames and application ID; associate front/back images with the same application.
- Source/provenance and permission to use the images; whether synthetic or public.
- Expected application values and separately annotated text/style actually visible in the images.
- Expected check outcomes, deliberately introduced defects and any ambiguous evidence.
- Image dimensions/size, development versus held-out designation, and annotation reviewer/date.

Inspect the actual pixels. A generation prompt or expected application value is not evidence of what the label contains. Keep held-out examples out of prompt/rule tuning; if used for tuning, reclassify them and record the change.

## 3. Planned checks

These are test intentions, not passing results. One fixture may exercise several checks.

| ID | Scenario | Expected behavior |
| --- | --- | --- |
| EV01 | Clear matching label and application | Supported comparisons pass; unresolved checks remain visible. |
| EV02 | `STONE'S THROW` versus `Stone's Throw` | Brand matches under documented normalization. |
| EV03 | Substantively different brand | Discrepancy; no broad fuzzy acceptance. |
| EV04 | Expected ABV 40%, label 45% | Discrepancy showing both values. |
| EV05 | Expected 750 mL, label 0.75 L | Match after supported unit conversion. |
| EV06 | Class/type, producer/address and import-origin cases | Apply documented comparison/applicability rules; missing data cannot pass. |
| EV07 | Warning word omitted or changed | Wording discrepancy without autocorrecting the observation. |
| EV08 | Title-case warning heading | Separate heading-case discrepancy. |
| EV09 | Bold heading, non-bold heading, entirely bold warning | Separate heading/body style outcomes; uncertain or unsupported style requires review. |
| EV10 | Warning on supplied back image | Use both images before assessing whether evidence is missing. |
| EV11 | Unreadable/cropped evidence or conflicting observations | Needs review with evidence and reason; no all-clear result. |
| EV12 | Missing expected application value | Actionable incomplete input or Not evaluated. |
| EV13 | Corrupt/oversized image or unsupported format | Useful error; session remains usable. |
| EV14 | Timeout, blocked endpoint, rate error or invalid response | Controlled processing failure; preserve inputs and provide recovery. |
| EV15 | Reviewer workflow | Check previews, labels, keyboard navigation, readable statuses and recovery. |
| EV16 | Fresh setup and evaluator access | Documented installation/run/test steps work; deployed app and repository are accessible as intended. |

## 4. Methods — planned

### Automated and manual checks

1. Test pure comparison/applicability rules without network calls.
2. Test adapter parsing and error handling using controlled responses. These tests validate behavior, not real extraction accuracy.
3. Evaluate actual extraction on annotated images, including held-out examples.
4. Manually walk through match, discrepancy, Needs review and processing-error states.
5. Follow README from a clean environment and check the deployed revision in a fresh browser session.

Record the actual commands and outcomes when run. Link to test output or CI evidence rather than copying long logs. Mark skipped, blocked and unsupported checks explicitly.

### Correctness measurements

Report raw counts and denominators alongside any rates:

- **Extraction correctness:** correctly extracted fields / annotated eligible fields. Report missing and ambiguous outputs separately.
- **Defect detection:** seeded defects explicitly identified as discrepancies / seeded defects evaluated. Needs review is reported separately from detection.
- **False accept:** a known defective check is reported as passing. Also record any application-level all-clear with a known defect or unresolved relevant check.
- **False discrepancy:** a known acceptable check is reported as a discrepancy.
- **Review burden:** applications requiring review / applications evaluated, with reasons.
- **Processing failures:** attempted reviews that did not produce a completed verification result.

The proposed acceptance goal is zero false accepts on the small critical-defect suite. Even if achieved, this supports only a claim about that suite, not general regulatory accuracy. Sending everything to review is not successful automation.

### Verify-to-result performance

- Measure at least twenty uncached hosted review attempts across the annotated scenarios, including held-out examples. Repeated runs measure timing variability; they do not create independent accuracy examples.
- Start at the Verify action and stop when the completed result is visible. A spinner, acknowledgement or partial result is not completion. Server-only timings must be labelled separately if client-visible timing is unavailable.
- Report prior upload/page-load time separately. Record image count, sizes, hosting conditions and concurrent workload.
- Record cold/warm conditions and any result caching. Do not use cached results to claim uncached performance.
- Record every attempt, including timeouts and failures. Report completed-result latency statistics alongside completion/failure counts; fast error responses do not count as successful results.
- Report median, p95 and maximum. For reproducibility, use nearest-rank p95: sort completed-run durations and select rank `ceil(0.95 × n)` (one-based). State `n` and the method with results.
- Also report completed results within five seconds / all attempts. This exposes reliability gaps that a success-only p95 can hide.
- Disclose that twenty attempts give a preliminary estimate. Separate cold-start observations; identify which conditions are included in each summary.

Batch throughput and queue delay require separate measurement if batch support is implemented.

## 5. Actual results

**No live extraction accuracy or performance evaluation recorded.** The AL-6 spike below is feasibility evidence, not an AL-8 evaluation run. Use “Not run,” “Blocked” or “Not measured” rather than zero where evidence is absent.

### AL-8 offline implementation checks (2026-10-23)

| Command | Result | Scope |
| --- | --- | --- |
| `poetry run pytest` | 126 passed, 0 failed, 0 skipped | Offline suite; includes mocked provider contract, response parsing, multi-image aggregation and failure mapping. |
| `poetry run ruff check .` | Passed | Repository lint. |
| `poetry run ruff format --check .` | Passed; 20 files formatted | Repository formatting check. |

These checks do not validate live extraction accuracy or hosted performance. The adapter smoke results below are separate from a full accuracy or performance evaluation.

### AL-8 live adapter smoke check (2026-10-23)

- **Input:** `starter-clear.png` from the synthetic development fixtures; one adapter call, not a browser workflow or benchmark.
- **Provider configuration:** OpenAI Responses API, model `gpt-6-luna`, prompt `label-extraction-v1`, schema `label-observations-v1`.
- **Observed result:** No processing error. Seven fields were `observed`; `country_of_origin` was `missing`, matching the fixture annotation. The warning was returned as raw `warning_text`.
- **Failure diagnosed and corrected:** A blank `OPENAI_BASE_URL` in the local environment overrode the default, producing the relative URL `/responses`. Blank values now use `https://api.openai.com/v1`; an offline regression test covers this.
- **Limitations:** Latency was not measured. This single adapter smoke call does not establish accuracy, UI behavior, hosted performance, or the AL-8 requirement to evaluate both distinct starter images.

### AL-8 concurrent two-image smoke check (2026-10-23)

- **Input:** `starter-clear.png` and `starter-warning-changed.png`, passed together as one two-image application to the production adapter.
- **Provider configuration:** OpenAI Responses API, model `gpt-6-luna`, prompt `label-extraction-v1`, schema `label-observations-v1`.
- **Observed result:** Both calls completed without processing errors. Ordinary fields were observed, country of origin was missing, and `warning_text` was conflicting across the two images.
- **Elapsed time:** 14.09 seconds for the full local `extract_application` call in this single run. The UI now displays the client-side duration of each individual provider request; those request durations are not total Verify-to-result latency.
- **Limitations:** This is one smoke measurement, not the prescribed performance sample. It exceeds the five-second target and does not establish p95 performance or general extraction accuracy. More timing/evaluation work remains necessary.

### AL-6 feasibility spike (2026-10-23)

Script: `scripts/al6_extraction_spike.py` (throwaway, not the adapter). Model `gpt-6-luna` through the OpenAI Responses API with a strict JSON schema, only the image sent, `store: false`. Two distinct images: `starter-clear` and `starter-warning-changed` (S02 and S03 reuse the clear image). Development data only; no held-out images. Exact string comparison to `visible_text` in `tests/fixtures/manifest.json`.

| Reasoning effort | Attempts | Exact fields | Latency (s) | Notes |
| --- | --- | --- | --- | --- |
| model default | 8 | 9 of 9 each | 3.05 to 4.13 warm; 3.92 and 7.89 first attempt | Later runs reused a cached 1,756-token prefix |
| `low` | 6 | 9 of 9 each | 2.52 to 3.13 | Reasoning tokens 0 to 74 |
| `none` | 6 | 9 of 9 each | 2.34 to 3.37 | No reasoning tokens |
| `minimal` | 6 | Not run | Rejected, HTTP 400 | Unsupported for this model |

- **Bold signal:** "yes" on both images, both of which have a bold heading. No negative case was tested.
- **Hosted check:** text-only call from the Azure App Service B1 host returned HTTP 200 in 4.13 s. No image extraction was run on the host.
- **Limits:** Few attempts; warm and cached conditions; client was the developer's machine, not the deployed app; cost not measured. This does not establish accuracy on other layouts, photographed labels or the five-second target.

### AL-10 deployed smoke check (2026-10-24)

- **Deployed revision:** `e4c8acb` on `main`, https://alcohol-label-staging.azurewebsites.net, Azure App Service B1 (Central US).
- **Result:** In a fresh browser session a real extraction and brand comparison ran end to end: brand match, brand discrepancy and the implemented-checks notice all worked.
- **Latency observed:** OpenAI Responses API request latency was over 5 s on the first run and 3.98 s on the second. Exact first-run value, sample size and input images were not recorded, so this is anecdotal and does not support the five-second target; the hosted performance evaluation is still pending.

### AL-11 live pipeline check on the fixtures (2026-10-24)

- **Revision and setup:** branch `al-11-compare-remaining` at `ffb1222`, run from the developer's machine (not the deployed app) with the production adapter, model `gpt-6-luna`, prompt `label-extraction-v3`, schema `label-observations-v1`, reasoning effort per the local `.env`.
- **Input:** all 15 scenarios in `tests/fixtures/manifest.json` (`starter-0.2`), one run each, one image per application. They use nine distinct synthetic images; S01 to S03 and S10 share one image. Development data only; no held-out images.
- **Result:** no processing errors. For the seven field checks, the app's outcome equalled the annotated expected outcome in all 105 of 105 cases (15 scenarios by 7 checks). This includes `Product of Scotland` against `Scotland` (match), the importer-address-only label (origin `needs_review`), proof-only and fl oz-only readings (`needs_review`), the role-phrase producer line (address isolated and matched), and `New Louisville, KY` (discrepancy). The four warning checks were not evaluated by design and are excluded.
- **Latency (client-side extraction request, single image):** 3.12 to 7.08 s, with 14 of 15 requests between 3.1 and 5.0 s; the 7.08 s request was S08. This is not a hosted measurement and does not establish the five-second target.
- **Limits:** one run per scenario, so run-to-run variation is unknown; the annotations are the developer's pending review and were made from the rendered pixels; synthetic, clear images only. This is not an accuracy claim for real labels.

### AL-11 deployed smoke check

- **Status:** Not run. It requires merging to `main` and deploying; the fixture clear label (`S01`) and one mismatch (`S03`) are to be run in a fresh browser session. Record the deployed commit, date, observed outcomes and latency here when done.

### AL-12 offline warning-check implementation (2026-10-24)

- **Checks run:** `poetry run pytest tests/test_comparison.py tests/test_review.py -q` (146 passed).
- **Covered behavior:** exact wording with layout whitespace changes; changed warning word; independent uppercase-heading outcome; missing and uncertain warning evidence; conflicting observations from front/back images retain both evidence references. The two boldness checks remain `not_evaluated` for AL-13.
- **Additional regression and repository checks:** omitted-word and second-image warning cases; final `poetry run pytest -q` (326 passed), `poetry run ruff check .` (passed), `poetry run ruff format --check .` (22 files formatted), and Streamlit `AppTest` (no app exceptions).
- **Source:** current eCFR text for [27 CFR 16.21](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16/section-16.21); comparison normalizes whitespace only and retains the original observation.
- **Limitations:** tests use synthetic or constructed observations and do not establish live extraction accuracy, hosted behavior, formatting compliance, or physical label placement. No deployed smoke check was run for this branch.

### Run context

| Item | Recorded value |
| --- | --- |
| Run ID / date / evaluator | Not recorded |
| Git commit / deployed revision / URL | Not recorded |
| Dataset version and scenario IDs | Not recorded |
| Python / dependency lock revision | Not recorded |
| Extraction provider / model / prompt or schema version | Not recorded |
| Host / resources / cold or warm conditions | Not recorded |
| Input profile / concurrent workload / caching | Not recorded |
| Commands and evidence links | Not recorded |

### Check results

Add rows for completed or attempted checks; reference the planned check IDs and fixture IDs.

| Run / check / fixture IDs | Expected outcome | Actual outcome | Status | Evidence / defect link |
| --- | --- | --- | --- | --- |
| — | — | — | Not run | — |

Use Pass, Fail, Blocked, Not run or Not supported for **evaluation status**. Keep these distinct from the app's Match, Discrepancy, Needs review and other product outcomes: a test may pass because the app correctly reports a discrepancy.

### Correctness summary

| Metric | Count / denominator | Notes / evidence |
| --- | --- | --- |
| Correctly extracted fields | Not measured | — |
| Seeded defects detected | Not measured | — |
| False accepts | Not measured | — |
| False discrepancies | Not measured | — |
| Applications requiring review | Not measured | — |
| Processing failures | Not measured | — |

### Performance summary

| Run group / conditions | Attempts / completed / failed | Median | p95 | Maximum | Completed within 5 s / all attempts |
| --- | --- | --- | --- | --- | --- |
| Not measured | — | — | — | — | — |

**Target assessment:** Not evaluated.

Link to raw timing evidence when available. Include attempt ID, scenario ID, duration, outcome and cold/warm state so summary calculations can be reproduced. Do not include credentials or sensitive uploaded content.

## 6. Known failures and limitations

**Observed failures:** None recorded because evaluation has not yet been performed. This is not evidence that no failures exist.

| Finding ID | Scenario / observed behavior | Impact | Evidence / Jira issue | Mitigation or next step | Retest result |
| --- | --- | --- | --- | --- | --- |
| — | No observed findings recorded | — | — | Run evaluation | Not run |

Declared scope limitations include clear-image/distilled-spirit coverage, small sample size, deferred large batches, and inability to establish physical type size or container-wide placement from arbitrary images. Record actual visual-style support and measured performance gaps after evaluation; do not imply they have been resolved.

When a defect is fixed, retain the original finding and add the retest commit/result. A completed measurement task does not mean its product target was met.

## 7. Submission assessment

Complete after final evaluation:

- **Verified behavior:** Pending.
- **Unmet requirements and measured target misses:** Pending evaluation.
- **Unsupported/deferred scope:** Confirm against the implemented app and engineering plan.
- **Clean setup and fresh-session access:** Not checked.
- **Final commit / deployed revision:** Not recorded.
- **Remaining risks for the evaluator:** Pending.
