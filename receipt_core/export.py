"""RECEIPT Core proof pack export — local HTML only, self-contained."""
from __future__ import annotations

import html
from datetime import datetime

from receipt_core.schema import Receipt
from receipt_core.validate import CustodyStatus, ValidationResult


def build_proof_pack_html(
    receipt: Receipt,
    result: ValidationResult | None = None,
) -> str:
    """Build a self-contained, local-only HTML proof pack from a receipt.

    Includes parsed summary, custody result, warnings/gaps, and the raw
    receipt text.  No external assets, no CDN, no tracking.
    """
    escaped_raw = html.escape(receipt.raw_text or '(empty receipt)')

    # --- trust ---
    trust = result.trust_display if result else 'Unknown'
    status = result.custody_status if result else None
    verified = result.verified_count if result else 0
    missing = result.missing_count if result else 0
    total = result.total_count if result else 0

    # --- custody block ---
    custody_html = _custody_section(status, trust, verified, missing, total)

    # --- warnings ---
    warnings_html = ''
    all_warnings = list(receipt.warnings)
    if result:
        all_warnings.extend(result.warnings)
    if all_warnings:
        items = '\n'.join(
            f'      <li>{html.escape(w)}</li>' for w in all_warnings)
        warnings_html = f'''    <section>
      <h2>Warnings / Gaps</h2>
      <ul>
{items}
      </ul>
    </section>'''

    # --- errors ---
    errors_html = ''
    if result and result.errors:
        err_items = '\n'.join(
            f'      <li>{html.escape(e)}</li>' for e in result.errors)
        errors_html = f'''    <section>
      <h2>Custody Gaps</h2>
      <ul>
{err_items}
      </ul>
    </section>'''

    # --- summary stats ---
    artefact_count = receipt.artifact_count
    bytes_claimed = _human(receipt.total_bytes_claimed)
    rtype = receipt.receipt_type.value.replace('_', ' ').title()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>RECEIPT Proof Pack — {rtype}</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif;
         background: #1a1d24; color: #e5e7eb; margin: 0; padding: 2rem; }}
  .card {{ background: #262c36; border-radius: 10px; padding: 1.5rem;
           margin-bottom: 1.5rem; border: 1px solid #39414e; }}
  h1 {{ color: #3b82f6; font-size: 1.4rem; margin: 0 0 .25rem; }}
  h2 {{ color: #9aa4b2; font-size: 1rem; margin: 0 0 .75rem;
        text-transform: uppercase; letter-spacing: .05em; }}
  .sub {{ color: #9aa4b2; font-size: .75rem; margin-bottom: 1rem; }}
  table {{ width: 100%%; border-collapse: collapse; }}
  td {{ padding: .4rem .75rem; border-bottom: 1px solid #39414e; }}
  td:first-child {{ color: #9aa4b2; width: 140px; }}
  td:last-child {{ font-weight: 600; }}
  .trust {{ font-size: 2rem; font-weight: 700; }}
  .trust-ok {{ color: #22c55e; }}
  .trust-gap {{ color: #f87171; }}
  .trust-na {{ color: #9aa4b2; }}
  pre {{ background: #1a1f26; padding: 1rem; border-radius: 6px;
         overflow-x: auto; font-size: .8rem; line-height: 1.5; }}
  li {{ margin-bottom: .25rem; }}
  .local-only {{ text-align: center; color: #6b7480; font-size: .7rem;
                 margin-top: 2rem; }}
  .badge {{ display: inline-block; padding: .2rem .6rem; border-radius: 4px;
            font-size: .7rem; font-weight: 600; }}
  .badge-verified {{ background: #143d26; color: #22c55e; }}
  .badge-gap {{ background: #3b1414; color: #f87171; }}
  .badge-partial {{ background: #1e293b; color: #9aa4b2; }}
</style>
</head>
<body>

  <div class="card">
    <h1>RECEIPT Proof Pack</h1>
    <p class="sub">{rtype} Receipt &middot; Generated {now}</p>
    <table>
      <tr><td>Receipt type</td><td>{rtype}</td></tr>
      <tr><td>Date</td><td>{receipt.created_at or 'Unknown'}</td></tr>
      <tr><td>Producer</td><td>{receipt.producer_app} {receipt.producer_version}</td></tr>
      <tr><td>Items</td><td>{artefact_count}</td></tr>
      <tr><td>Space</td><td>{bytes_claimed}</td></tr>
    </table>
  </div>

{custody_html}

{warnings_html}

{errors_html}

  <div class="card">
    <h2>Raw Receipt</h2>
    <pre>{escaped_raw}</pre>
  </div>

  <p class="local-only">
    RECEIPT Proof Pack &mdash; local-only. No account, no cloud, no telemetry.<br>
    This file was generated on your machine and never left it.
  </p>

</body>
</html>'''


def _custody_section(
    status: CustodyStatus | None,
    trust: str,
    verified: int,
    missing: int,
    total: int,
) -> str:
    if status is None:
        return '''  <div class="card">
    <h2>Custody</h2>
    <p>No custody data available.</p>
  </div>'''

    if status == CustodyStatus.VERIFIED:
        badge = '<span class="badge badge-verified">Verified</span>'
        trust_class = 'trust-ok'
        detail = 'All referenced archive artifacts are present.'
    elif status == CustodyStatus.GAPS_DETECTED:
        badge = '<span class="badge badge-gap">Gaps detected</span>'
        trust_class = 'trust-gap'
        detail = (
            f'{missing}/{total} artifact(s) missing from the archive. '
            f'This usually means they were pruned, moved, or deleted '
            f'outside the producer app.'
        )
    elif status == CustodyStatus.PARTIAL_RECEIPT:
        badge = '<span class="badge badge-partial">Partial receipt</span>'
        trust_class = 'trust-na'
        detail = (
            'This receipt does not include enough structured artifact data '
            'for a full custody check.'
        )
    elif status == CustodyStatus.NO_ARTIFACT_PATHS:
        badge = '<span class="badge badge-partial">Partial receipt</span>'
        trust_class = 'trust-na'
        detail = 'No individual artifact paths available for custody check.'
    else:
        badge = '<span class="badge badge-partial">Unknown</span>'
        trust_class = 'trust-na'
        detail = 'Unable to determine custody status.'

    counts = ''
    if total > 0:
        counts = (
            f'    <p>Verified: {verified} / Missing: {missing} / Total: {total}</p>'
        )

    return f'''  <div class="card">
    <h2>Custody</h2>
    {badge}
    <p class="trust {trust_class}">{trust}</p>
    <p>{detail}</p>
{counts}
  </div>'''


def _human(n: int) -> str:
    sign = '-' if n < 0 else ''
    n = abs(n)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{sign}{n:.1f}{unit}'
        n /= 1024
    return f'{sign}{n:.1f}PB'
