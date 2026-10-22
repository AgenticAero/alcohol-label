"""Shared identifiers and states for verification data contracts.

Processing failures (timeouts, invalid provider responses) are deliberately not
members of any enum here; they belong to a separate error contract.
"""

from enum import StrEnum


class FieldId(StrEnum):
    """Application fields and raw label text that can be extracted and compared."""

    BRAND = "brand"
    CLASS_TYPE = "class_type"
    ALCOHOL_CONTENT = "alcohol_content"
    NET_CONTENTS = "net_contents"
    PRODUCER_NAME = "producer_name"
    PRODUCER_ADDRESS = "producer_address"
    COUNTRY_OF_ORIGIN = "country_of_origin"
    WARNING_TEXT = "warning_text"


class CheckId(StrEnum):
    """Individual verification checks; each yields one CheckOutcome."""

    BRAND = "brand"
    CLASS_TYPE = "class_type"
    ALCOHOL_CONTENT = "alcohol_content"
    NET_CONTENTS = "net_contents"
    PRODUCER_NAME = "producer_name"
    PRODUCER_ADDRESS = "producer_address"
    COUNTRY_OF_ORIGIN = "country_of_origin"
    WARNING_WORDING = "warning_wording"
    WARNING_HEADING_CASE = "warning_heading_case"
    WARNING_HEADING_BOLD = "warning_heading_bold"
    WARNING_BODY_NOT_BOLD = "warning_body_not_bold"


class CheckOutcome(StrEnum):
    """Result of evaluating one check."""

    MATCH = "match"
    DISCREPANCY = "discrepancy"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"
    NOT_EVALUATED = "not_evaluated"


class ExtractionState(StrEnum):
    """What extraction found for one field in the supplied images."""

    OBSERVED = "observed"
    MISSING = "missing"
    UNCERTAIN = "uncertain"
    CONFLICTING = "conflicting"
