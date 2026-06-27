#!/usr/bin/env python3
"""Packaged release dry-run smoke — fresh profile, sandbox demo only.

Validates the built Cleanroom.exe without destructive actions:
  - launch + clean exit
  - --headless-clean on demo folder (archive, receipt, log)
  - --open-receipt on generated receipt
  - no orphan Cleanroom/python GUI process after quit

GUI flows (scan UI, preview modal, archive table, tray) are covered by source
gate scripts on the same commit; this script proves the frozen binary paths.

Usage:
    python scripts/packaged_v105_smoke.py
    python scripts/packaged_v105_smoke.py --exe dist/Cleanroom/Cleanroom.exe
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_EXE = ROOT / 'dist' / 'Cleanroom' / 'Cleanroom.exe'


def _fail(msg: str) -> None:
    print(f'FAIL: {msg}', file=sys.stderr)
    raise SystemExit(1)


def _ok(msg: str) -> None:
    print(f'OK: {msg}')


def _kill_cleanroom_processes() -> None:
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
        "Where-Object { $_.CommandLine -match 'startup_manager_gui|Cleanroom' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; "
        "Get-Process Cleanroom -ErrorAction SilentlyContinue | "
        "ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=False)


def _seed_demo(profile_local: Path) -> tuple[Path, Path]:
    """Return (config_path, log_path) under a fresh LOCALAPPDATA profile."""
    sandbox = Path(os.environ.get('TEMP', tempfile.gettempdir())) / 'cleanroom_v105_packaged_smoke'
    if sandbox.exists():
        import shutil
        shutil.rmtree(sandbox, ignore_errors=True)
    scan = sandbox / 'scan'
    archive = sandbox / 'archive'
    scan.mkdir(parents=True)
    archive.mkdir(parents=True)
    sample = scan / 'demo_stale.zip'
    sample.write_bytes(b'x' * 4096)
    old_ts = time.time() - 45 * 86400
    os.utime(sample, (old_ts, old_ts))

    log_path = sandbox / 'cleanup_log.json'
    log_path.write_text('[]', encoding='utf-8')
    cfg = sandbox / 'config.yaml'
    cfg.write_text(
        f'paths:\n  - "{scan.as_posix()}"\n'
        'age_days:\n  temp: 7\n  installers: 30\n'
        'size_threshold_mb: 0\n'
        "extensions_archive: ['.zip']\n"
        'exclude_patterns: []\nwhitelist: []\n'
        f'archive_dir: "{archive.as_posix()}"\n'
        f'log_file: "{log_path.as_posix()}"\n'
        'confirm_threshold_bytes: 99999999999999\n',
        encoding='utf-8',
    )

    cleanroom = profile_local / 'Cleanroom'
    cleanroom.mkdir(parents=True, exist_ok=True)
    return cfg, log_path


def _launch_smoke(exe: Path, env: dict, seconds: float = 8.0) -> None:
    proc = subprocess.Popen(
        [str(exe)],
        cwd=str(exe.parent),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(seconds)
    if proc.poll() is not None:
        _fail(f'Packaged EXE exited early with code {proc.returncode}')
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    _ok(f'Packaged EXE launch smoke ({seconds:.0f}s, clean terminate)')


def _headless_archive(exe: Path, env: dict, cfg: Path, log_path: Path) -> Path | None:
    import brand

    env = dict(env)
    env['PATH'] = os.environ.get('SystemRoot', r'C:\Windows') + r'\System32'
    proc = subprocess.run(
        [str(exe), '--headless-clean', '--config', str(cfg)],
        cwd=str(exe.parent),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or '')[-600:]
        _fail(f'--headless-clean exit {proc.returncode}: {tail}')
    _ok('--headless-clean archived demo file')

    if not log_path.is_file():
        _fail('cleanup_log.json missing after headless clean')
    entries = json.loads(log_path.read_text(encoding='utf-8'))
    if not entries:
        _fail('cleanup_log.json empty after headless clean')
    _ok(f'Archive log has {len(entries)} entr{"y" if len(entries) == 1 else "ies"}')

    profile_local = Path(env['LOCALAPPDATA'])
    receipts = profile_local / 'Cleanroom' / 'receipts'
    receipt_files = list(receipts.glob('*.txt')) + list(receipts.glob('*.cleanroom-receipt'))
    if not receipt_files:
        _fail('No receipt generated under Cleanroom/receipts')
    _ok('Cleanroom Receipt generated')
    receipt = receipt_files[-1]
    if brand.PROOF_FOUNDRY_BYLINE not in receipt.read_text(encoding='utf-8'):
        _fail('Receipt missing Proof Foundry product attribution')
    _ok('Cleanroom Receipt includes Proof Foundry branding')
    return receipt


def _open_receipt_smoke(exe: Path, env: dict, receipt: Path) -> None:
    env = dict(env)
    proc = subprocess.Popen(
        [str(exe), '--open-receipt', str(receipt)],
        cwd=str(exe.parent),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(4.0)
    if proc.poll() is not None and proc.returncode != 0:
        _fail(f'--open-receipt exit {proc.returncode}')
    proc.terminate()
    try:
        proc.wait(timeout=6)
    except subprocess.TimeoutExpired:
        proc.kill()
    _ok('--open-receipt launched receipt viewer')


def _process_cleanup_check() -> None:
    ps = (
        "$p = Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
        "Where-Object { $_.CommandLine -match 'startup_manager_gui|Cleanroom|cleanroom_v105' }; "
        "$c = Get-Process Cleanroom -ErrorAction SilentlyContinue; "
        "if ($p -or $c) { exit 1 } else { exit 0 }"
    )
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps])
    if r.returncode != 0:
        _fail('Orphan Cleanroom/python GUI process after smoke')
    _ok('Process cleanup — no orphan Cleanroom/python GUI')


def main() -> int:
    import argparse

    import brand

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=DEFAULT_EXE)
    args = parser.parse_args()
    exe: Path = args.exe
    if not exe.is_file():
        _fail(f'Packaged EXE not found: {exe} (run build_exe.ps1 first)')

    internal = exe.parent / '_internal' / 'customtkinter'
    if not internal.is_dir():
        _fail('customtkinter _internal missing in packaged build')

    _kill_cleanroom_processes()
    version_slug = brand.APP_VERSION.replace('.', '-')
    profile = Path(tempfile.mkdtemp(prefix=f'cleanroom-v{version_slug}-smoke-'))
    local = profile / 'LocalAppData'
    local.mkdir()
    env = os.environ.copy()
    env['LOCALAPPDATA'] = str(local)

    _ok(f'Fresh profile LOCALAPPDATA={local}')
    cfg, log_path = _seed_demo(local)

    try:
        _launch_smoke(exe, env)
        receipt = _headless_archive(exe, env, cfg, log_path)
        if receipt:
            _open_receipt_smoke(exe, env, receipt)
        _process_cleanup_check()
    finally:
        _kill_cleanroom_processes()

    print(f'\nPackaged v{brand.APP_VERSION} smoke PASSED')
    print('NOTE: Full GUI flows (scan UI, preview modal, archive table, tray)')
    print('      are validated by source gate scripts on the same commit.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
