import sys
from pathlib import Path

import yaml


def _import_enable_telemetry():
    # ensure project root is on sys.path for imports
    tests_dir = Path(__file__).resolve().parent
    project_dir = tests_dir.parent
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    import enable_telemetry
    return enable_telemetry


def test_enable_telemetry(tmp_path, monkeypatch):
    enable_telemetry = _import_enable_telemetry()
    cfg = tmp_path / "cleanup_config.yaml"
    cfg.write_text("telemetry:\n  enabled: false\n", encoding='utf-8')
    monkeypatch.setattr(enable_telemetry, 'CFG', cfg)
    rc = enable_telemetry.main(enable=True)
    assert rc == 0
    data = yaml.safe_load(cfg.read_text(encoding='utf-8'))
    assert data.get('telemetry', {}).get('enabled') is True


def test_disable_telemetry(tmp_path, monkeypatch):
    enable_telemetry = _import_enable_telemetry()
    cfg = tmp_path / "cleanup_config.yaml"
    cfg.write_text("telemetry:\n  enabled: true\n", encoding='utf-8')
    monkeypatch.setattr(enable_telemetry, 'CFG', cfg)
    rc = enable_telemetry.main(enable=False)
    assert rc == 0
    data = yaml.safe_load(cfg.read_text(encoding='utf-8'))
    assert data.get('telemetry', {}).get('enabled') is False
    
def test_toggle(tmp_path):
    from enable_telemetry import is_opted_in, set_opt_in
    p = tmp_path / 'telemetry.json'
    # point to local telemetry path for test
    import enable_telemetry as et
    old = et.TEL_PATH
    try:
        et.TEL_PATH = p
        assert not is_opted_in()
        assert set_opt_in(True) is True
        assert is_opted_in() is True
        assert set_opt_in(False) is True
        assert is_opted_in() is False
    finally:
        et.TEL_PATH = old
