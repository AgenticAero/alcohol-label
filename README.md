# Alcohol Label Verification

A Python prototype that helps a reviewer compare alcohol label images with expected application values and identify discrepancies, missing evidence and checks that need human review.

**Status:** Planning and initial repository setup. Application behavior, setup commands, tests and deployment have not yet been verified. Features below describe the intended prototype, not completed functionality.

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
| Supported Python version | Pending verification and recording |
| Poetry version | Pending verification and recording |
| UI framework | Proposed; selection pending |
| Extraction provider/model | Pending selection |
| Hosting platform | Pending selection |
| Native dependencies and required network endpoints | Pending confirmation |

Actual tools and AI assistance are documented in [Tool use](docs/tool-use.md).

## Setup

**Pending implementation and clean-environment verification.** Replace the placeholders below with commands that have actually been tested.

| Step | Instructions |
| --- | --- |
| Obtain the source | TODO: Add the repository URL and clone command. |
| Install prerequisites | TODO: State supported Python/Poetry versions and any native dependencies. |
| Install dependencies | TODO: Add the verified Poetry installation command, including any required dependency groups. |
| Configure the application | TODO: List required settings, credential setup and required endpoints. Link to a secret-free `.env.example` once created. |
| Confirm the environment | TODO: Add a simple command that confirms the expected interpreter/configuration. |

Keep credentials outside version control. Document which image data is sent to an external service, if applicable, and how uploaded data is retained or cleaned up.

## Run locally

**Verified startup command:** TODO after the application entry point exists.

**Local URL and expected startup behavior:** TODO.

**Sample review:** TODO: Link to reviewed sample images and expected input values once available. Include a matching example and a deliberate discrepancy.

## Tests and code checks

| Check | Verified command | Current evidence |
| --- | --- | --- |
| Unit and adapter tests | TODO | Not run |
| Formatting/linting | TODO | Not run |
| Live extraction evaluation | TODO | Not run |
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
