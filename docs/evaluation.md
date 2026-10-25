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

**Fixture manifest:** [`tests/fixtures/manifest.json`](../tests/fixtures/manifest.json) (`starter-0.3`), checked offline by `tests/test_fixtures.py`. It holds sixteen synthetic scenarios on ten labels: `S01` clear match, `S02` case-only brand, `S03` ABV mismatch, `S04` changed warning word, `S16` title-case warning heading, and `S05` to `S15` for origin, net-contents, proof-only and address rules, plus the existing public or vendor images as unannotated reference images with source URLs and unconfirmed permission. An offline test feeds each scenario's annotated label text through the comparison rules and review and checks the expected outcomes. Annotations are pending developer review. All scenarios are development data; no held-out set exists yet. Expected outcomes are pixel ground truth, not extractor results.

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
| EV15 | Reviewer workflow | Check previews, labels, readable statuses and recovery. |
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

### AL-13 warning font-weight evaluation (2026-10-25)

- **Revision and setup:** branch `al-13-warning-font` at `0514e46`, run from the developer's machine (not the deployed app) with `scripts/al13_style_eval.py` and the production adapter: OpenAI Responses API, model `gpt-6-luna`, prompt `label-extraction-v4`, schema `label-observations-v2`, one image per application, reasoning effort per the local `.env`. Style is requested in the same request as transcription, so there is no extra call.
- **Input:** the three font-weight fixtures from `tests/fixtures/manifest.json` (`starter-0.4`), three runs each, 9 runs in total. Development data only; no held-out images. The annotations are the developer's pending review, made from the rendered pixels.

| Scenario / image | Annotated heading, body | Observed (3 runs) | Heading check | Body check |
| --- | --- | --- | --- | --- |
| S01 `starter-clear.png` | bold, regular | bold, not bold in 3 of 3 | match 3/3 | match 3/3 |
| S17 `warning-heading-regular.png` | regular, regular | not bold, not bold in 3 of 3 | discrepancy 3/3 | match 3/3 |
| S18 `warning-all-bold.png` | bold, bold | bold, bold in 3 of 3 | match 3/3 | discrepancy 3/3 |

- **Result:** 18 of 18 style check outcomes equalled the annotated expectation. No processing errors, no `uncertain` judgements and no `needs_review` outcomes occurred, so the uncertain path was not exercised live. There were no false accepts and no false discrepancies on this suite. Each defective style (S17 heading, S18 body) was reported as a discrepancy in 3 of 3 runs.
- **Latency (client-side extraction request, single image):** 3.66 to 8.63 s; 3 of 9 requests were at or under 5 s and 6 of 9 were over. This is not a hosted measurement and does not establish the five-second target.
- **Limits:** one provider and model; one rendering style (DejaVu Sans, 22 px, clean synthetic text); both weights are clearly distinct; only three images and three runs each, so run-to-run variation is poorly characterised. Photographed labels, other typefaces, small text, glare, blur and low-contrast headings were not tested, and no ambiguous example was run live. This is not an accuracy claim for real labels. The uncertain, absent-style, conflicting-image and wrong-image paths are covered only by offline tests with constructed inputs.
- **Automation coverage:** automatic heading and body weight assessment worked on the three clear fixtures within the timebox; the requirement is therefore not recorded as unmet for these inputs. Where the model is uncertain, returns no style or the images disagree, the check is `needs_review` with the original image and a reason shown. That visual-review path is a fallback and is not automated compliance. Physical type size is not assessed.
- **Offline checks:** `poetry run pytest` (381 passed), `poetry run ruff check .` (passed), `poetry run ruff format --check .` (passed). These validate contracts and rules with mocked provider output, not live accuracy.

### AL-14 reviewer-workflow walkthrough (2026-10-25)

- **Setup:** commit `7ee3059` on branch `al-14-`, run locally (not the deployed app) with `poetry run streamlit run` and driven in the integrated browser. Provider: OpenAI Responses API, model `gpt-6-luna`, prompt `label-extraction-v4`. Images were uploaded from the committed fixtures. Single run per state; this is a walkthrough, not an accuracy or performance measurement.

| State | Input | Observed on screen |
| --- | --- | --- |
| Input errors | Empty form, **Verify** | Warning "Expected values not entered: brand, class type, ... until then they are not evaluated"; errors "Application ID is required. Enter it, then click Verify." and "Upload at least one label image. Choose a label image, then click Verify." No provider call. |
| Match | S01 values, `starter-clear.png` | "Pass: all supported checks passed. Of 11 checks: 10 matched, 0 discrepancy, 0 needs review, 0 not evaluated, 1 not applicable." Table shows status word, expected, observed, file-name evidence and reason; the two style rows say "Judged from the image; physical type size is not assessed." |
| Discrepancy | Same image, ABV changed to 40 | "Not a pass ... 9 matched, 1 discrepancy ... Discrepancies: alcohol content." Row: "Label states 45%; expected 40%." No "What to do next" section. |
| Review needed | S01 values, `starter-clear-blur-r8.png` | "Not a pass ... 3 matched, 7 needs review, 1 not applicable. Needs review: class type, alcohol content, net contents, producer name, producer address, warning wording, warning heading case." "What to do next" lists "The class type could not be read reliably. Upload a clearer, closer image of it." (and five more fields). Technical details expander collapsed. |
| Failure and retry | Local proxy returned HTTP 429 to the first request, then forwarded | Error "Extraction failed for image image-1..."; "Not a pass ... 10 not evaluated ... Processing failed (1 error)". Steps: "The extraction service is busy. Wait a moment, then retry." and "Your entries and images are kept; use Retry to run Verify again." One **Retry** button. Clicking it re-ran Verify with the form and upload kept and gave "Pass ... 10 matched"; the failure steps and Retry button disappeared. |

- **Keyboard:** tab order was Application ID, brand, class/type, ABV, net contents, unit, producer name, address, imported toggle, upload, Verify, Clear form. Streamlit's own heading-anchor links are also focus stops. Screen-reader behavior was not tested.
- **Contrast:** status colours are 6.57 to 7.87 against white and 5.86 to 7.02 against the secondary background (WCAG AA needs 4.5); checked by `tests/test_presentation.py`. Streamlit's own alert tints were judged by eye only. The previous `green`, `red` and `darkorange` were 5.14, 4.00 and 2.33 against white.
- **Findings, not yet fixed:**
  1. **Fixed after the walkthrough.** On `starter-clear-blur-r8.png` the warning text was `uncertain` and two warning-text checks needed review, yet heading bold and body not bold were both reported `match` from the same image. Style is now `needs_review` whenever the warning text extraction is `uncertain` ("the warning text could not be read reliably, so the ... weight judgement is not accepted"). A later single live run on the same image gave warning text `uncertain`, model judgement bold / not bold, and both style checks `needs_review`, so the review was not all-clear. One run only; the 18 AL-13 outcomes were not re-run, but those fixtures have readable warning text.
  2. The first-line error for any provider failure reads "Check provider configuration and connectivity", even for a rate limit, and names `image-1` rather than the file.
  3. The upload control advertises "200MB per file" while the app rejects files over 10 MiB.
  4. Six separate "could not be read reliably" steps repeat the same advice.
  5. The extraction request for the blurred image took 16.92 s (other runs 3.66 s).
- **Not done:** the deployed app was not smoke-checked (the staging deployment is older than this branch), and the non-retryable failure and Visual review needed sections were not exercised in the browser; they are covered by offline tests and Streamlit test-harness runs only.
- **Offline checks:** `poetry run pytest` (422 passed), `poetry run ruff check .` and `poetry run ruff format --check .` passed.

### Held-out examples reserved for Day 3 (AL-153)

- **What is held out:** `S29-held-out-wide-two-column` (1500x800, left-aligned two-column serif layout, 1 L net contents, clean match) and `S30-held-out-tall-narrow` (800x1200, centered sans layout, imported, regular-weight warning heading). Both are synthetic renders from `tests/fixtures/render_starter_labels.py` with layouts, typefaces, canvas sizes and products that differ from the starter label. Manifest `starter-0.7` marks them `split: held_out`.
- **How they were chosen:** designed to differ from the development label in layout and typeface, not sampled. Expected outcomes were annotated from the rendered pixels (developer review pending).
- **Not used for tuning:** the extraction prompt and comparison rules were not run against them, and no test checks their outcomes. Tests exclude them from the development regression and per-field checks, and a test fails if any file under `tests/`, `scripts/` or `src/` names a held-out scenario or image. Any reclassification must be recorded in the manifest's `held_out_policy.reclassifications` (currently empty).
- **Limitation:** two clean, synthetic examples show feasibility on unseen layouts only. They cannot estimate accuracy, and they include no photographed, rotated, low-contrast or small-print label.

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
