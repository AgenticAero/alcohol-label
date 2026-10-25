"""Streamlit entry point: expected-value form, label upload and Verify."""

import pandas as pd
import streamlit as st

from alcohol_label.extraction import extract_application
from alcohol_label.intake import MAX_IMAGES, UploadedImage, build_application
from alcohol_label.presentation import (
    check_label,
    evidence_actions,
    evidence_names,
    failure_guidance,
    image_names,
    input_error_actions,
    missing_values_note,
    summarize,
)
from alcohol_label.review import review_after_extraction, unresolved_style_checks
from alcohol_label.schemas import Measurement, Unit

_VOLUME_UNITS = {
    "mL": Unit.MILLILITER,
    "L": Unit.LITER,
    "fl oz": Unit.FLUID_OUNCE,
}
_STATUS_STYLES = {
    "match": "color: green",
    "discrepancy": "color: red",
    "needs review": "color: darkorange",
}
_TEXT_KEYS = (
    "application_id",
    "brand",
    "class_type",
    "alcohol_content",
    "net_contents",
    "producer_name",
    "producer_address",
    "country_of_origin",
)


def _clear_form() -> None:
    for key in _TEXT_KEYS:
        st.session_state[key] = ""
    st.session_state["unit"] = next(iter(_VOLUME_UNITS))
    st.session_state["is_imported"] = False
    # A new key is the only way to empty a file uploader.
    st.session_state["upload_version"] = st.session_state.get("upload_version", 0) + 1


def _request_retry() -> None:
    st.session_state["retry_verify"] = True


def main() -> None:
    st.set_page_config(page_title="Alcohol Label Checker", page_icon="🥃")
    st.title("Alcohol Label Checker")
    st.info(
        "Scope: English-language U.S. distilled-spirit labels, one application "
        f"at a time, with one or two JPEG/PNG images (up to {MAX_IMAGES})."
    )
    st.info(
        "Implemented checks: brand, class/type, alcohol content, net contents, "
        "producer name and address, country of origin for imports, warning "
        "wording, uppercase heading, and warning heading and body font weight. "
        "Font weight is judged visually from the image, not from the text; "
        "physical type size is not checked. When weight is unclear, the check "
        "needs review and is not a pass."
    )

    st.subheader("Expected application values")
    application_id = st.text_input("Application ID", key="application_id")
    brand = st.text_input("Brand name", key="brand")
    class_type = st.text_input("Class/type", key="class_type")
    alcohol_content = st.text_input("Alcohol content (% ABV)", key="alcohol_content")
    net_col, unit_col = st.columns([3, 1])
    net_contents = net_col.text_input("Net contents", key="net_contents")
    unit_label = unit_col.selectbox("Unit", list(_VOLUME_UNITS), key="unit")
    producer_name = st.text_input("Producer/bottler name", key="producer_name")
    producer_address = st.text_input("Producer/bottler address", key="producer_address")
    is_imported = st.toggle("Imported product", key="is_imported")
    country_of_origin = ""
    if is_imported:
        country_of_origin = st.text_input(
            "Country of origin (required for imports)", key="country_of_origin"
        )

    st.subheader("Label images")
    files = st.file_uploader(
        "Upload one or two label images (JPEG or PNG)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"upload_{st.session_state.get('upload_version', 0)}",
    )
    uploads = [UploadedImage(f.name, f.getvalue()) for f in files]
    for upload in uploads:
        st.image(upload.data, caption=upload.name, width=320)

    verify_col, clear_col, _ = st.columns([1, 1, 4])
    verify = verify_col.button("Verify", type="primary")
    clear_col.button("Clear form", on_click=_clear_form)
    # Retry sets a flag because Streamlit reruns the script on every click.
    retry = st.session_state.pop("retry_verify", False)
    if verify or retry:
        result = build_application(
            application_id=application_id,
            brand=brand,
            class_type=class_type,
            alcohol_content=alcohol_content,
            net_contents=net_contents,
            net_contents_unit=_VOLUME_UNITS[unit_label],
            producer_name=producer_name,
            producer_address=producer_address,
            is_imported=is_imported,
            country_of_origin=country_of_origin,
            uploads=uploads,
        )
        note = missing_values_note(result.missing_fields)
        if note:
            st.warning(note)
        for line in input_error_actions(result.errors):
            st.error(line)
        if not result.errors:
            with st.spinner("Reading text from label images..."):
                _show_review(result.application, uploads)


def _display(value) -> str:
    if value is None:
        return ""
    if isinstance(value, Measurement):
        unit = {Unit.PERCENT_ABV: "% ABV"}.get(value.unit, f" {value.unit.value}")
        return f"{value.value}{unit}"
    return str(value)


def _show_review(application, uploads: list[UploadedImage]) -> None:
    extraction = extract_application(
        application.images,
        [upload.data for upload in uploads],
    )
    if extraction.metadata:
        st.caption(
            f"Extraction: {extraction.metadata.provider} / {extraction.metadata.model} "
            f"(prompt {extraction.metadata.prompt_id}, schema {extraction.metadata.schema_id})"
        )
    if extraction.request_timings:
        request_latencies = ", ".join(
            f"{timing.image_id}: {timing.elapsed_seconds:.2f}s"
            for timing in extraction.request_timings
        )
        st.caption(f"OpenAI Responses API request latency: {request_latencies}")
    for error in extraction.errors:
        st.error(error.message)

    if extraction.fields:
        with st.expander("Observed label fields", expanded=False):
            headers = st.columns([1.2, 1, 5])
            headers[0].markdown("**Field**")
            headers[1].markdown("**State**")
            headers[2].markdown("**Observations**")
            for index, field in enumerate(extraction.fields):
                field_column, state_column, observation_column = st.columns([1.2, 1, 5])
                field_column.write(field.field_id.value.replace("_", " "))
                state_column.write(field.state.value.replace("_", " "))
                with observation_column:
                    for observation in field.observations:
                        st.text(
                            f"{observation.raw_text} (image {observation.image_id})"
                        )
                    if field.explanation:
                        st.caption(f"Note: {field.explanation}")
                if index < len(extraction.fields) - 1:
                    st.divider()

    response = review_after_extraction(
        application, extraction.errors, extraction.fields, extraction.warning_styles
    )
    results = response.check_results
    summary = summarize(response)
    names = image_names(application.images)
    if summary.all_clear:
        st.success(f"# :green[✔] {summary.headline}\n\n{summary.counts_text}")
    else:
        problems = "\n\n".join(summary.problems)
        st.warning(
            f"# :red[✖] {summary.headline}\n\n{summary.counts_text}\n\n{problems}"
        )
    guidance = failure_guidance(extraction.errors)
    next_steps = (*guidance.lines, *evidence_actions(response, extraction.fields))
    if next_steps:
        st.subheader("What to do next")
        for step in next_steps:
            st.markdown(f"- {step}")
    if guidance.can_retry:
        st.button("Retry", key="retry_button", on_click=_request_retry)
    table = pd.DataFrame(
        {
            "Check": [check_label(r.check_id) for r in results],
            "Status": [r.outcome.value.replace("_", " ") for r in results],
            "Expected": [_display(r.expected_value) for r in results],
            "Observed": [_display(r.observed_value) for r in results],
            "Evidence (image)": [evidence_names(r, names) for r in results],
            "Reason": [r.explanation or "" for r in results],
        }
    )
    st.table(
        table.style.map(
            lambda status: _STATUS_STYLES.get(status, ""),
            subset=["Status"],
        )
    )
    _show_label_previews(application, uploads, names)
    _show_style_review(application, uploads, response)


def _show_label_previews(
    application, uploads: list[UploadedImage], names: dict[str, str]
) -> None:
    st.subheader("Label images reviewed")
    columns = st.columns(len(uploads))
    for column, image, upload in zip(columns, application.images, uploads, strict=True):
        column.image(
            upload.data,
            caption=f"{names[image.image_id]} is {image.image_id}",
            alt=f"Label image {names[image.image_id]}",
            width="stretch",
        )


def _show_style_review(application, uploads: list[UploadedImage], response) -> None:
    items = unresolved_style_checks(
        response, [image.image_id for image in application.images]
    )
    if not items:
        return
    by_image: dict[str, list] = {}
    for result, image_ids in items:
        for image_id in image_ids:
            by_image.setdefault(image_id, []).append(result)
    originals = {
        image.image_id: upload
        for image, upload in zip(application.images, uploads, strict=True)
    }
    st.subheader("Visual review needed: warning font weight")
    st.write(
        "Font weight could not be settled automatically. Compare the warning "
        "heading with the warning text in the original image and decide. This "
        "is a manual review, not an automated pass."
    )
    for image_id, results in by_image.items():
        upload = originals[image_id]
        image_column, reason_column = st.columns([3, 2])
        image_column.image(
            upload.data,
            caption=f"Original image {upload.name} ({image_id})",
            alt=f"Original label image {upload.name}",
            width="stretch",
        )
        with reason_column:
            for result in results:
                name = result.check_id.value.replace("_", " ")
                st.markdown(f"**{name}: needs review**")
                st.write(result.explanation)


main()
