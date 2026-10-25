"""Live font-weight evaluation (AL-13): repeated runs of the production adapter.

Runs each font-weight scenario RUNS times through ``extract_application`` and
the review, then prints observed style judgements and outcomes next to the
annotated expectation. Needs OPENAI_API_KEY and OPENAI_MODEL (or .env). This is
development data only, not a general accuracy measurement.

    poetry run python scripts/al13_style_eval.py [--runs 3]
"""

import argparse
import json
from pathlib import Path

from alcohol_label.extraction import extract_application
from alcohol_label.review import review_after_extraction
from alcohol_label.schemas import CheckId, application_from_dict

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
SCENARIO_IDS = (
    "S01-clear-match",
    "S17-warning-heading-not-bold",
    "S18-warning-all-bold",
)
STYLE_CHECKS = (CheckId.WARNING_HEADING_BOLD, CheckId.WARNING_BODY_NOT_BOLD)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    runs = parser.parse_args().runs

    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    scenarios = {s["scenario_id"]: s for s in manifest["scenarios"]}
    for scenario_id in SCENARIO_IDS:
        scenario = scenarios[scenario_id]
        application = application_from_dict(scenario["application"])
        image_file = scenario["image_files"][0]
        data = (FIXTURES / image_file).read_bytes()
        expected = scenario["expected_outcomes"]
        print(f"\n{scenario_id}  ({image_file})")
        for run in range(1, runs + 1):
            result = extract_application(application.images, [data])
            if run == 1 and result.metadata:
                m = result.metadata
                print(
                    f"  {m.provider} {m.model} prompt={m.prompt_id} schema={m.schema_id}"
                )
            response = review_after_extraction(
                application, result.errors, result.fields, result.warning_styles
            )
            outcomes = {r.check_id: r for r in response.check_results}
            seconds = ", ".join(
                f"{t.elapsed_seconds:.2f}s" for t in result.request_timings
            )
            style = result.warning_styles[0] if result.warning_styles else None
            seen = (
                f"heading={style.heading.value} body={style.body.value}"
                f" reason={style.reason!r}"
                if style
                else "no style returned"
            )
            errors = [e.code.value for e in result.errors]
            print(f"  run {run}: {seen}; request {seconds}; errors={errors}")
            for check in STYLE_CHECKS:
                got = outcomes[check].outcome.value
                want = expected[check.value]
                flag = "ok" if got == want else "DIFFERS"
                print(f"    {check.value}: got {got}, annotated {want} [{flag}]")


if __name__ == "__main__":
    main()
