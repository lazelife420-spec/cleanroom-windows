"""Unit tests for receipt_core.validate — custody + trust honesty."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from receipt_core.schema import (
    Artifact,
    CustodySummary,
    ProofRecord,
    Receipt,
    ReceiptType,
)
from receipt_core.validate import (
    CustodyStatus,
    ValidationStatus,
    validate,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _cleanup_receipt(artifacts=None, proof=None, legacy=False):
    return Receipt(
        receipt_type=ReceiptType.CLEANUP,
        artifacts=artifacts or [],
        proof=proof,
        legacy=legacy,
    )


def _proof(total=5, verified=5, missing=0):
    return ProofRecord(
        custody=CustodySummary(total=total, verified=verified, missing=missing),
    )


# ---------------------------------------------------------------------------
# trust
# ---------------------------------------------------------------------------


class TestTrustScoring:
    def test_all_present_gives_100(self):
        r = _cleanup_receipt(proof=_proof(5, 5, 0))
        result = validate(r)
        assert result.trust_display == "100/100"

    def test_single_missing_is_never_100(self):
        r = _cleanup_receipt(proof=_proof(10, 9, 1))
        result = validate(r)
        assert result.trust_display != "100/100"
        assert "/100" in result.trust_display

    def test_half_missing_is_below_100(self):
        r = _cleanup_receipt(proof=_proof(10, 5, 5))
        result = validate(r)
        assert result.trust_display != "100/100"
        assert result.trust_display == "50/100"

    def test_all_missing_is_0(self):
        r = _cleanup_receipt(proof=_proof(3, 0, 3))
        result = validate(r)
        assert result.trust_display == "0/100"

    def test_zero_total_is_0(self):
        r = _cleanup_receipt(proof=_proof(0, 0, 0))
        result = validate(r)
        assert result.trust_display == "0/100"

    def test_unknown_legacy_shows_unknown(self):
        r = Receipt(receipt_type=ReceiptType.UNKNOWN_LEGACY, proof=None)
        result = validate(r)
        assert result.trust_display == "Unknown"

    def test_prune_receipt_shows_na(self):
        r = Receipt(receipt_type=ReceiptType.PRUNE, proof=None)
        result = validate(r)
        assert result.trust_display == "n/a"

    def test_legacy_flag_without_proof_shows_legacy(self):
        r = _cleanup_receipt(legacy=True, proof=None)
        result = validate(r)
        assert result.trust_display == "Legacy"


# ---------------------------------------------------------------------------
# custody
# ---------------------------------------------------------------------------


class TestCustodyVerification:
    def test_all_present_is_verified(self, tmp_path):
        f = tmp_path / 'artifact.bin'
        f.write_bytes(b'data')
        a = Artifact(source_path=str(f), archive_path=str(f), action='moved')
        r = _cleanup_receipt(artifacts=[a])
        result = validate(r)
        assert result.custody_status == CustodyStatus.VERIFIED

    def test_missing_artifact_is_gap(self, tmp_path):
        a = Artifact(source_path=str(tmp_path / 'gone.bin'),
                      archive_path=str(tmp_path / 'gone.bin'),
                      action='moved')
        r = _cleanup_receipt(artifacts=[a])
        result = validate(r)
        assert result.custody_status == CustodyStatus.GAPS_DETECTED
        assert result.missing_count >= 1

    def test_empty_artifacts_is_no_paths(self):
        r = _cleanup_receipt(artifacts=[])
        result = validate(r)
        assert result.custody_status == CustodyStatus.NO_ARTIFACT_PATHS

    def test_summary_only_artifact_is_treated_as_no_paths(self):
        a = Artifact(source_path='', reason='summary', size_bytes=100)
        r = _cleanup_receipt(artifacts=[a])
        result = validate(r)
        # summary rows have no archive_path, so they are filtered out
        assert result.custody_status == CustodyStatus.NO_ARTIFACT_PATHS

    def test_mixed_present_and_missing(self, tmp_path):
        present = tmp_path / 'present.bin'
        present.write_bytes(b'ok')
        a1 = Artifact(source_path=str(present), archive_path=str(present), action='moved')
        a2 = Artifact(source_path=str(tmp_path / 'gone.bin'),
                       archive_path=str(tmp_path / 'gone.bin'),
                       action='moved')
        r = _cleanup_receipt(artifacts=[a1, a2])
        result = validate(r)
        assert result.custody_status == CustodyStatus.GAPS_DETECTED
        assert result.verified_count == 1
        assert result.missing_count == 1


# ---------------------------------------------------------------------------
# status aggregation
# ---------------------------------------------------------------------------


class TestValidationStatus:
    def test_clean_receipt_is_valid(self, tmp_path):
        f = tmp_path / 'clean.bin'
        f.write_bytes(b'hello')
        a = Artifact(source_path=str(f), archive_path=str(f), action='moved')
        r = _cleanup_receipt(artifacts=[a], proof=_proof(1, 1, 0))
        result = validate(r)
        assert result.status == ValidationStatus.VALID

    def test_gaps_give_errors(self):
        a = Artifact(source_path='C:\\gone\\missing.txt',
                      archive_path='C:\\gone\\missing.txt',
                      action='moved')
        r = _cleanup_receipt(artifacts=[a])
        result = validate(r)
        assert result.status == ValidationStatus.ERRORS

    def test_warnings_add_to_status(self):
        r = _cleanup_receipt(proof=_proof(0, 0, 0))
        result = validate(r)
        assert result.status in (ValidationStatus.WARNINGS, ValidationStatus.ERRORS)


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_count_never_exceeds_total(self):
        r = _cleanup_receipt(proof=_proof(5, 3, 2))
        result = validate(r)
        assert result.missing_count <= result.total_count

    def test_prune_does_not_check_filesystem(self, tmp_path):
        f = tmp_path / 'pruned.bin'
        f.write_bytes(b'gone')
        a = Artifact(source_path=str(f), archive_path=str(f), action='pruned')
        r = Receipt(receipt_type=ReceiptType.PRUNE, artifacts=[a])
        result = validate(r)
        # pruned artifacts are expected to be gone — still run the check
        # but trust display is n/a because there's no proof
        assert result.trust_display == "n/a"

    def test_errors_list_contains_missing_paths(self):
        a = Artifact(source_path='Z:\\void\\gone.txt',
                      archive_path='Z:\\void\\gone.txt',
                      action='moved')
        r = _cleanup_receipt(artifacts=[a])
        result = validate(r)
        assert any('gone.txt' in e for e in result.errors)
