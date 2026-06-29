# Home + Cleaner v2 Implementation Plan

## Scope

This document starts a separate UI/product lane for Home v2 and Cleaner v2.

- Baseline commit: `8c7b989b9bb6459d697590015908313b97d2bfb5`
- Branch: `ui/home-cleaner-v2-foundation`
- Scope of this PR: planning and foundation inventory only
- Explicitly out of scope:
  - release prep for `v1.0.7`
  - tags or releases
  - installer metadata
  - release download links
  - cleanup/archive/receipt behavior changes

The product direction is to make Cleanroom feel like a serious local-first product, with Home and Cleaner centered around archive-first, proof-backed, reversible trust.

## Current Code Map

### Main app shell

- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:365)
  - `StartupManagerGUI` remains the primary composition root for page layout, actions, and state wiring.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:1995)
  - `_update_page_chrome()` hides the old stacked chrome and keeps page-owned hero sections in control.

### Home page

- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2018)
  - `_build_optimizer_tab()` is the current Home builder.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2022)
  - Hero block: status, subtitle, and primary CTA row.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2055)
  - Four top summary cards: review health, startup count, cleanup count, reclaimable size.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2083)
  - Main Home scroll region.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2091)
  - "Recent proof" tile row.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2108)
  - Disk foresight strip.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2123)
  - "Next recommended action" area with split pane.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2163)
  - Home recommendations empty state.

### Cleaner page

- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3074)
  - `_build_cleaner_tab()` is the current Cleaner builder.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3078)
  - Hero block: title, scan state, subtitle, primary CTA row.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3108)
  - Summary chip strip: candidates, reclaimable size, archive target, category.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3122)
  - Tool row: dedupe toggle, select all/none, legacy hidden progress control.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3139)
  - Main Cleaner split workspace.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3147)
  - Candidate tree/table card.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3174)
  - Candidate detail panel and row-level actions.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3215)
  - Cleaner empty state.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3231)
  - Loading/scanning panel with counters and stop/skip actions.

### Shared Home + Cleaner state logic

- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:646)
  - `_scan_display_metrics()` is the shared metric source for both pages.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:666)
  - `_sync_cleaner_state()` is the single source of truth for Cleaner hero, footer, action visibility, and loading/empty/results surface.
- [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:776)
  - `_sync_home_state()` aligns Home with the same scan lifecycle and custody signals.
- [`ui/page_state.py`](/C:/Users/KickA/smart_clean_tool/ui/page_state.py:47)
  - `cleaner_page_state(...)` defines Cleaner page copy/states.
- [`ui/page_state.py`](/C:/Users/KickA/smart_clean_tool/ui/page_state.py:113)
  - `home_page_state(...)` defines Home page copy/states.

### Existing reusable UI helpers under `ui/`

- [`ui/page_layout.py`](/C:/Users/KickA/smart_clean_tool/ui/page_layout.py:8)
  - Shared shell sizing and responsive layout constants already exist.
- [`ui/page_layout.py`](/C:/Users/KickA/smart_clean_tool/ui/page_layout.py:126)
  - `sync_split_workspace(...)` already standardizes loading/empty/results split behavior.
- [`ui/page_layout.py`](/C:/Users/KickA/smart_clean_tool/ui/page_layout.py:149)
  - `sync_table_empty_view(...)` already standardizes table/detail empty-state switching.
- [`ui/ctk_theme.py`](/C:/Users/KickA/smart_clean_tool/ui/ctk_theme.py:12)
  - Current type scale exists but is minimal and page-specific spacing values still live inline in page builders.
- [`ui/proof_dashboard.py`](/C:/Users/KickA/smart_clean_tool/ui/proof_dashboard.py:13)
  - `proof_card(...)` is a good precedent for reusable stat card construction.
- [`ui/proof_dashboard.py`](/C:/Users/KickA/smart_clean_tool/ui/proof_dashboard.py:41)
  - `app_shell_header(...)` shows the repo already accepts shell-level reusable product surfaces.
- [`ui/proof_dashboard.py`](/C:/Users/KickA/smart_clean_tool/ui/proof_dashboard.py:430)
  - `recent_proof_tile(...)` is already a reusable Home tile primitive.
- [`ui/proof_dashboard.py`](/C:/Users/KickA/smart_clean_tool/ui/proof_dashboard.py:456)
  - `recommendation_card(...)` is already the nearest existing equivalent to a guided action card.
- [`ui/proof_dashboard.py`](/C:/Users/KickA/smart_clean_tool/ui/proof_dashboard.py:520)
  - `ProofSummaryCard` is the current right-side Home trust/proof detail surface.

## Findings

1. Home and Cleaner are already on the right architectural path.
   The scan-state copy is centralized in `ui/page_state.py`, and layout-state switching is partially centralized in `ui/page_layout.py`.

2. The biggest remaining issue is composition, not behavior.
   Both `_build_optimizer_tab()` and `_build_cleaner_tab()` still inline large sections of hero, stat, empty-state, and detail-panel markup inside `startup_manager_gui.py`.

3. The safest redesign path is helper extraction before visual rewrite.
   The current code already exposes reliable state seams for Home/Cleaner, so the smallest-risk path is to move repeated panel patterns into reusable view helpers before introducing Home v2 and Cleaner v2 visuals.

4. Existing helper coverage is uneven.
   The repo has useful one-off cards and shell pieces, but no shared product primitives yet for trust states, workflow strips, guided actions, cleaner summaries, risk chips, or receipt-state pills.

## Proposed Component Targets

These should be introduced as reusable helpers, likely under `ui/proof_dashboard.py` first or a dedicated new `ui/home_cleaner_components.py` module once the surface area is clear.

### Home-oriented targets

- `hero_state_panel(...)`
  - Use for the top hero on Home and Cleaner.
  - Current source candidates:
    - Home hero in [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2022)
    - Cleaner hero in [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3078)
  - Should accept title, state headline, supporting copy, action slots, and visual tone.

- `trust_stat_tile(...)`
  - Use for compact proof/trust statistics on Home.
  - Current source candidates:
    - `health_card` in [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:2061)
    - existing `proof_card(...)` in [`ui/proof_dashboard.py`](/C:/Users/KickA/smart_clean_tool/ui/proof_dashboard.py:13)

- `guided_action_card(...)`
  - Use for Home’s recommendation cards.
  - Current source candidates:
    - `recommendation_card(...)` in [`ui/proof_dashboard.py`](/C:/Users/KickA/smart_clean_tool/ui/proof_dashboard.py:456)

- `trust_explainer_panel(...)`
  - Use for the right-hand Home panel explaining what the selected action or proof state means.
  - Current source candidates:
    - `ProofSummaryCard` in [`ui/proof_dashboard.py`](/C:/Users/KickA/smart_clean_tool/ui/proof_dashboard.py:520)

- `workflow_step_strip(...)`
  - Use for visualizing "Scan -> Preview Receipt -> Archive & Clean -> Restore" in a more deliberate product surface.
  - Current source candidates:
    - `PROOF_FLOW_TEXT` in [`ui/ctk_theme.py`](/C:/Users/KickA/smart_clean_tool/ui/ctk_theme.py:12)
    - command-bar proof flow label in [`ui/proof_dashboard.py`](/C:/Users/KickA/smart_clean_tool/ui/proof_dashboard.py:280)

### Cleaner-oriented targets

- `cleaner_summary_tile(...)`
  - Use for candidate count, reclaimable size, archive target, and category summary blocks.
  - Current source candidates:
    - chip row in [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3108)

- `candidate_detail_panel(...)`
  - Use for the Cleaner right-side selected-item detail view.
  - Current source candidates:
    - detail panel in [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3174)

- `risk_chip(...)`
  - Use for cleaner reason/category severity labeling and risk framing.
  - Current source candidates:
    - tree `reason` presentation and row hints in [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3153)
    - `_cleanup_reason_hint(...)` in [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3310)

- `receipt_state_pill(...)`
  - Use for displaying draft/ready/included/not-included proof state.
  - Current source candidates:
    - Home/Cleaner page-state copy in [`ui/page_state.py`](/C:/Users/KickA/smart_clean_tool/ui/page_state.py:47)
    - selection-state copy in [`startup_manager_gui.py`](/C:/Users/KickA/smart_clean_tool/startup_manager_gui.py:3272)

## Recommended Safe First Code PR After This

This should stay intentionally small and should not attempt Home v2 or Cleaner v2 end-to-end.

### PR 2 target

- shared shell cleanup
  - normalize page hero wrappers, card wrappers, and repeated empty/loading shell shapes
- typography and spacing constants
  - move repeated `Segoe UI` sizes, corner radii, and common paddings into `ui/ctk_theme.py` and/or `ui/page_layout.py`
- component helpers
  - extract low-risk shared primitives only
  - start with `hero_state_panel(...)`, `cleaner_summary_tile(...)`, `guided_action_card(...)`, and `candidate_detail_panel(...)`
- no workflow rewrites
  - keep current callbacks, state models, receipt flows, archive flows, and tree behavior intact

### Why this is the safest sequence

- It reduces duplicate UI code before visual divergence increases.
- It preserves scan/archive/receipt behavior while giving later PRs a cleaner composition layer.
- It allows Home v2 and Cleaner v2 to land separately instead of as a single risky rewrite.

## Planned PR Sequence

1. PR 1: UI foundation / shell inventory
   This PR. Planning and component extraction map only.
2. PR 2: shared component helpers + typography/spacing
   Small structural helper extraction, no major visual rewrite.
3. PR 3: Home v2
   Rebuild Home around trust, local-first explanation, proof-backed next actions.
4. PR 4: Cleaner v2
   Rebuild Cleaner around review confidence, risk framing, archive-first execution, and reversible trust.
5. PR 5: copy/empty-state cleanup + screenshots
   Final pass on product voice, empty states, and captured UI assets.

## Guardrails For Follow-On PRs

- Do not change cleanup behavior.
- Do not change archive behavior.
- Do not change receipt behavior.
- Do not remove existing actions.
- Do not fold Home v2 and Cleaner v2 into one PR.
- Prefer reusable helpers over more page-specific inline panel code inside `startup_manager_gui.py`.

## Verification Checklist For This PR

- `python -m ruff check .`
- `python -m pytest -p no:xonsh tests/`
- `python scripts/verify_release_surface.py`

This PR is planning/foundation only. No workflow behavior should change.
