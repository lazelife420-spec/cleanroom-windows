#!/usr/bin/env python3
"""Export a shareable HTML audit — the proof document no other cleaner ships."""
import html
from datetime import datetime
from pathlib import Path

from ledger import format_trust_score_display


def _human(n):
    sign = '-' if n < 0 else ''
    n = abs(n)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{sign}{n:.1f} {unit}'
        n /= 1024
    return f'{sign}{n:.1f} PB'


def _esc(s):
    return html.escape(str(s or ''), quote=True)


def export_html_audit(feed, custody, summary, trust, output_path, app_version='1.0.0'):
    """Write a self-contained dark HTML audit report. Returns the path."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ok = custody.get('missing', 0) == 0 and custody.get('total', 0) > 0
    status = 'CUSTODY VERIFIED' if ok else ('NO ACTIONS YET' if custody.get('total', 0) == 0 else 'GAPS DETECTED')
    status_color = '#22c55e' if ok else ('#94a3b8' if custody.get('total', 0) == 0 else '#f87171')
    trust_display = format_trust_score_display(
        custody.get('verified', 0),
        custody.get('total', 0),
        custody.get('missing', 0),
    )

    rows = []
    for e in feed[:500]:
        if e.get('kind') == 'restore':
            continue
        badge = '✓' if e.get('present') else '✗'
        badge_cls = 'ok' if e.get('present') else 'bad'
        when = _esc((e.get('when') or '')[:19].replace('T', ' '))
        rows.append(
            f'<tr><td class="{badge_cls}">{badge}</td>'
            f'<td>{when}</td>'
            f'<td>{_esc(e.get("reason"))}</td>'
            f'<td class="mono">{_esc(e.get("src"))}</td>'
            f'<td>{_human(e.get("size", 0))}</td></tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="5" class="muted">No archived actions yet.</td></tr>')

    reason_lines = ''.join(
        f'<li><span>{_esc(r)}</span><strong>{c}</strong></li>'
        for r, c in summary.get('reasons', {}).most_common()
    ) or '<li class="muted">—</li>'

    doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Cleanroom Proof Pack — {now}</title>
<style>
  :root {{ --bg:#0f1419; --card:#1a2332; --text:#e7ecef; --muted:#94a3b8;
           --accent:#22c55e; --bad:#f87171; --border:#334155; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:Segoe UI,system-ui,sans-serif; background:var(--bg);
          color:var(--text); margin:0; padding:32px; line-height:1.5; }}
  h1 {{ font-size:1.75rem; margin:0 0 4px; }}
  .sub {{ color:var(--muted); margin-bottom:24px; }}
  .hero {{ background:var(--card); border:1px solid var(--border); border-radius:12px;
           padding:24px; margin-bottom:20px; }}
  .status {{ font-size:1.4rem; font-weight:700; color:{status_color}; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin-top:16px; }}
  .stat {{ background:#121820; border-radius:8px; padding:14px; text-align:center; }}
  .stat b {{ display:block; font-size:1.5rem; }}
  .stat span {{ color:var(--muted); font-size:0.8rem; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.85rem; }}
  th,td {{ padding:8px 10px; border-bottom:1px solid var(--border); text-align:left; }}
  th {{ color:var(--muted); font-weight:600; }}
  .mono {{ font-family:Consolas,monospace; font-size:0.75rem; word-break:break-all; }}
  .ok {{ color:var(--accent); font-weight:bold; }}
  .bad {{ color:var(--bad); font-weight:bold; }}
  .muted {{ color:var(--muted); }}
  ul.reasons {{ list-style:none; padding:0; }}
  ul.reasons li {{ display:flex; justify-content:space-between; padding:6px 0;
                    border-bottom:1px solid var(--border); }}
  .footer {{ margin-top:24px; color:var(--muted); font-size:0.8rem; }}
  .compare {{ background:#121820; border-radius:8px; padding:16px; margin-top:16px; }}
  .compare li {{ margin:6px 0; }}
</style>
</head>
<body>
<h1>Cleanroom — Proof Pack</h1>
<p class="sub">Generated {now} · v{_esc(app_version)} · independently verifiable</p>

<div class="hero">
  <div class="status">{status}</div>
  <p>Trust score: <strong>{trust_display}</strong> — {custody.get("verified",0)}/{custody.get("total",0)} archived
     artifacts verified on disk ({_human(custody.get("bytes_in_custody",0))} in custody).</p>
  <div class="grid">
    <div class="stat"><b>{summary.get("total_actions",0)}</b><span>Actions logged</span></div>
    <div class="stat"><b>{summary.get("present",0)}</b><span>Restorable now</span></div>
    <div class="stat"><b>{summary.get("missing",0)}</b><span>Missing from archive</span></div>
    <div class="stat"><b>{_human(summary.get("bytes_moved",0))}</b><span>Bytes moved (logged)</span></div>
  </div>
  <div class="compare">
    <strong>Why this matters</strong>
    <ul>
      <li>Other optimizers: &ldquo;Fixed 1,247 registry errors!&rdquo; — no proof, no undo.</li>
      <li>Cleanroom: every row below is a real file or registry export you can restore.</li>
      <li>Missing rows usually mean you pruned the archive or changed files outside the app.</li>
    </ul>
  </div>
</div>

<div class="hero">
  <h2 style="margin-top:0;font-size:1.1rem;">By reason</h2>
  <ul class="reasons">{reason_lines}</ul>
</div>

<div class="hero">
  <h2 style="margin-top:0;font-size:1.1rem;">Activity log (newest first, max 500)</h2>
  <table>
    <thead><tr><th></th><th>When</th><th>Reason</th><th>Source</th><th>Size</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>

<p class="footer">Cleanroom never permanently deletes during normal cleanup — items are archived
or exported to .reg backups. Open the Restore tab or Cleanroom Rewind to roll back.
This report was generated locally; no data left your PC.</p>
</body>
</html>'''
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding='utf-8')
    return out
