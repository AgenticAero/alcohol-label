"""Shared manifest access and annotation-derived provider output for tests."""

import json
from pathlib import Path

from alcohol_label.schemas import FieldId

FIXTURES = Path(__file__).parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
SCENARIOS = {s["scenario_id"]: s for s in MANIFEST["scenarios"]}
STARTERS = {i["file"]: i for i in MANIFEST["images"]}


def _judgement(text: str | None) -> str:
    if text is None or text.startswith("cannot"):
        return "uncertain"
    return "bold" if text.startswith("bold") else "not_bold"


def provider_response(entry: dict) -> dict:
    """What a faithful provider would return for an annotated image.

    Printed text is observed, unprinted is missing, and an illegible field is
    uncertain with only a partial reading. Style follows ``visible_style``.
    """
    text, illegible = entry["visible_text"], set(entry.get("illegible_fields", []))
    fields = {}
    for field in FieldId:
        if field is FieldId.WARNING_TEXT:
            heading = text["warning_heading"]
            value = None if heading is None else f"{heading} {text['warning_body']}"
        else:
            value = text[field.value]
        if value is None:
            fields[field.value] = {"text": None, "state": "missing"}
        elif field.value in illegible:
            fields[field.value] = {"text": value[:20], "state": "uncertain"}
        else:
            fields[field.value] = {"text": value, "state": "observed"}
    style = entry["visible_style"]
    heading, body = (
        _judgement(style["warning_heading"]),
        _judgement(style["warning_body"]),
    )
    fields["warning_style"] = {
        "heading": heading,
        "body": body,
        "reason": (
            "The warning is not visible or not legible."
            if "uncertain" in (heading, body)
            else None
        ),
    }
    content = {"type": "output_text", "text": json.dumps(fields)}
    return {"output": [{"content": [content]}]}
