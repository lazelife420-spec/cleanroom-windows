"""Receipt animation helpers — deterministic disable path."""
import os

from ui.receipt_animation import animations_disabled, play_receipt_animation


def test_animations_disabled_env(monkeypatch):
    monkeypatch.delenv('CLEANROOM_DISABLE_ANIMATIONS', raising=False)
    assert animations_disabled() is False
    monkeypatch.setenv('CLEANROOM_DISABLE_ANIMATIONS', '1')
    assert animations_disabled() is True
    monkeypatch.setenv('CLEANROOM_DISABLE_ANIMATIONS', 'true')
    assert animations_disabled() is True


def test_play_skips_when_disabled(monkeypatch):
    monkeypatch.setenv('CLEANROOM_DISABLE_ANIMATIONS', '1')
    called = []

    play_receipt_animation(None, 'RECEIPT GENERATED', on_complete=lambda: called.append(1))
    assert called == [1]


def test_play_skips_when_panel_missing():
    called = []
    play_receipt_animation(None, 'CUSTODY VERIFIED', on_complete=lambda: called.append(1))
    assert called == [1]
