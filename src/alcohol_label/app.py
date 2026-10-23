"""Streamlit entry point: expected-value form, label upload and Verify."""

import streamlit as st

from alcohol_label.intake import MAX_IMAGES, UploadedImage, build_application
from alcohol_label.review import review_without_extraction
from alcohol_label.schemas import CheckOutcome, Unit

_VOLUME_UNITS = {
    "mL": Unit.MILLILITER,
    "L": Unit.LITER,
    "fl oz": Unit.FLUID_OUNCE,
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


def main() -> None:
    st.set_page_config(page_title="Alcohol Label Verification")
    st.title("Alcohol Label Verification")
    st.info(
        "Scope: English-language U.S. distilled-spirit labels, one application "
        f"at a time, with one or two JPEG/PNG images (up to {MAX_IMAGES})."
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
            _show_review(result.application)


def _show_review(application) -> None:
    response = review_without_extraction(application)
    results = response.check_results
    unresolved = sum(r.outcome is CheckOutcome.NOT_EVALUATED for r in results)
    if response.all_clear:
        st.success("All supported checks passed.")
    else:
        st.warning(
            f"Incomplete: {unresolved} of {len(results)} checks not evaluated. "
            "This is not a pass."
        )
    st.table(
        {
            "Check": [r.check_id.value.replace("_", " ") for r in results],
            "Status": [r.outcome.value.replace("_", " ") for r in results],
            "Reason": [r.explanation for r in results],
        }
    )


main()
