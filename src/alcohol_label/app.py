"""Streamlit entry point: expected-value form, label upload and Verify."""

import pandas as pd
import streamlit as st

from alcohol_label.extraction import extract_application
from alcohol_label.intake import MAX_IMAGES, UploadedImage, build_application
from alcohol_label.review import review_after_extraction
from alcohol_label.schemas import CheckOutcome, Measurement, Unit

_VOLUME_UNITS = {
    "mL": Unit.MILLILITER,
    "L": Unit.LITER,
    "fl oz": Unit.FLUID_OUNCE,
}
_STATUS_STYLES = {"match": "color: green", "discrepancy": "color: red"}
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


def main() -> None:
    st.set_page_config(page_title="Alcohol Label Verification", page_icon="🥃")
    st.title("Alcohol Label Verification")
    st.info(
        "Scope: English-language U.S. distilled-spirit labels, one application "
        f"at a time, with one or two JPEG/PNG images (up to {MAX_IMAGES})."
    )
    st.info(
        "Implemented checks: brand, class/type, alcohol content, net contents, "
        "producer name and address, and country of origin for imports. Warning "
        "checks are not implemented yet and are shown as not evaluated; they are "
        "not a pass."
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
    if verify:
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
        if result.missing_fields:
            names = ", ".join(f.value.replace("_", " ") for f in result.missing_fields)
            st.error(f"Missing expected values: {names}")
        if result.errors:
            for error in result.errors:
                st.error(error)
        else:
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
        application, extraction.errors, extraction.fields
    )
    results = response.check_results
    counts = {o: sum(r.outcome is o for r in results) for o in CheckOutcome}
    if response.all_clear:
        st.success("# :green[✔] Pass\n\nAll supported checks passed.")
    else:
        extraction_status = (
            " Extraction encountered processing failures." if extraction.errors else ""
        )
        st.warning(
            "# :red[✖] Not a pass\n\n"
            f"{counts[CheckOutcome.DISCREPANCY]} discrepancy, "
            f"{counts[CheckOutcome.NEEDS_REVIEW]} need review, "
            f"{counts[CheckOutcome.NOT_EVALUATED]} not evaluated of "
            f"{len(results)} checks.{extraction_status}"
        )
    table = pd.DataFrame(
        {
            "Check": [r.check_id.value.replace("_", " ") for r in results],
            "Status": [r.outcome.value.replace("_", " ") for r in results],
            "Expected": [_display(r.expected_value) for r in results],
            "Observed": [_display(r.observed_value) for r in results],
            "Evidence (image)": [
                ", ".join(dict.fromkeys(e.image_id for e in r.evidence))
                for r in results
            ],
            "Reason": [r.explanation or "" for r in results],
        }
    )
    st.table(
        table.style.map(
            lambda status: _STATUS_STYLES.get(status, ""),
            subset=["Status"],
        )
    )


main()
