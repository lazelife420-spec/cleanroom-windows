#!/usr/bin/env python3
"""Local telemetry opt-in helpers and config toggle CLI."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

TEL_PATH = Path(__file__).parent / 'telemetry.json'
CFG = Path(__file__).parent / 'cleanup_config.yaml'

try:
    import yaml
except Exception:
    yaml = None


def is_opted_in() -> bool:
    try:
        if not TEL_PATH.exists():
            return False
        with open(TEL_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return bool(data.get('opt_in'))
    except Exception:
        return False


def set_opt_in(value: bool) -> bool:
    try:
        payload = {'opt_in': bool(value), 'ts': datetime.now().isoformat()}
        with open(TEL_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        return True
    except Exception:
        return False


def load_yaml(path: Path):
    text = path.read_text(encoding='utf-8')
    if yaml:
        return yaml.safe_load(text)
    import ruamel.yaml as ry

    return ry.YAML().load(text)


def write_yaml(path: Path, obj) -> None:
    if yaml:
        path.write_text(yaml.safe_dump(obj), encoding='utf-8')
        return
    import ruamel.yaml as ry

    ry.YAML().dump(obj, path.open('w', encoding='utf-8'))


def main(enable: bool = True) -> int:
    if not CFG.exists():
        print('Config not found:', CFG)
        return 2
    try:
        cfg = load_yaml(CFG)
    except Exception as exc:
        print('Failed to parse config:', exc)
        return 2
    tele = cfg.get('telemetry') or {}
    tele['enabled'] = bool(enable)
    cfg['telemetry'] = tele
    try:
        write_yaml(CFG, cfg)
    except Exception as exc:
        print('Failed to write config:', exc)
        return 2
    print(f"Telemetry {'enabled' if enable else 'disabled'} in {CFG}")
    return 0


if __name__ == '__main__':
    enabled = True
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ('off', 'false', '0', 'disable'):
            enabled = False
    sys.exit(main(enable=enabled))
