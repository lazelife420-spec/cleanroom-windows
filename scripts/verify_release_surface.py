#!/usr/bin/env python3
"""Fail CI when public release surfaces drift from Cleanroom proof-loop doctrine."""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPO = 'Z3r0DayZion-install/cleanroom-windows'

PUBLIC_DOC_GLOBS = ('README.md', 'docs/RELEASE-v*.md')

FORBIDDEN_PUBLIC = (
    'Smart Clean',
    'SmartClean',
    'smart_clean',
    'Optimizer',
    'Dashboard',
    'Registry Health',
    'old junk',
    'Health:',
    'Startup:',
    'Programs:',
)

# Standalone UI label — not CLI/internal names (apply_actions, --apply, apply_cleanup).
FORBIDDEN_UI_APPLY = re.compile(r"""text\s*=\s*['"][^'"]*\bApply\b[^'"]*['"]""")

FORBIDDEN_UI_TERMS = FORBIDDEN_PUBLIC + ('Apply',)

ALLOWLIST_FILES = {
    ROOT / 'CHANGELOG.md',
    ROOT / 'HANDOFF.md',
    ROOT / 'brand.py',
}

SCREENSHOTS = (
    'cleanroom-review.png',
    'cleanroom-activity-ledger.png',
    'cleanroom-proof-pack-demo.png',
)

RELEASE_URL = re.compile(
    rf'https://github\.com/{re.escape(REPO)}/releases/download/v[\d.]+/',
)
RAW_GH_URL = re.compile(
    rf'https://raw\.githubusercontent\.com/{re.escape(REPO)}/',
)

UI_FILES = (
    ROOT / 'startup_manager_gui.py',
    ROOT / 'recommendations.py',
    ROOT / 'receipts.py',
    ROOT / 'opt_in_gui.py',
)


def _fail(msg: str) -> None:
    print(f'FAIL: {msg}', file=sys.stderr)


def _ok(msg: str) -> None:
    print(f'OK: {msg}')


def _public_doc_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern in PUBLIC_DOC_GLOBS:
        if '*' in pattern:
            paths.extend(ROOT.glob(pattern))
        else:
            p = ROOT / pattern
            if p.is_file():
                paths.append(p)
    return sorted(set(paths))


def _migration_context_allowed(path: Path, line: str, term: str) -> bool:
    """README upgrade note may mention legacy Smart Clean paths."""
    if path.name != 'README.md':
        return False
    if term not in ('Smart Clean', 'SmartClean'):
        return False
    low = line.lower()
    return 'upgrading' in low or 'migration' in low


def scan_public_docs() -> bool:
    ok = True
    for path in _public_doc_paths():
        text = path.read_text(encoding='utf-8')
        rel = path.relative_to(ROOT).as_posix()
        for line_no, line in enumerate(text.splitlines(), 1):
            for term in FORBIDDEN_PUBLIC:
                if term not in line:
                    continue
                if _migration_context_allowed(path, line, term):
                    continue
                _fail(f'{rel}:{line_no} contains forbidden public term {term!r}')
                ok = False
        if FORBIDDEN_UI_APPLY.search(text):
            _fail(f'{rel} contains forbidden Apply UI label')
            ok = False
        for m in RAW_GH_URL.finditer(text):
            if any(ext in m.group(0) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                _fail(f'{rel} uses raw.githubusercontent.com screenshot URL: {m.group(0)}')
                ok = False
        for line_no, line in enumerate(text.splitlines(), 1):
            if '![' in line and '](http' in line and 'releases/download/v' not in line:
                if any(ext in line for ext in ('.png', '.jpg', '.jpeg')):
                    _fail(f'{rel}:{line_no} screenshot link must use releases/download/vX.Y.Z/ URLs')
                    ok = False
    if ok:
        _ok('Public docs clean (no forbidden terms, no raw screenshot URLs)')
    return ok


def scan_release_docs() -> bool:
    ok = True
    release_docs = sorted(ROOT.glob('docs/RELEASE-v*.md'))
    if not release_docs:
        _fail('No docs/RELEASE-v*.md release notes found')
        return False
    for path in release_docs:
        text = path.read_text(encoding='utf-8')
        rel = path.relative_to(ROOT).as_posix()
        if 'proof-loop' not in text.lower() and 'archive-first' not in text.lower():
            _fail(f'{rel} missing proof-loop positioning (archive-first / proof-loop)')
            ok = False
        if not RELEASE_URL.search(text):
            _fail(f'{rel} must embed releases/download/vX.Y.Z/ screenshot URLs')
            ok = False
    if ok:
        _ok(f'Release docs scan passed ({len(release_docs)} file(s))')
    return ok


def scan_screenshot_assets() -> bool:
    ok = True
    shot_dir = ROOT / 'assets' / 'screenshots'
    for name in SCREENSHOTS:
        path = shot_dir / name
        if not path.is_file() or path.stat().st_size < 1024:
            _fail(f'Missing or empty screenshot: assets/screenshots/{name}')
            ok = False
    demo = ROOT / 'docs' / 'demo' / 'cleanroom-proof-pack-demo.html'
    if not demo.is_file():
        _fail('Missing docs/demo/cleanroom-proof-pack-demo.html')
        ok = False
    elif 'CUSTODY VERIFIED' not in demo.read_text(encoding='utf-8'):
        _fail('Demo Proof Pack HTML missing CUSTODY VERIFIED banner')
        ok = False
    if ok:
        _ok('Screenshot assets and demo Proof Pack present')
    return ok


def scan_forbidden_ui_labels() -> bool:
    ok = True
    for path in UI_FILES:
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        for line_no, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if 'text=' not in line and 'messagebox.' not in line and 'showinfo(' not in line:
                continue
            for term in FORBIDDEN_UI_TERMS:
                if term == 'Apply':
                    if FORBIDDEN_UI_APPLY.search(line):
                        _fail(f'{rel}:{line_no} forbidden UI label Apply')
                        ok = False
                    continue
                if term in line:
                    _fail(f'{rel}:{line_no} forbidden UI label {term!r}')
                    ok = False
    if ok:
        _ok('Forbidden UI label scan passed')
    return ok


def scan_brand_surface() -> bool:
    ok = True
    readme = ROOT / 'README.md'
    if not readme.is_file():
        _fail('README.md missing')
        return False
    text = readme.read_text(encoding='utf-8')
    for needle in ('Cleanroom', 'archive-first', 'proof', REPO):
        if needle not in text:
            _fail(f'README.md missing brand marker {needle!r}')
            ok = False
    if ok:
        _ok('Brand/public surface scan passed')
    return ok


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest().upper()


def verify_checksums(version: str | None = None) -> bool:
    sums_path = ROOT / 'SHA256SUMS.txt'
    if not sums_path.is_file():
        _fail('SHA256SUMS.txt missing')
        return False
    entries: dict[str, str] = {}
    for line in sums_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            _fail(f'Invalid SHA256SUMS line: {line!r}')
            return False
        entries[parts[1]] = parts[0].upper()

    dist = ROOT / 'dist'
    expected: list[tuple[Path, str]] = []
    if version:
        installer = dist / f'Cleanroom-Setup-{version}.exe'
        if installer.is_file():
            expected.append((installer, installer.name))
    else:
        expected.extend((p, p.name) for p in sorted(dist.glob('Cleanroom-Setup-*.exe')))
    portable = dist / 'Cleanroom' / 'Cleanroom.exe'
    if portable.is_file():
        expected.append((portable, 'Cleanroom/Cleanroom.exe'))

    if not expected:
        _fail('No built artifacts in dist/ to verify')
        return False

    ok = True
    for path, name in expected:
        if name not in entries:
            _fail(f'SHA256SUMS.txt missing entry for {name}')
            ok = False
            continue
        actual = _sha256(path)
        if actual != entries[name]:
            _fail(f'Checksum mismatch for {name}: file={actual} sums={entries[name]}')
            ok = False
    if ok:
        _ok('SHA256SUMS.txt matches built artifacts')
    return ok


def verify_tag_alignment(tag: str, *, verify_artifacts: bool = False) -> bool:
    """Fail if tag, brand version, docs, README URLs, or artifacts drift."""
    import brand  # noqa: WPS433

    version = tag.lstrip('vV')
    ok = True
    url_needle = f'releases/download/v{version}/'
    installer_name = f'Cleanroom-Setup-{version}.exe'

    if brand.APP_VERSION != version:
        _fail(f'Tag {tag!r} ({version}) does not match brand.APP_VERSION={brand.APP_VERSION!r}')
        ok = False

    notes = ROOT / 'docs' / f'RELEASE-v{version}.md'
    if not notes.is_file():
        _fail(f'Missing release notes for tag: {notes.name}')
        ok = False
    else:
        notes_text = notes.read_text(encoding='utf-8')
        if url_needle not in notes_text:
            _fail(f'{notes.name} must use {url_needle} screenshot URLs')
            ok = False
        if installer_name not in notes_text:
            _fail(f'{notes.name} must reference {installer_name}')
            ok = False

    readme = ROOT / 'README.md'
    if readme.is_file():
        readme_text = readme.read_text(encoding='utf-8')
        if url_needle not in readme_text:
            _fail(f'README.md must link screenshots to {url_needle}')
            ok = False
        if installer_name not in readme_text:
            _fail(f'README.md must reference {installer_name} for provenance docs')
            ok = False

    sums = ROOT / 'SHA256SUMS.txt'
    if sums.is_file():
        lines = sums.read_text(encoding='utf-8').splitlines()
        if lines and f'v{version}' not in lines[0]:
            _fail(f'SHA256SUMS.txt header must reference v{version}')
            ok = False

    if verify_artifacts:
        installer = ROOT / 'dist' / installer_name
        if not installer.is_file():
            _fail(f'Expected installer artifact: dist/{installer_name}')
            ok = False
        if sums.is_file() and installer_name not in sums.read_text(encoding='utf-8'):
            _fail(f'SHA256SUMS.txt must list {installer_name}')
            ok = False

    if ok:
        _ok(f'Tag {tag} alignment verified (brand, docs, README, checksums)')
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-checksums', action='store_true',
                        help='Require dist/ artifacts and validate SHA256SUMS.txt')
    parser.add_argument('--tag', default='', help='Release tag (e.g. v1.0.1) for version alignment')
    parser.add_argument('--version', default='', help='Release version (e.g. 1.0.1)')
    parser.add_argument('--verify-artifacts', action='store_true',
                        help='Require dist/ installer matching tag version')
    args = parser.parse_args()

    results = [
        scan_brand_surface(),
        scan_public_docs(),
        scan_release_docs(),
        scan_screenshot_assets(),
        scan_forbidden_ui_labels(),
    ]
    if args.tag:
        results.append(verify_tag_alignment(args.tag, verify_artifacts=args.verify_artifacts))
    if args.verify_checksums:
        version = args.version or (args.tag.lstrip('vV') if args.tag else None)
        results.append(verify_checksums(version))

    print()
    if all(results):
        print('Release surface verification PASSED')
        return 0
    print('Release surface verification FAILED', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
