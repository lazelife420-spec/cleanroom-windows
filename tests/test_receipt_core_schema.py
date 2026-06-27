"""Unit tests for receipt_core.schema — receipt model correctness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from receipt_core.schema import (
    RECEIPT_SCHEMA_VERSION,
    Artifact,
    CustodySummary,
    HashStatus,
    ProofRecord,
    Receipt,
    ReceiptType,
)


def test_cleanup_receipt_has_correct_type():
    r = Receipt(receipt_type=ReceiptType.CLEANUP)
    assert r.receipt_type == ReceiptType.CLEANUP
    assert r.receipt_type.value == "cleanup"


def test_prune_receipt_has_correct_type():
    r = Receipt(receipt_type=ReceiptType.PRUNE)
    assert r.receipt_type == ReceiptType.PRUNE


def test_unknown_legacy_is_default():
    r = Receipt()
    assert r.receipt_type == ReceiptType.UNKNOWN_LEGACY
    assert r.legacy is False


def test_legacy_flag_is_explicit():
    r = Receipt(legacy=True, receipt_type=ReceiptType.UNKNOWN_LEGACY)
    assert r.legacy is True


def test_schema_version_is_positive():
    assert RECEIPT_SCHEMA_VERSION >= 1


def test_receipt_defaults_to_current_version():
    r = Receipt()
    assert r.receipt_version == RECEIPT_SCHEMA_VERSION


def test_warnings_default_empty():
    r = Receipt()
    assert r.warnings == []


def test_artifact_defaults():
    a = Artifact(source_path="C:\\test.txt")
    assert a.source_path == "C:\\test.txt"
    assert a.archive_path == ""
    assert a.size_bytes == 0
    assert a.reason == ""
    assert a.action == ""
    assert a.hash_status == HashStatus.NOT_COMPUTED
    assert a.hash_sha256 == ""
    assert a.exists is None


def test_artifact_count():
    r = Receipt(artifacts=[Artifact(source_path="C:\\a.txt"), Artifact(source_path="C:\\b.txt")])
    assert r.artifact_count == 2


def test_total_bytes_claimed_sums_size():
    r = Receipt(artifacts=[
        Artifact(source_path="C:\\a.txt", size_bytes=100),
        Artifact(source_path="C:\\b.txt", size_bytes=200),
    ])
    assert r.total_bytes_claimed == 300


def test_total_bytes_claimed_handles_junk_size():
    r = Receipt(artifacts=[
        Artifact(source_path="C:\\a.txt", size_bytes="not-a-number"),   # type: ignore[arg-type]
    ])
    assert r.total_bytes_claimed == 0   # graceful skip


def test_to_dict_is_json_safe():
    r = Receipt(
        receipt_type=ReceiptType.CLEANUP,
        producer_app="Cleanroom",
        producer_version="1.0.4",
        created_at="2026-06-10T12:00:00",
        summary="43 items moved",
        artifacts=[Artifact(source_path="C:\\junk\\tmp.bin", size_bytes=1024, reason="temp")],
        raw_text="=== RAW RECEIPT ===",
        legacy=False,
        warnings=["hash not verified"],
    )
    d = r.to_dict()
    json_str = json.dumps(d)
    loaded = json.loads(json_str)
    assert loaded["receipt_type"] == "cleanup"
    assert loaded["producer_version"] == "1.0.4"
    assert loaded["legacy"] is False
    assert loaded["warnings"] == ["hash not verified"]
    assert loaded["artifacts"][0]["source_path"] == "C:\\junk\\tmp.bin"


def test_to_dict_without_proof_omits_proof_key():
    r = Receipt(receipt_type=ReceiptType.PRUNE)
    d = r.to_dict()
    # schema v1: proof not present when None
    assert "proof" not in d


def test_to_dict_includes_proof_when_present():
    custody = CustodySummary(total=3, verified=2, missing=1)
    prf = ProofRecord(before_free=1000, after_free=1300, measured_delta=300,
                       claimed_bytes=300, custody=custody)
    r = Receipt(receipt_type=ReceiptType.CUSTODY_CHECK, proof=prf)
    d = r.to_dict()
    assert d["proof"]["before_free"] == 1000
    assert d["proof"]["custody"]["verified"] == 2
    assert d["proof"]["custody"]["missing"] == 1


def test_to_dict_preserves_empty_artifacts():
    r = Receipt(receipt_type=ReceiptType.PREVIEW)
    d = r.to_dict()
    assert d["artifacts"] == []


def test_to_dict_roundtrip_json_stable():
    """Round-tripping through JSON should preserve basic typed fields."""
    custody = CustodySummary(total=5, verified=5, missing=0)
    prf = ProofRecord(before_free=10_000_000, after_free=15_000_000,
                       measured_delta=5_000_000, claimed_bytes=4_800_000,
                       custody=custody)
    r = Receipt(
        receipt_type=ReceiptType.CLEANUP,
        created_at="2026-01-01T00:00:00",
        summary="All clean",
        proof=prf,
        legacy=False,
        warnings=["example warning"],
    )
    js = json.dumps(r.to_dict())
    reloaded = json.loads(js)
    assert reloaded["receipt_type"] == "cleanup"
    assert reloaded["proof"]["custody"]["total"] == 5
    assert reloaded["warnings"] == ["example warning"]
