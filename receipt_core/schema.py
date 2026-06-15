"""RECEIPT Core schema — stable, versioned machine-readable receipt model.

No Cleanroom GUI imports.  No destructive claims.  Legacy receipts must
parse as partial receipts, not failures.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

RECEIPT_SCHEMA_VERSION = 1


class ReceiptType(str, Enum):
    CLEANUP = "cleanup"
    PREVIEW = "preview"
    PRUNE = "prune"
    MIGRATION = "migration"
    CUSTODY_CHECK = "custody_check"
    PROOF_PACK = "proof_pack"
    UNKNOWN_LEGACY = "unknown_legacy"


class HashStatus(str, Enum):
    VERIFIED = "verified"
    MISSING = "missing"
    NOT_COMPUTED = "not_computed"
    MISMATCH = "mismatch"


@dataclass
class Artifact:
    """One archived item as recorded in a receipt."""
    source_path: str
    archive_path: str = ""
    size_bytes: int = 0
    reason: str = ""
    action: str = ""              # moved, pruned, copied, …
    exists: bool | None = None    # None = not checked
    hash_sha256: str = ""
    hash_status: HashStatus = HashStatus.NOT_COMPUTED


@dataclass
class CustodySummary:
    """Snapshot of what the receipt claims and what is actually present."""
    total: int = 0
    verified: int = 0
    missing: int = 0
    missing_items: list[str] = field(default_factory=list)
    bytes_in_custody: int = 0


@dataclass
class ProofRecord:
    """OS-measured before/after free-space snapshot."""
    before_free: int = 0
    after_free: int = 0
    measured_delta: int = 0
    claimed_bytes: int = 0
    custody: CustodySummary | None = None


@dataclass
class Receipt:
    """The canonical receipt model — what every receipt becomes after parsing."""
    receipt_version: int = RECEIPT_SCHEMA_VERSION
    receipt_id: str = ""
    producer_app: str = "Cleanroom"
    producer_version: str = ""
    receipt_type: ReceiptType = ReceiptType.UNKNOWN_LEGACY
    created_at: str = ""                      # ISO-8601
    action_id: str = ""
    summary: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    proof: ProofRecord | None = None
    source_path: str = ""                     # original file location
    raw_text: str = ""                        # verbatim receipt content
    legacy: bool = False                      # True when parsed from old-format .txt
    warnings: list[str] = field(default_factory=list)

    # --- convenience helpers ---

    @property
    def artifact_count(self) -> int:
        return len(self.artifacts)

    @property
    def total_bytes_claimed(self) -> int:
        claimed = 0
        for a in self.artifacts:
            try:
                claimed += a.size_bytes
            except (TypeError, ValueError):
                pass
        return claimed

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (no dataclass nesting)."""
        d: dict[str, Any] = {
            "receipt_version": self.receipt_version,
            "receipt_id": self.receipt_id,
            "producer_app": self.producer_app,
            "producer_version": self.producer_version,
            "receipt_type": self.receipt_type.value,
            "created_at": self.created_at,
            "action_id": self.action_id,
            "summary": self.summary,
            "artifacts": [asdict(a) for a in self.artifacts],
            "source_path": self.source_path,
            "raw_text": self.raw_text,
            "legacy": self.legacy,
            "warnings": self.warnings[:],
        }
        if self.proof is not None:
            d["proof"] = {
                "before_free": self.proof.before_free,
                "after_free": self.proof.after_free,
                "measured_delta": self.proof.measured_delta,
                "claimed_bytes": self.proof.claimed_bytes,
                "custody": asdict(self.proof.custody) if self.proof.custody else None,
            }
        return d
