"""Tests for receipt_desktop — CLI, state, and parse/display integration."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Headless CI may have a broken/partial tk install; probe widget creation.
def _tk_works() -> bool:
    try:
        import customtkinter as ctk
        root = ctk.CTk()
        ctk.CTkButton(root, text='probe')  # loads tk button.tcl
        root.update_idletasks()
        root.destroy()
        return True
    except Exception:
        return False


_HAS_DISPLAY = _tk_works()

_needs_display = pytest.mark.skipif(
    not _HAS_DISPLAY, reason='requires a display (tk available)')


class TestAppCLI:
    def test_parse_args_no_flags(self):
        from receipt_desktop.app import parse_args
        args = parse_args([])
        assert args.receipt_path is None

    def test_parse_args_open_flag(self):
        from receipt_desktop.app import parse_args
        args = parse_args(['--open', r'C:\foo\receipt.cleanroom-receipt'])
        assert args.receipt_path == r'C:\foo\receipt.cleanroom-receipt'

    def test_open_receipt_standalone_missing_file(self, tmp_path):
        from receipt_desktop.app import open_receipt_standalone
        rc = open_receipt_standalone(str(tmp_path / 'nonexistent.cleanroom-receipt'))
        assert rc == 1


class TestViewerState:
    def test_default_state(self):
        from receipt_desktop.state import ViewerState
        s = ViewerState()
        assert s.loaded is False
        assert s.has_errors is False
        assert s.trust_display == 'Unknown'
        assert s.artifact_count == 0
        assert s.total_bytes == 0

    def test_state_with_error(self):
        from receipt_desktop.state import ViewerState
        s = ViewerState(error='test error')
        assert s.loaded is False
        assert s.has_errors is True
        assert str(s.error) == 'test error'

    def test_state_with_receipt(self):
        from receipt_core.schema import Artifact, Receipt, ReceiptType
        from receipt_desktop.state import ViewerState

        r = Receipt(
            receipt_type=ReceiptType.CLEANUP,
            artifacts=[Artifact(source_path='C:\\a.txt', size_bytes=100)],
            summary='1 item moved',
            legacy=True,
        )
        s = ViewerState(receipt=r, file_path='C:\\test.cleanroom-receipt')
        assert s.loaded is True
        assert s.artifact_count == 1
        assert s.total_bytes == 100
        assert s.summary == '1 item moved'


class TestParseThenDisplay:
    """Integration: parse a receipt and check ViewerState derivation."""

    def test_cleanup_receipt_populates_state(self):
        from receipt_core.parse import parse_text
        from receipt_core.validate import validate
        from receipt_desktop.state import ViewerState
        from receipt_core import render
        from brand import APP_MOTTO

        text = render.format_receipt(
            [{'src': 'C:\\a.txt', 'dest': 'C:\\a2.txt',
              'reason': 'large-file', 'size': 500, 'when': '2026-01-01T00:00:00'}],
            motto=APP_MOTTO,
        )
        receipt = parse_text(text)
        result = validate(receipt)
        s = ViewerState(receipt=receipt, result=result)

        assert s.loaded is True
        assert s.artifact_count > 0
        assert s.trust_display != ''
        assert s.custody_status in ('verified', 'gaps_detected', 'no_artifact_paths',
                                     'partial_receipt', 'unknown')

    def test_prune_receipt_populates_state(self):
        from receipt_core.parse import parse_text
        from receipt_core.validate import validate
        from receipt_desktop.state import ViewerState
        from receipt_core import render
        from brand import APP_MOTTO

        text = render.format_prune_receipt(
            [{'dest': r'C:\arch\x.zip', 'size': 1024}],
            motto=APP_MOTTO,
        )
        receipt = parse_text(text)
        result = validate(receipt)
        s = ViewerState(receipt=receipt, result=result)

        assert s.loaded is True
        assert receipt.receipt_type.value == 'prune'
        assert len(receipt.artifacts) > 0

    def test_unknown_text_gives_partial_state(self):
        from receipt_core.parse import parse_text
        from receipt_core.validate import validate
        from receipt_desktop.state import ViewerState

        receipt = parse_text('Random content, not a receipt.')
        result = validate(receipt)
        s = ViewerState(receipt=receipt, result=result)

        assert s.loaded is True
        assert receipt.receipt_type.value == 'unknown_legacy'
        assert s.trust_display == 'Unknown'


@_needs_display
class TestCustodySummary:
    """Tests for the _build_custody_summary_text output."""

    def _app_with_cleanup(self, tmp_path, monkeypatch):
        monkeypatch.setattr('customtkinter.CTk.mainloop', lambda s: None)

        from receipt_core import render
        from brand import APP_MOTTO
        from receipt_desktop.viewer import ReceiptViewerApp as App

        f = tmp_path / 'receipt.cleanroom-receipt'
        f.write_text(
            render.format_receipt(
                [{'src': 'C:\\x.txt', 'dest': 'C:\\x2.txt',
                  'reason': 'large-file', 'size': 100,
                  'when': '2026-01-01T00:00:00'}],
                motto=APP_MOTTO,
            ),
            encoding='utf-8',
        )
        app = App()
        app.load_receipt(str(f))
        return app

    def _app_with_prune(self, tmp_path, monkeypatch):
        monkeypatch.setattr('customtkinter.CTk.mainloop', lambda s: None)

        from receipt_core import render
        from brand import APP_MOTTO
        from receipt_desktop.viewer import ReceiptViewerApp as App

        f = tmp_path / 'prune_receipt.cleanroom-receipt'
        f.write_text(
            render.format_prune_receipt(
                [{'dest': r'C:\arch\x.zip', 'size': 1024}],
                motto=APP_MOTTO,
            ),
            encoding='utf-8',
        )
        app = App()
        app.load_receipt(str(f))
        return app

    def test_prune_receipt_says_pruned(self, tmp_path, monkeypatch):
        app = self._app_with_prune(tmp_path, monkeypatch)
        text = app._build_custody_summary_text()
        assert 'Pruned by receipt' in text
        assert 'n/a' in text
        app.destroy()

    def test_cleanup_with_gaps_produces_summary(self, tmp_path, monkeypatch):
        app = self._app_with_cleanup(tmp_path, monkeypatch)
        text = app._build_custody_summary_text()
        assert 'RECEIPT Custody Summary' in text
        assert 'Trust:' in text
        app.destroy()

    def test_summary_includes_trust_score(self, tmp_path, monkeypatch):
        app = self._app_with_cleanup(tmp_path, monkeypatch)
        text = app._build_custody_summary_text()
        assert 'Trust:' in text
        app.destroy()

    def test_summary_for_partial_receipt(self, tmp_path, monkeypatch):
        monkeypatch.setattr('customtkinter.CTk.mainloop', lambda s: None)
        from receipt_desktop.viewer import ReceiptViewerApp as App

        f = tmp_path / 'unknown.cleanroom-receipt'
        f.write_text('Random content, not a receipt.', encoding='utf-8')

        app = App()
        app.load_receipt(str(f))
        text = app._build_custody_summary_text()
        assert 'Unknown' in text or 'Partial' in text
        app.destroy()

    def test_summary_no_receipt_loaded(self, monkeypatch):
        monkeypatch.setattr('customtkinter.CTk.mainloop', lambda s: None)
        from receipt_desktop.viewer import ReceiptViewerApp as App

        app = App()
        text = app._build_custody_summary_text()
        assert 'No receipt loaded' in text
        app.destroy()


@_needs_display
class TestViewerNoTk:
    """Tests that require importing ReceiptViewerApp (needs tk)."""

    def test_viewer_app_can_instantiate_minimal(self, monkeypatch):
        """Smoke: ReceiptViewerApp.__init__ without launching mainloop."""
        monkeypatch.setattr('customtkinter.CTk.mainloop', lambda s: None)
        from receipt_desktop.viewer import ReceiptViewerApp as App

        app = App()
        assert app._state.loaded is False
        app.destroy()

    def test_viewer_load_receipt_updates_title_and_status(self, tmp_path, monkeypatch):
        monkeypatch.setattr('customtkinter.CTk.mainloop', lambda s: None)

        from receipt_core import render
        from brand import APP_MOTTO
        from receipt_desktop.viewer import ReceiptViewerApp as App

        receipt_file = tmp_path / 'receipt_20260101_120000.cleanroom-receipt'
        text = render.format_receipt(
            [{'src': 'C:\\x.txt', 'dest': 'C:\\x2.txt',
              'reason': 'large-file', 'size': 100, 'when': '2026-01-01T00:00:00'}],
            motto=APP_MOTTO,
        )
        receipt_file.write_text(text, encoding='utf-8')

        app = App()
        app.load_receipt(str(receipt_file))
        assert app._state.loaded is True
        assert app._state.receipt is not None
        assert 'receipt_20260101' in app.title()
        app.destroy()

    def test_viewer_load_nonexistent_sets_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr('customtkinter.CTk.mainloop', lambda s: None)
        from receipt_desktop.viewer import ReceiptViewerApp as App

        app = App()
        app.load_receipt(str(tmp_path / 'missing.cleanroom-receipt'))
        assert app._state.has_errors is True
        assert 'File not found' in app._state.error
        app.destroy()

    def test_viewer_parse_legacy_txt(self, tmp_path, monkeypatch):
        monkeypatch.setattr('customtkinter.CTk.mainloop', lambda s: None)

        from receipt_core import render
        from brand import APP_MOTTO
        from receipt_desktop.viewer import ReceiptViewerApp as App

        legacy = tmp_path / 'receipt_20260101_120000.txt'
        legacy.write_text(
            render.format_receipt(
                [{'src': 'C:\\b.txt', 'dest': 'C:\\b2.txt',
                  'reason': 'zero-byte', 'size': 0,
                  'when': '2026-01-01T00:00:00'}],
                motto=APP_MOTTO,
            ),
            encoding='utf-8',
        )

        app = App()
        app.load_receipt(str(legacy))
        assert app._state.loaded is True
        assert app._state.receipt is not None
        assert app._state.receipt.legacy is True
        app.destroy()
