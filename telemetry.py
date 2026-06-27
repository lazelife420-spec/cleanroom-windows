import json
from datetime import datetime
from pathlib import Path


def log_event(cfg, event_name, meta=None):
    try:
        tele = cfg.get('telemetry', {})
        if not tele.get('enabled'):
            return
        usage = Path(tele.get('usage_log') or (Path(__file__).parent / 'usage_log.json'))
        entry = {
            'time': datetime.utcnow().isoformat() + 'Z',
            'event': event_name,
            'meta': meta or {}
        }
        data = []
        if usage.exists():
            try:
                data = json.loads(usage.read_text(encoding='utf-8'))
            except Exception:
                data = []
        data.append(entry)
        usage.write_text(json.dumps(data, indent=2), encoding='utf-8')
    except Exception:
        # telemetry must never break the tool
        return
