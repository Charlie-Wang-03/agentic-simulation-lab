from enum import Enum


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    PARTIAL = "PARTIAL"
    NOT_RUN = "NOT_RUN"


VALID_STATUSES = frozenset(item.value for item in Status)


def normalize_status(value: object) -> str:
    text = str(value or "").upper()
    if "BLOCK" in text:
        return Status.BLOCKED.value
    if text.startswith("PASS"):
        return Status.PASS.value
    if text.startswith("FAIL"):
        return Status.FAIL.value
    if "PARTIAL" in text:
        return Status.PARTIAL.value
    return Status.NOT_RUN.value
