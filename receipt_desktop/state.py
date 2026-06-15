"""RECEIPT Desktop state — a single loaded receipt and its validation result."""
from __future__ import annotations

from dataclasses import dataclass

from receipt_core.schema import Receipt
from receipt_core.validate import ValidationResult


@dataclass
class ViewerState:
    """Holds the currently loaded receipt and derived display state."""

    receipt: Receipt | None = None
    result: ValidationResult | None = None
    file_path: str = ""
    error: str = ""

    @property
    def loaded(self) -> bool:
        return self.receipt is not None

    @property
    def has_errors(self) -> bool:
        return bool(self.error)

    @property
    def summary(self) -> str:
        if self.receipt is None:
            return ""
        return self.receipt.summary or ""

    @property
    def artifact_count(self) -> int:
        if self.receipt is None:
            return 0
        return self.receipt.artifact_count

    @property
    def total_bytes(self) -> int:
        if self.receipt is None:
            return 0
        return self.receipt.total_bytes_claimed

    @property
    def trust_display(self) -> str:
        if self.result is None:
            return "Unknown"
        return self.result.trust_display

    @property
    def custody_status(self) -> str:
        if self.result is None:
            return "unknown"
        return self.result.custody_status.value

    @property
    def verified_count(self) -> int:
        if self.result is None:
            return 0
        return self.result.verified_count

    @property
    def missing_count(self) -> int:
        if self.result is None:
            return 0
        return self.result.missing_count
