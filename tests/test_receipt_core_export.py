"""Unit tests for receipt_core.export — HTML proof pack generation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from receipt_core.export import build_proof_pack_html
from receipt_core.schema import (
    Artifact,
    CustodySummary,
    ProofRecord,
    Receipt,
    ReceiptType,
)
from receipt_core.validate import CustodyStatus, ValidationResult


def _result(**kw) -> ValidationResult:
    defaults = dict(
        trust_display='100/100',
        custody_status=CustodyStatus.VERIFIED,
        verified_count=2,
        missing_count=0,
        total_count=2,
    )
    defaults.update(kw)
    return ValidationResult(**defaults)


class TestBuildProofPackHtml:
    def test_html_contains_doctype(self):
        r = Receipt(receipt_type=ReceiptType.CLEANUP)
        html = build_proof_pack_html(r, result=_result())
        assert '<!DOCTYPE html>' in html

    def test_html_contains_receipt_type(self):
        r = Receipt(receipt_type=ReceiptType.PRUNE)
        html = build_proof_pack_html(r, result=_result(
            trust_display='n/a', custody_status=CustodyStatus.NO_ARTIFACT_PATHS))
        assert 'Prune' in html

    def test_html_contains_raw_receipt_escaped(self):
        r = Receipt(
            receipt_type=ReceiptType.CLEANUP,
            raw_text='<script>alert("xss")</script>',
        )
        html = build_proof_pack_html(r, result=_result())
        assert '<script>' not in html
        assert '&lt;script&gt;' in html

    def test_html_includes_trust_score(self):
        r = Receipt(receipt_type=ReceiptType.CLEANUP)
        html = build_proof_pack_html(r, result=_result())
        assert '100/100' in html

    def test_html_includes_missing_trust(self):
        r = Receipt(receipt_type=ReceiptType.CLEANUP)
        html = build_proof_pack_html(r, result=_result(
            trust_display='99/100', custody_status=CustodyStatus.GAPS_DETECTED,
            verified_count=9, missing_count=1, total_count=10,
            errors=['Custody gaps detected: 1/10 artifact(s) missing from archive'],
        ))
        assert '99/100' in html
        assert 'trust-gap' in html
        assert 'Gaps detected' in html

    def test_html_includes_warnings(self):
        r = Receipt(
            receipt_type=ReceiptType.UNKNOWN_LEGACY,
            warnings=['created_at missing', 'no structured artifact rows found'],
        )
        html = build_proof_pack_html(r)

        assert 'Warnings / Gaps' in html
        assert 'created_at missing' in html
        assert 'no structured artifact rows found' in html

    def test_html_includes_validation_warnings(self):
        r = Receipt(receipt_type=ReceiptType.CLEANUP)
        result = _result()
        result.warnings = ['No custody data available']
        html = build_proof_pack_html(r, result=result)
        assert 'No custody data available' in html

    def test_html_includes_custody_errors(self):
        r = Receipt(receipt_type=ReceiptType.CLEANUP)
        result = _result(
            custody_status=CustodyStatus.GAPS_DETECTED,
            verified_count=1, missing_count=2, total_count=3,
            errors=[
                'Custody gaps detected: 2/3 artifact(s) missing from archive',
                '  missing: C:\\gone\\a.zip',
            ],
        )
        html = build_proof_pack_html(r, result=result)
        assert 'Custody Gaps' in html
        assert 'C:\\gone\\a.zip' in html

    def test_html_no_custody_when_none(self):
        r = Receipt(receipt_type=ReceiptType.CLEANUP)
        html = build_proof_pack_html(r, result=None)
        assert 'No custody data available' in html

    def test_html_includes_local_only_footer(self):
        r = Receipt(receipt_type=ReceiptType.CLEANUP)
        html = build_proof_pack_html(r, result=_result())
        assert 'local-only' in html.lower()
        assert 'no account' in html.lower() or 'No account' in html

    def test_html_includes_summary_stats(self):
        r = Receipt(
            receipt_type=ReceiptType.CLEANUP,
            created_at='2026-01-01 10:00:00',
            producer_app='Cleanroom',
            producer_version='1.0.4',
            artifacts=[Artifact(source_path='C:\\a.bin', size_bytes=500)],
        )
        html = build_proof_pack_html(r, result=_result(total_count=1))
        assert '2026-01-01' in html
        assert 'Cleanroom' in html
        assert '1.0.4' in html
        assert '500.0B' in html
