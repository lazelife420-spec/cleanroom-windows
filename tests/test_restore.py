import json
import subprocess
import sys
from pathlib import Path


def test_restore_moves_file(tmp_path):
    ROOT = Path(__file__).resolve().parents[1]
    RESTORE = ROOT / 'restore.py'

    # create archive dir and original path under tmp
    original = tmp_path / 'original_dir' / 'file.txt'
    archive = tmp_path / 'archive_dir' / 'file.txt'
    archive.parent.mkdir(parents=True)
    original.parent.mkdir(parents=True)
    # create the archived file (dest) and ensure original does not exist
    archive.write_text('archived')
    if original.exists():
        original.unlink()

    plan = {'plan_time': 'test', 'archive_dir': str(archive.parent), 'actions': [{'src': str(original), 'dest': str(archive), 'reason': 'test', 'size': 7}]}
    plan_file = tmp_path / 'plan.json'
    plan_file.write_text(json.dumps(plan))

    # run restore in apply mode
    subprocess.run([sys.executable, str(RESTORE), '--log', str(plan_file), '--apply'], capture_output=True, text=True)
    # after apply, the archived file should have been moved to original
    assert original.exists()
    assert not archive.exists()
    # cleanup
    original.unlink()
