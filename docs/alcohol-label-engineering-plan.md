# Alcohol Label Verification — Engineering Plan

Date: October 21, 2026  
Status: Proposed approach; no application code, benchmark, deployment, or test results have been produced as part of this document.  
Basis: The supplied `instructions.md`, the visible Python/Poetry/GitHub setup discussion, and the primary sources listed below.

## 1. Problem and success criteria

Build a standalone reviewer aid that compares submitted application values with evidence visible in alcohol label images, applies a documented subset of labeling checks, and quickly explains discrepancies and uncertainty.

The reviewer remains responsible for the decision. A result such as “Supported checks passed” describes only the checks actually performed. It is not a certification of complete TTB compliance.

The assignment's critical outcomes are useful verification, approximately five-second results, an obvious interface, and a working deployed URL. Its evaluation criteria also reward maintainable code, reasonable technical choices, error handling, requirement coverage, and documented trade-offs. No scoring weights or hard deadline were supplied.

Important input gap: the brief does not specify how application data reaches the prototype. Extracting label text by itself cannot establish whether it matches an application. This plan proposes a manual expected-values form first, and a manifest for batches.

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
| R07 | Batch uploads requested by stakeholder | Next increment after the single-application path: images plus a manifest, application identifiers, progress, per-item results, bounded concurrency, isolated failures, and results download. Test 200–300 applications before claiming that capacity. |
| R08 | Imperfect photographs | Initially correct orientation and validate readability. Rotation, glare, curvature, and blur form a challenge set. Route unresolved images to review; improve automatic handling after the core works. |
| R09 | Standalone, restricted network context | No COLA integration. State required runtime endpoints and whether the selected extraction path works without outbound inference access. Azure and .NET are background context, not mandated technologies. |
| R10 | Submission deliverables | Repository with source, locked dependencies, setup/run steps, approach/tools/assumptions, and a working deployed URL. Test access as an evaluator. |

Batch support is a meaningful stakeholder request, even though it is not enumerated under Technical Requirements. Deferring it protects the core, but does not make it disappear: report its actual status and limits.

### Scope boundary

Start implementation with the supplied distilled-spirits example to prove the complete workflow. Before submission, account explicitly for every listed common field and each beverage category exposed in the UI. Restrict or label unsupported categories instead of applying spirits rules universally.

Do not expand the prototype into COLA integration, production authorization, custom model training, a comprehensive regulatory engine, or an enterprise document archive. Physical type size and container-wide placement cannot be established from arbitrary images without adequate scale and coverage information. Surface those limitations.

## 3. Proposed assumptions register

| ID | Assumption or unresolved question | Initial decision | Consequence / validation |
| --- | --- | --- | --- |
| A01 | Application data format is unspecified | Manual typed fields for single review; structured CSV manifest for batches | Publish the schema and a sample. Replace the adapter if a real application format is provided. |
| A02 | Label evidence may span multiple sides | Allow several images for one application | Ask for all relevant sides. “Not found in supplied images” does not prove absence from the whole bottle. |
| A03 | Warning language and market | Initial profile covers English warnings for the stated U.S. exercise | Do not assume multilingual or export rules have been implemented. |
| A04 | Meaning of five seconds | Proposed target: p95 Verify-to-result within five seconds for a defined single-application profile | Report upload and page-load delays separately as well. Report cold starts, image counts and sizes, and concurrent load. No claim until measured. |
| A05 | File formats are unspecified | JPEG and PNG first; proposed limits of 10 MiB per image and 20 megapixels, subject to measurement | Validate decoded images, reject unsupported files clearly, and document total batch limits. PDF support is a separate decision. |
| A06 | Rules for matching are unspecified beyond examples | Per-field normalization; exact numeric equality after supported unit conversion | No general fuzzy-match acceptance and no invented numeric tolerance. |
| A07 | Cloud inference availability is unknown | Evaluate a local OCR baseline and one managed vision option | Record endpoint dependencies, observed latency, extraction quality, and cost. A cloud outage must never produce a pass. |
| A08 | No sensitive exercise data is required | Use synthetic/public test data; process uploads in memory or temporary storage | Document deletion behavior and any external processing. Do not claim that a provider has zero retention without checking its terms. |
| A09 | Batch pairing is unspecified | Map images to application IDs in a validated manifest | Detect duplicates, missing references, and unmatched files. Multiple sides of one application are not independent applications. |
| A10 | Time budget and rubric weights are unknown | Prioritize one complete deployed workflow, then batch support and image robustness | Record deferred items without representing them as finished. |

Update each assumption when evidence changes it. Add date, reason, and impacted requirement/test IDs; do not silently rewrite the project's history.

## 4. Processing design

Use a small Python application with four responsibilities:

1. **UI and input validation:** receive application values and images; display results and useful errors.
2. **Extraction adapter:** transcribe observed label content and return structured fields with evidence. Keep the provider behind a small interface.
3. **Comparison and rule functions:** normalize each field appropriately and apply explicit checks using ordinary Python.
4. **Result presentation:** explain matches, discrepancies, incomplete checks, and processing failures.

Keep extraction independent of expected application values where practical, so the model is less likely to copy the answer it was expected to find. Send only the image and an extraction schema. For vision models, label content is untrusted data, never instructions. Do not give the extractor tools or authority to make a final approval decision.

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

Before committing to an extraction engine, prepare roughly 10–15 manually verified images: clear text, stylized brand, warning change, ABV mismatch, small print, skew, blur, and front/back split. This is a development sample, not a general accuracy claim.

Compare a local OCR option such as Tesseract with one feasible managed vision option. Record field transcription errors, missed discrepancies, warning character errors, unresolved style checks, latency, network dependencies, setup effort, and per-application cost if applicable. Tesseract's official documentation specifically identifies skew as a source of OCR degradation; image handling is a measurable technical risk, not merely cosmetic preprocessing.

Choose one primary path based on results. Local OCR offers an inference path without external endpoints but does not by itself establish boldness. Managed vision may help with layout/style but introduces latency, cost, network access, and probabilistic output. Do not implement two production paths unless the measured value justifies it.

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
| Batch with one bad image or missing manifest reference | Isolate affected applications and preserve valid results. |

Unit-test pure comparison and applicability rules without network calls. Test the extraction adapter's parsing and error behavior with controlled responses. Keep a separate live integration benchmark for actual image extraction and deployment; mocked tests are not evidence of AI accuracy.

### Dataset and metrics

Create reproducible fixtures by rendering known text and known styling, then inspect them. AI-generated or public label images can supplement variety, but manually annotate their actual pixels; a generation prompt is not ground truth. Track provenance and permitted use for sourced images.

Reserve some layouts/examples for evaluation rather than tuning. Record the dataset version, app commit, extractor/model version, prompt version if relevant, hardware/hosting, and run date.

Report counts alongside rates: fields extracted correctly, seeded discrepancies detected/missed, false accepts, false discrepancies, and applications needing review. A system that sends every application to review may avoid false accepts while providing little useful automation. A reasonable acceptance goal is zero false accepts on the small critical defect suite, clearly limited to that suite.

For speed, measure uncached deployed runs and disclose cold/warm conditions. Include median, p95, maximum, sample count, failures, and image profile. A small sample gives a preliminary p95, not a stable service-level guarantee. Batch throughput, queue delay, time to first result, and total time are distinct from one-application latency. A progress spinner is not a completed five-second result.

## 7. Documentation that stays useful

Start with this plan in `docs/engineering-plan.md`; keep documentation small enough to maintain. Split it only when actual content makes that useful.

| Repository item | Content |
| --- | --- |
| `README.md` | Problem, deployed URL, quick start, actual Python/Poetry versions, system dependencies, configuration, example use, test commands, supported scope, and limitations. |
| `docs/engineering-plan.md` | Requirements, assumptions, architecture, rationale, build order, and requirement-to-test mapping. Update proposal statuses. |
| `docs/evaluation.md` | Fixture provenance, method, measured accuracy/performance, failures, and limitations. Create when experiments begin. |
| `docs/tool-use.md` | Tools and AI assistance actually used, purpose, versions where relevant, and how outputs were checked. |
| `src/<package>/` | Small modules for schemas, extraction, comparison/rules, orchestration, and UI. Use the actual existing package name. |
| `tests/` and `tests/fixtures/` | Meaningful automated cases and reviewed sample inputs/expected outputs. |
| `.env.example`, `.gitignore`, `pyproject.toml`, `poetry.lock` | Reproducible setup and secret-free configuration examples. Ignore real secrets and `.venv`. |

Use short decision entries within the plan first; a separate ADR directory is optional. Record a decision when there is a real alternative and consequence, not for every minor coding choice.

### Initial tool-use entry

- ChatGPT: analyzed the supplied assignment, proposed requirements and engineering workflow, and consulted primary documentation on October 21, 2026.
- Review status: proposed plan for the developer to adopt or revise. No implementation or test execution occurred as part of preparing this plan.
- Python/Poetry, VS Code, Git and GitHub: setup is described in the visible conversation; exact versions and current repository contents have not been inspected here.

When coding assistance is used later, record affected work and actual verification. Never mark a result tested solely because an assistant suggested it. Do not put credentials or sensitive images into the log.

## 8. Implementation sequence and completion gates

1. **Understand and specify:** commit the requirements, assumptions, supported scope, and representative expected results. Define application/label schemas and outcome semantics.
2. **Resolve the risky dependency:** run the bounded extraction experiment; choose the primary adapter and record measured trade-offs.
3. **Build one complete path:** one application and its images through extraction, comparison, warning checks, and explained UI results. Include error handling and basic tests as it is built.
4. **Deploy early:** verify native dependencies, secret configuration, endpoint access, and evaluator access from another session. Streamlit Community Cloud is a candidate, not a requirement; validate its current limits and actual performance. Its docs recognize Poetry's `pyproject.toml` and separate system dependencies.
5. **Close coverage gaps:** cover all supported fields and categories, front/back evidence, case handling, exact-warning failures, unknown outcomes, and timing measurements.
6. **Add batches:** use the same per-application verifier, a manifest, bounded workers, progress, failure isolation, and download. Bound total upload/memory cost; do not launch 300 unconstrained inference calls. Document any batch-size limitation or interrupted-session behavior.
7. **Finish the evidence:** run the held-out examples and live deployment checks, record actual results, reconcile documentation with code, and submit the repository plus URL.

For a feature to be complete, its behavior must work, its important cases must be checked, its errors must be useful, and its scope/limitations must be documented. Deployment is part of completion.

## 9. Mapping work to the evaluation criteria

| Evaluation criterion | What the reviewer should be able to see |
| --- | --- |
| Correctness and completeness | Expected-versus-observed comparisons; supported-field coverage; separate strict warning checks; correct uncertainty handling; functioning submission. |
| Code quality and organization | Typed boundaries, small modules, pure rule functions, isolated provider integration, useful tests, and consistent style. |
| Appropriate technical choices | A small dependency set and application architecture, plus evidence explaining extraction and hosting choices. |
| User experience and error handling | Obvious workflow, readable reasons/evidence, recoverable failures, partial batch success, and accessible evaluator entry. |
| Attention to requirements | Explicit handling of five seconds, benign case differences, strict warning case/boldness, multiple label sides, restricted egress, and batch demand. |
| Creative problem-solving | Evidence crops, precise differences, conservative uncertainty, useful batch progress, and measured solutions to actual image problems. |

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
