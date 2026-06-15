"""RECEIPT Core validator — custody verification and honest trust scoring.

Operates on a parsed :class:`Receipt` schema object.  Never claims
verified status for unknown evidence.  Gaps are surfaced, not hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from receipt_core.schema import Receipt, ReceiptType


class ValidationStatus(str, Enum):
    VALID = "valid"
    WARNINGS = "warnings"
    ERRORS = "errors"


class CustodyStatus(str, Enum):
    VERIFIED = "verified"
    GAPS_DETECTED = "gaps_detected"
    PARTIAL_RECEIPT = "partial_receipt"
    NO_ARTIFACT_PATHS = "no_artifact_paths"
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    """Outcome of validating a single receipt."""
    status: ValidationStatus = ValidationStatus.VALID
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    trust_display: str = "0/100"
    custody_status: CustodyStatus = CustodyStatus.UNKNOWN
    verified_count: int = 0
    missing_count: int = 0
    total_count: int = 0


def validate(receipt: Receipt) -> ValidationResult:
    """Run full validation against a parsed receipt."""
    result = ValidationResult()

    # --- trust ---
    _compute_trust(receipt, result)

    # --- custody ---
    _compute_custody(receipt, result)

    # --- aggregate ---
    if result.errors:
        result.status = ValidationStatus.ERRORS
    elif result.warnings:
        result.status = ValidationStatus.WARNINGS

    return result


# ---------------------------------------------------------------------------
# trust
# ---------------------------------------------------------------------------


def _compute_trust(receipt: Receipt, result: ValidationResult) -> None:
    trust = receipt.proof
    if trust is None or trust.custody is None:
        result.trust_display = _trust_label(receipt)
        if receipt.receipt_type == ReceiptType.UNKNOWN_LEGACY:
            result.warnings.append("No custody data available — receipt is untyped or legacy")
        return

    custody = trust.custody
    total = max(custody.total, 0)
    verified = max(custody.verified, 0)
    missing = max(custody.missing, 0)
    result.total_count = total
    result.verified_count = verified
    result.missing_count = missing

    if total == 0:
        result.trust_display = "0/100"
        result.warnings.append("Custody total is zero — nothing to verify")
        return

    score = _trust_score(verified, total, missing)
    result.trust_display = f"{score}/100"


def _trust_score(verified: int, total: int, missing: int) -> int:
    """Honest trust score: never 100 when anything is missing."""
    if total <= 0:
        return 0
    raw = int(round(100 * verified / total))
    if missing > 0:
        return min(raw, 99)
    return raw


def _trust_label(receipt: Receipt) -> str:
    """Fallback display when no custody proof exists."""
    if receipt.receipt_type == ReceiptType.PRUNE:
        return "n/a"
    if receipt.receipt_type == ReceiptType.UNKNOWN_LEGACY:
        return "Unknown"
    if receipt.legacy:
        return "Legacy"
    return "n/a"


# ---------------------------------------------------------------------------
# custody
# ---------------------------------------------------------------------------


def _compute_custody(receipt: Receipt, result: ValidationResult) -> None:
    artifacts = [a for a in receipt.artifacts
                 if a.archive_path and a.action != 'summary']
    if not artifacts:
        result.custody_status = CustodyStatus.NO_ARTIFACT_PATHS
        result.warnings.append(
            "No individual artifact paths found — "
            "custody check requires per-item archive paths"
        )
        return

    verified = 0
    missing_paths: list[str] = []
    for a in artifacts:
        if Path(a.archive_path).exists():
            verified += 1
        else:
            missing_paths.append(a.archive_path)

    total = len(artifacts)
    missing = total - verified
    result.verified_count = verified
    result.missing_count = missing
    result.total_count = total

    if missing == 0:
        result.custody_status = CustodyStatus.VERIFIED
    else:
        result.custody_status = CustodyStatus.GAPS_DETECTED
        result.errors.append(
            f"Custody gaps detected: {missing}/{total} artifact(s) missing from archive"
        )
        for mp in missing_paths[:5]:
            result.errors.append(f"  missing: {mp}")
        if len(missing_paths) > 5:
            result.errors.append(f"  … and {len(missing_paths) - 5} more")
