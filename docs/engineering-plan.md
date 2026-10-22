# Alcohol Label Verification — Engineering Plan

Date: October 21, 2026  
Status: Proposed approach; no application code, benchmark, deployment, or test results have been produced as part of this document.  
Basis: The supplied `instructions.md`, Python/Poetry/GitHub setup discussion, three-day scope decisions consolidated from `plan.md`, and the primary sources listed below. This scope supersedes the earlier open-ended sequence; implementation status remains unverified.

## 1. Problem and success criteria

Build a standalone reviewer aid that compares submitted application values with evidence visible in alcohol label images, applies a documented subset of labeling checks, and quickly explains discrepancies and uncertainty.

The reviewer remains responsible for the decision. A result such as “Supported checks passed” describes only the checks actually performed. It is not a certification of complete TTB compliance.

The assignment's critical outcomes are useful verification, approximately five-second results, an obvious interface, and a working deployed URL. Its evaluation criteria also reward maintainable code, reasonable technical choices, error handling, requirement coverage, and documented trade-offs. No scoring weights were supplied. The developer has set a three-working-day prototype budget; an exact submission date/time remains unspecified.

Important input gap: the brief does not specify how application data reaches the prototype. Extracting label text by itself cannot establish whether it matches an application. Use a manual expected-values form for the committed prototype. A manifest belongs only to optional batch support.

## 2. Requirements and evidence of completion

The priorities below are engineering recommendations, not an official ranking supplied by the evaluator.

| ID | Requirement or stakeholder need | Proposed implementation and acceptance evidence |
| --- | --- | --- |
| R01 | Compare the application with the label | Expected-values form plus image upload. Results show expected value, observed value, evidence, status, and reason. Deliberately different application values produce discrepancies. |
| R02 | Common label fields | Cover brand, class/type, alcohol content, net contents, producer/bottler name and address, and origin where applicable. Document beverage-specific applicability. An omitted expected value is not a successful comparison. |
| R03 | Reasonable matching | Accept the supplied `STONE'S THROW` versus `Stone's Throw` case example. Preserve substantive differences and flag ambiguous OCR. Use separate field policies. |
| R04 | Exact warning text and presentation | Separate checks for wording, uppercase heading, and bold presentation. Preserve original text and image evidence. A text-only extraction cannot establish boldness. |
| R05 | About five-second results | Measure the deployed path from Verify to visible result for uncached supported inputs. Publish sample count, conditions, median, p95, maximum, and timeout count. Target p95 at or below five seconds as a proposed interpretation. |
| R06 | Simple agent experience | One obvious workflow: expected details, image upload, Verify, explained results. Large readable text, useful labels, keyboard access, and status words alongside colors. |
| R07 | Batch uploads requested by stakeholder | Deferred from the core commitment. A batch of up to five applications is optional stretch only after the core is submission-ready. Use a manifest, progress, isolated failures and results download. Durable 200–300 application processing requires separate implementation and evaluation. |
| R08 | Imperfect photographs | Initially correct orientation and validate readability. Rotation, glare, curvature, and blur form a challenge set. Route unresolved images to review; improve automatic handling after the core works. |
| R09 | Standalone, restricted network context | No COLA integration. State required runtime endpoints and whether the selected extraction path works without outbound inference access. Azure and .NET are background context, not mandated technologies. |
| R10 | Submission deliverables | Repository with source, locked dependencies, setup/run steps, approach/tools/assumptions, and a working deployed URL. Test access as an evaluator. |

Batch support is a meaningful stakeholder request, even though it is not enumerated under Technical Requirements. Deferring it protects the core, but does not make it disappear: report its actual status and limits.
## Requirement coverage and conscious gaps

| Requirement | Assignment need | Work items | Three-day treatment |
| --- | --- | --- | --- |
| R01 | Application versus label comparison | AL-7–AL-9, AL-11 | Manual expected-values form; one application per review. |
| R02 | Common fields and beverage applicability | AL-7, AL-8, AL-11 | All listed common fields included for the distilled-spirit profile; wine/beer-specific rules deferred. |
| R03 | Sensible text matching | AL-9, AL-11 | Case/whitespace and supported unit normalization; no broad fuzzy acceptance. |
| R04 | Warning wording, uppercase and bold | AL-12, AL-13, AL-15 | Separate text and visual outcomes; disclose any unimplemented/unreliable style automation. |
| R05 | Results in about five seconds | AL-6, AL-17 | Target and measurement commitment; no unmeasured guarantee. |
| R06 | Obvious UI and useful errors | AL-7, AL-9, AL-14, AL-15, AL-19 | One primary workflow, evidence, clear statuses and recovery. |
| R07 | Batch uploads | AL-20, AL-21 | Five-application batch is stretch; 200–300 scale is deferred. |
| R08 | Imperfect photographs | AL-16, AL-22 | Basic orientation and honest uncertainty now; difficult-image correction deferred. |
| R09 | Standalone prototype and network concerns | AL-6, AL-8, AL-10, AL-16, AL-18 | One documented extraction path and required endpoints; no COLA integration. |
| R10 | Repository, documentation and deployed URL | AL-5, AL-10, AL-15, AL-17, AL-18, AL-19 | Deployment on Day 1; final reproducibility and access checks on Day 3. |

### Scope boundary

The committed deliverable is a deployed Python/Poetry application for one application at a time, using English-language U.S. distilled-spirit labels. A reviewer enters expected values and uploads one or two clear JPEG/PNG images for the same application's front/back labels. Cover all listed common fields, including origin for imports, with separate warning wording, heading-case and supported font-weight outcomes. Wine/beer-specific rules are outside the three-day commitment; make that boundary visible in the UI.

Budget assumption: one developer with eight available hours per working day, of which six are planned and two reserved for debugging, deployment and review: 18 planned hours plus six hours of buffer. The buffer is not a feature commitment. Reduce scope if that capacity is unavailable. Sprint dates, estimates, assignments and progress are maintained in Jira.

Batch processing of up to five applications is stretch only when the core submission is ready and at least its estimated 2.5 hours of genuine spare capacity remain, including final checks. Durable 200–300 application batches, advanced glare/perspective/curvature correction, additional beverage profiles and persistent case history are deferred. Basic EXIF orientation and useful unreadable-image handling remain in scope.

Warning font-weight automation is the highest technical uncertainty. If it cannot be demonstrated within the planned 1.5-hour implementation timebox, ship an explicit visual-review path and record the unmet automation requirement. Human review does not count as automated formatting verification.

Label count and image coverage: TTB does not require separate front and back labels for distilled spirits. Required information may appear on one or multiple labels, subject to applicable placement requirements. The prototype accepts one or two images per application; this limit is an implementation constraint, not a regulatory requirement. A second image is optional. Missing information in supplied images requires additional evidence and does not establish that the information is absent from the bottle. Finding brand, class/type and alcohol content across uploaded images does not establish that they appear together in the required field of vision on the physical container.

Do not expand the prototype into COLA integration, production authorization, custom model training, a comprehensive regulatory engine, or an enterprise document archive. Physical type size and container-wide placement cannot be established from arbitrary images without adequate scale and coverage information. Surface those limitations.

## 3. Proposed assumptions register

| ID | Assumption or unresolved question | Initial decision | Consequence / validation |
| --- | --- | --- | --- |
| A01 | Application data format is unspecified | Manual typed fields for single review; CSV manifest only if batch stretch is implemented | Publish the schema and a sample. Replace the adapter if a real application format is provided. |
| A02 | Label evidence may span multiple sides | Allow one or two clear JPEG/PNG images for one application | Ask for all relevant sides. “Not found in supplied images” does not prove absence from the whole bottle. |
| A03 | Warning language and market | Initial tested profile covers English-language U.S. distilled-spirit labels | Do not assume multilingual or export rules have been implemented. |
| A04 | Meaning of five seconds | Proposed target: p95 Verify-to-result within five seconds for a defined single-application profile | Report upload and page-load delays separately as well. Report cold starts, image counts and sizes, and concurrent load. No claim until measured. |
| A05 | File formats are unspecified | JPEG and PNG first; proposed limits of 10 MiB per image and 20 megapixels, subject to measurement | Validate decoded images, reject unsupported files clearly, and document total batch limits if batch stretch is implemented. PDF support is a separate decision. |
| A06 | Rules for matching are unspecified beyond examples | Per-field normalization; exact numeric equality after supported unit conversion | No general fuzzy-match acceptance and no invented numeric tolerance. |
| A07 | Cloud inference availability is unknown | Timebox feasibility to one hour; test an accessible option and at most one alternative if blocked or unusable | Record endpoint dependencies, observed latency, extraction quality, and cost. A cloud outage must never produce a pass. |
| A08 | No sensitive exercise data is required | Use synthetic/public test data; process uploads in memory or temporary storage | Document deletion behavior and any external processing. Do not claim that a provider has zero retention without checking its terms. |
| A09 | Batch pairing is unspecified | Map images to application IDs in a validated manifest | Detect duplicates, missing references, and unmatched files. Multiple sides of one application are not independent applications. |
| A10 | Three working days; rubric weights and exact submission time are unspecified | Plan 18 hours of core work plus six hours of buffer for one developer | Prioritize the complete deployed single-review workflow; keep batch and advanced image support deferred. |
| A11 | Existing repository, inference access and hosting are assumed usable | Verify Python/Poetry versions, credentials or local OCR, host dependencies and endpoint access at the outset | Unresolved access, billing or account approval requires an immediate scope/deployment decision; mocked extraction is not a working substitute. |

Update each assumption when evidence changes it. Add date, reason, and impacted requirement/test IDs; do not silently rewrite the project's history.

## 4. Processing design

Use a small Python application with four responsibilities:

1. **UI and input validation:** receive application values and images; display results and useful errors.
2. **Extraction adapter:** transcribe observed label content and return structured fields with evidence. Keep the provider behind a small interface.
3. **Comparison and rule functions:** normalize each field appropriately and apply explicit checks using ordinary Python.
4. **Result presentation:** explain matches, discrepancies, incomplete checks, and processing failures.

Keep extraction independent of expected application values, so the model is less likely to copy the answer it was expected to find. Send only the image and an extraction schema. For vision models, label content is untrusted data, never instructions. Do not give the extractor tools or authority to make a final approval decision.

Preserve entered values after recoverable errors. Enforce a finite extraction deadline, handle blocked endpoints/rate limits/schema failures, and prevent ordinary UI rerenders from duplicating provider work. Validate decoded image format, pixel and byte limits; correct EXIF orientation. Document temporary-file cleanup and avoid logging image contents or credentials.

### Data contracts

Define typed records for:

- `ApplicationData`: application ID, beverage category, import status, expected values, and supplied image references.
- `ExtractedField`: raw observed text, parsed value if available, source image ID, evidence location/crop when available, and explicit missing/uncertain/conflicting state.
- `CheckResult`: check ID, expected value, observed value, outcome, reason, and evidence.
- `VerificationResult`: all checks, summary, supported scope, extractor/rule version, and elapsed timings.

Use `null` and explicit states for unknowns. Do not manufacture a confidence percentage: provider or model confidence is not a calibrated probability of correctness.

### Results policy

| Outcome | Meaning |
| --- | --- |
| Match / Passed check | The supported comparison or rule was actually evaluated and passed. |
| Discrepancy | Observed evidence differs from the expected value or a supported rule. |
| Needs review | Evidence is unreadable, ambiguous, incomplete, or insufficient to establish the result. |
| Not applicable | A documented applicability rule excludes this check. |
| Not evaluated | A relevant check is unsupported or lacks required input; it cannot count as a pass. |

Represent a processing error separately from a labeling result. The aggregate cannot report all supported checks passed if a relevant check is unresolved, not evaluated, or failed. Keep known discrepancies visible even when other checks need review.

### Field-specific comparison policies

- **Brand and class/type:** normalize Unicode, whitespace, and case as appropriate. Handle typographic apostrophes explicitly. Do not remove all punctuation or accept a similar-looking brand automatically.
- **Alcohol content:** parse the numeric percentage, compare using decimal values, and retain the printed text. `45%` versus `45.0%` can match numerically; `45%` versus `40%` cannot. Proof consistency may be an additional documented check, but proof alone must not silently satisfy a required percentage statement.
- **Net contents:** convert supported units to a canonical quantity for comparison; `0.75 L` and `750 mL` can be equivalent. Value equivalence is separate from the legal acceptability of every printed format.
- **Producer/address and origin:** begin with conservative normalization. Ambiguous abbreviations require review unless an equivalence rule is explicitly implemented and tested. Imported-product applicability comes from application data.
- **Warning:** obtain the canonical text from 27 CFR 16.21 and pin a reviewed version in the code. Allow documented layout whitespace normalization while retaining words, order, punctuation, and heading case. Do not autocorrect OCR into the expected warning.
- **Warning presentation:** assess the original image/crop for boldness and other supported visual checks. Assess style before image transformations that could alter apparent stroke weight. Uncertain or unsupported style checks remain visible as review items.

TTB and 27 CFR 16.22 require the warning heading to be uppercase and bold, with the remaining statement not bold. The warning can appear on front, back, or side labels. Physical size rules also exist; this prototype must identify which visual requirements it can and cannot verify. See sources 1–2.

## 5. Tool choices and the first technical experiment

### Working recommendation

| Tool | Role | Why / decision status |
| --- | --- | --- |
| Existing Python and Poetry environment | Application runtime and reproducible dependencies | Retain the user's setup; record actual versions. `.venv/bin/python3.11` suggests 3.11, but verify it. Commit the lock file. |
| Streamlit | Initial browser UI | Recommended for a Python-focused, time-constrained form/upload/results prototype. Keep business logic outside UI code. Supports multiple-file uploads. |
| Pydantic | Input/extraction/result schema validation | Recommended where structured input or provider output crosses a boundary. Valid structure does not establish factual truth. |
| Pillow | Image decoding and basic orientation/size processing | Proposed; add more image-processing dependencies only for a demonstrated need. |
| One OCR/vision adapter | Image-to-structured-evidence extraction | Select after a bounded experiment; do not assume a provider meets the speed or quality target. |
| pytest | Comparison, failure-path, and fixture tests | Recommended for parameterized cases that exercise actual requirement differences. |
| Ruff | Formatting and linting | Recommended to keep style consistent with little configuration. |
| Git/GitHub | Version history and submission | Already chosen by the user. Use small, coherent commits tied to implemented behavior. |

Use FastAPI with a lightweight HTML interface if API separation or background batch jobs become an immediate requirement. A separate JavaScript application, database, or distributed task system needs a concrete reason before it earns a place in this prototype.

### Timeboxed extraction experiment

Timebox initial extraction and hosting feasibility to one hour. Prepare four visually verified starter fixtures: a clear sample, case-only brand variation, ABV mismatch and warning-text change. Record actual transcription errors, approximate latency, style-evidence support, endpoint dependencies, setup requirements and cost where applicable.

Start with an already accessible vision service if feasible. Try one alternative only if the first option is blocked or clearly unusable within the same hour; do not run a broad provider comparison. Local OCR is a fallback when service access is blocked, but does not alone establish boldness. Build one primary extraction adapter and preserve unresolved style checks as review items.

Confirm the intended host can install dependencies, reach required endpoints and expose an evaluator-accessible URL. Record access/billing prerequisites and choose a feasible extraction/hosting path from observed evidence. If none works, record the blocker and replan immediately.

Record the choice in a short decision entry: context, options, evidence, decision, consequences, and conditions for reconsidering it. Never populate the evidence section with expected rather than observed performance.

## 6. Verification and evaluation plan

### Tests derived from the brief

| Test | Expected behavior |
| --- | --- |
| Exact clear label/application match | Supported comparisons pass; unresolved visual checks remain explicit. |
| `STONE'S THROW` against `Stone's Throw` | Brand matches under documented case normalization. |
| Similar but genuinely different brands | Discrepancy or review; no automatic fuzzy acceptance. |
| Application 40%, readable label 45% | Alcohol-content discrepancy with both values shown. |
| `0.75 L` against `750 mL` | Numeric volume comparison matches. |
| One warning word removed or changed | Warning discrepancy; do not reconstruct the intended wording. |
| Warning heading in title case | Heading-case discrepancy even if normalized wording would match. |
| Correct heading text, wrong font weight | Style discrepancy when supported evidence establishes it; otherwise review. |
| Entire warning in bold | Detect the body-style issue if supported, otherwise mark that check unresolved. |
| Warning absent from front but visible on supplied back image | Aggregate evidence for the same application before assessing absence. |
| Cropped or unreadable warning | Review with a request for the relevant clearer image. |
| Conflicting ABV across images | Discrepancy/review with both observations; do not choose arbitrarily. |
| Missing expected field | Incomplete input or not evaluated; no invented comparison. |
| Corrupt/oversized file or unsupported format | Actionable error; app remains usable. |
| Extraction timeout, blocked endpoint, invalid response | Explicit processing failure/review path; no success from fallback guesses. |
| Batch with one bad image or missing manifest reference (stretch only) | Isolate affected applications and preserve valid results if batch support is implemented. |

Unit-test pure comparison and applicability rules without network calls. Test the extraction adapter's parsing and error behavior with controlled responses. Keep a separate live integration benchmark for actual image extraction and deployment; mocked tests are not evidence of AI accuracy.

### Dataset and metrics

Create reproducible fixtures by rendering known text and known styling, then inspect them. AI-generated or public label images can supplement variety, but manually annotate their actual pixels; a generation prompt is not ground truth. Track provenance and permitted use for sourced images.

Grow the four starter fixtures into at least ten annotated scenarios covering the core comparisons, warnings, front/back evidence, unknowns and processing failures. Include known bold-heading, non-bold-heading and entirely-bold-warning examples. Reserve at least two distinct layouts/examples for evaluation rather than tuning. Record the dataset version, app commit, extractor/model version, prompt version if relevant, hardware/hosting, and run date.

Report counts alongside rates: fields extracted correctly, seeded discrepancies detected/missed, false accepts, false discrepancies, and applications needing review. A system that sends every application to review may avoid false accepts while providing little useful automation. A reasonable acceptance goal is zero false accepts on the small critical defect suite, clearly limited to that suite.

For speed, run at least twenty uncached hosted reviews across the annotated scenarios, including held-out examples, and disclose cold/warm conditions. Time from Verify click to the completed visible result; upload/page-load delays are reported separately. Include median, p95, maximum, sample count, failures, and image profile. A small sample gives a preliminary p95, not a stable service-level guarantee. Batch throughput, queue delay, time to first result, and total time are distinct from one-application latency. A progress spinner is not a completed five-second result.

## 7. Documentation that stays useful

Maintain three documents: the root README is the entry point, this file owns scope/assumptions/decisions/tool use, and `docs/evaluation.md` owns evaluation methods and actual results. Jira owns sprints, epics, stories, tasks, acceptance criteria, dependencies and status. Do not maintain a duplicate backlog, `docs/README.md`, `docs/plan.md`, separate tool-use document or Jira import instructions in the repository.

| Repository item | Content |
| --- | --- |
| `README.md` | Problem, deployed URL, quick start, actual Python/Poetry versions, system dependencies, configuration, example use, test commands, supported scope, and limitations. |
| `docs/engineering-plan.md` | Requirements, scope, assumptions, architecture, technical decisions, tools and AI usage, and completion policy. Update proposal statuses. |
| `docs/evaluation.md` | Fixture provenance, method, measured accuracy/performance, failures, and limitations. Create when experiments begin. |
| `src/<package>/` | Small modules for schemas, extraction, comparison/rules, orchestration, and UI. Use the actual existing package name. |
| `tests/` and `tests/fixtures/` | Meaningful automated cases and reviewed sample inputs/expected outputs. |
| `.env.example`, `.gitignore`, `pyproject.toml`, `poetry.lock` | Reproducible setup and secret-free configuration examples. Ignore real secrets and `.venv`. |

Use short decision entries within the plan first; a separate ADR directory is optional. Record a decision when there is a real alternative and consequence, not for every minor coding choice.

### Tool and AI usage record

- ChatGPT: analyzed the supplied assignment, proposed requirements and engineering workflow, and consulted primary documentation on October 21, 2026.
- Review status: proposed plan for the developer to adopt or revise. No implementation or test execution occurred as part of preparing this plan.
- Python/Poetry, VS Code, Git and GitHub: setup is described in the visible conversation; exact versions and current repository contents have not been inspected here.

Planning assistance also decomposed the three-day scope and consolidated its unique decisions into this document. These document edits provide no evidence of application implementation or runtime performance. Record actual provider/model, hosting and package versions, meaningful prompts and affected code/fixtures when used. When coding assistance is used later, record affected work and actual verification. Never mark a result tested solely because an assistant suggested it. Do not put credentials or sensitive images into the log.

## 8. Delivery decisions and completion gates

Detailed scheduling and acceptance criteria live in Jira. Apply these scope decisions throughout the three-day build:

- Establish real extraction and the first deployed brand comparison on the first working day. Resolve access/hosting blockers before expanding fields; unimplemented checks remain Not evaluated.
- Complete the supported field/warning checks with evidence before final evaluation. Preserve a visual-review path and disclose the shortfall if style automation is unreliable.
- Prioritize false accepts, crashes, inaccessible deployment and setup defects during final validation. Fix measured issues within the remaining budget, rerun affected checks and disclose unmet targets. Freeze new features before submission rehearsal.
- Consider the five-application stretch only after the core is ready. Reuse the verifier, validate manifest IDs/image references, bound concurrency/uploads, isolate failures and document interruption limits. Large batches require separate resource, resume and throughput validation.

Completion means demonstrated behavior, passing focused checks, explicit errors/unknowns, documented assumptions/tools/limitations, committed code and deployed UI smoke checks. Tests are written with the behavior; a final consolidation pass cannot absorb an otherwise untested application. Add minimal test/lint CI if the repository runner is available; otherwise record reproducible local checks.

Before submission, follow README from a clean checkout/environment, verify the deployed revision and repository access from a fresh session, and rehearse valid, mismatch and warning/review examples. Record final commit/release, URL, test results and remaining gaps in README/evaluation as appropriate. An evaluation task may be complete while its performance target remains unmet; keep the unresolved product requirement visible in Jira and the evaluation record.

## 9. Mapping work to the evaluation criteria

| Evaluation criterion | What the reviewer should be able to see |
| --- | --- |
| Correctness and completeness | Expected-versus-observed comparisons; supported-field coverage; separate strict warning checks; correct uncertainty handling; functioning submission. |
| Code quality and organization | Typed boundaries, small modules, pure rule functions, isolated provider integration, useful tests, and consistent style. |
| Appropriate technical choices | A small dependency set and application architecture, plus evidence explaining extraction and hosting choices. |
| User experience and error handling | Obvious workflow, readable reasons/evidence, recoverable failures and accessible evaluator entry; partial batch success only if stretch is implemented. |
| Attention to requirements | Explicit handling of five seconds, benign case differences, strict warning case/boldness, multiple label sides, restricted egress, and batch demand. |
| Creative problem-solving | Evidence crops, precise differences, conservative uncertainty, and measured solutions to actual image problems; batch progress only if stretch is implemented. |

The strongest initial milestone is a deployed, tested single-application workflow with an honest scope statement and measured behavior. Expand from that working baseline.

## 10. Primary references consulted

Accessed October 21, 2026. The assignment remains the source of requested prototype behavior; external guidance clarifies domain details and does not automatically expand the scope.

1. [TTB: Distilled Spirits — Health Warning Statement](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-health-warning)
2. [27 CFR Part 16, particularly sections 16.21 and 16.22](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16)
3. [TTB: Distilled Spirits — Mandatory Label Information](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-brand-label)
4. [Streamlit: File uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader)
5. [Streamlit Community Cloud: App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
6. [Tesseract: Improving output quality](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
7. [Pydantic: Models](https://docs.pydantic.dev/latest/concepts/models/)
8. [pytest: Parametrizing tests](https://docs.pytest.org/en/stable/how-to/parametrize.html)
9. [Ruff documentation](https://docs.astral.sh/ruff/)

*** End of proposed plan ***
