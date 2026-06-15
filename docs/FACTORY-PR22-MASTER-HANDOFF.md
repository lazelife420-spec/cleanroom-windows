# Cleanroom PR #22 — Master Cursor Handoff: Final Product Polish + Tray/Icon Pass

## Status

PR #22 remains **ON HOLD**.

Current active branch:

```text
ui/proof-dashboard-polish
```

Latest known PR #22 state before this handoff:

```text
PR #22: open / not merged
Automated gates: green
No version bump
No tag
No release prep
No installer/build file changes
```

Do **not** merge, tag, release, or prep `v1.0.5` from this lane.

---

## Current problem

Cleanroom is much better than it was, but it still does not fully feel like a finished product.

The app now has the bones of a real proof-first Windows utility:

- Home dashboard
- Sidebar hierarchy
- Settings left rail
- Dark modals/popovers
- More consistent table interactions
- Proof Ledger
- Archive Custody
- Startup Manager
- Uninstaller
- Cleaner
- Explorer Context Menus under Tools

But the remaining polish issues make it still feel partly like a developer/admin tool.

This pass must finish the product feel.

---

## Hard constraints

Do not violate these.

```text
No cleanup/archive/prune/uninstaller destructive behavior changes
No PR #21 shell/context menu behavior changes
No version bump
No tag
No release prep
Do not touch Cleanroom.spec
Do not touch build_installer.ps1
Do not touch scripts/tray_visual_gate.py
Stay Python/CustomTkinter
Keep local-only / proof-first doctrine
```

This is a UI/product polish pass, not a behavior rewrite.

---

## Product target

Cleanroom should feel like a finished local Windows product:

```text
Archive-first cleanup.
Receipt-backed proof.
Local-only custody.
No fake score.
No telemetry/cloud/account dependency.
Every action can be proven.
```

The app should feel closer to a polished Windows utility like IObit in organization and clarity, but with Cleanroom’s proof-first identity.

Do not copy IObit branding. Use only the layout lessons:

- clear left rail
- large primary action
- grouped product modules
- consistent cards/lists
- details panel
- obvious user actions
- no raw developer surfaces

---

# Part 1 — Tray menu is a blocker

## Current issue

The tray context menu currently looks like a plain native white menu with basic items:

```text
Open Cleanroom
Hide to tray
Show
Latest Receipt
Proof Pack
Quit
```

It looks unfinished and does not match the app’s dark product style.

The tray icon/menu should feel like part of Cleanroom, not a default tkinter/pystray leftover.

## Required tray improvements

### 1. Tray menu hierarchy

Replace the weak tray menu structure with a useful product menu.

Target menu:

```text
Cleanroom
Status: Archive-first ON · Custody trust 13%

Open Cleanroom
Run Scan
Preview Latest Receipt
Open Latest Receipt
Open Proof Pack
Open Archive Folder

Tools
  Explorer Context Menus
  Registry Snapshot
  Cleanroom Rewind
  Custody Check

Window
  Hide to tray
  Show
  Restore

Quit Cleanroom
```

If pystray cannot style the menu dark, still improve the menu naming and structure. If pystray supports only native menus, use better wording and iconography, and ensure the app’s in-app tray status page/modal is dark.

### 2. Tray status should be useful

Tray tooltip/status should show current proof state, not just app name.

Examples:

```text
Cleanroom — Ready to scan
Cleanroom — Receipt ready
Cleanroom — 738 candidates · 18.76GB
Cleanroom — Custody gaps need review
Cleanroom — Archive-first ON
```

### 3. Tray singleton / cleanup

Must remain enforced:

```text
Launch once -> one tray icon
Close/hide/show -> still one tray icon
Quit -> tray icon disappears
Launch 5 times -> no duplicate tray pile
Second launch -> focus/show existing instance or exit cleanly
```

If tray duplication can still happen, fix it before merge.

### 4. Tray actions must work

Manual gate:

```text
[ ] Open Cleanroom works
[ ] Hide to tray works
[ ] Show works
[ ] Run Scan works or is disabled with clear reason
[ ] Latest Receipt works or is disabled with clear reason
[ ] Proof Pack works or is disabled with clear reason
[ ] Open Archive Folder works
[ ] Quit removes tray icon
[ ] Repeated launches do not create duplicate tray icons
```

---

# Part 2 — Desktop/taskbar/app icon pass

## Current issue

The app icon is not yet “sick af” enough for a finished product. It needs to feel premium at desktop, taskbar, tray, titlebar, and installer sizes.

The icon must still be readable at small sizes.

## Required icon deliverables

Create/refine a Cleanroom icon system:

```text
brand/icon-cleanroom.svg
brand/icon-cleanroom-16.svg or small-size optimized source if needed
brand/icon-cleanroom-32.svg
brand/icon-cleanroom-256.svg
```

Generated outputs:

```text
icon.ico
icon.png
assets/icon.ico if used
assets/icon.png if used
installer icon if applicable
```

Only modify files that are actually part of the Cleanroom icon pipeline. Do not touch unrelated build/installer files unless the current repo already requires icon registration there and the change is scoped.

## Icon design direction

Cleanroom icon should read as:

```text
cyber-clean
proof/custody
archive-first
Windows utility
sharp but trustworthy
```

Good directions:

- shield + receipt/check glyph
- cleanroom “C” mark with proof tick
- archive/custody box with neon proof line
- dark blue/black base with cyan/green accent
- high-contrast silhouette for 16px tray/taskbar

Avoid:

```text
tiny unreadable text
busy gradients at 16px
generic recycle-bin look
too much neon
flat random C with no proof meaning
```

## Small-size requirements

At 16px and tray size:

```text
[ ] recognizable silhouette
[ ] no unreadable text
[ ] no muddy details
[ ] good contrast on dark Windows tray
[ ] good contrast on light menus if native tray menu appears
```

## Icon manual gate

Verify:

```text
[ ] Desktop shortcut icon looks premium
[ ] Taskbar icon looks premium
[ ] Tray icon looks premium
[ ] Titlebar icon looks premium
[ ] icon.ico contains multiple sizes
[ ] installer/app uses the same brand mark
[ ] no duplicate or stale icon assets
```

---

# Part 3 — App shell cohesion

## Current issue

The shell is better but still sometimes feels like stacked UI strips.

Avoid this feeling:

```text
custody strip
button strip
banner strip
sidebar
page
table
details
```

The app should feel like one integrated frame.

## Required shell structure

Use one consistent structure:

```text
Top workflow bar
Compact custody/status strip
Left product rail
Page identity card
Main content
Right/bottom details/proof panel
```

Home is the only full dashboard.

Workspace pages should not duplicate the full Home dashboard.

## Home

Home should always feel intentional, never empty.

Home must show:

```text
Dynamic Cleanroom identity
Primary status: Ready to scan / Receipt ready / Custody needs review
One dominant primary action
Proof/custody cards
Recent proof
Recommendations or polished empty state
```

Empty Home should not look unfinished. Use a polished empty state:

```text
Ready to scan
Run your first scan to create a receipt-backed cleanup plan.

[Scan Now]
```

## Workspaces

For Cleaner, Archive, Activity, Startup, Uninstaller, Restore, Settings, Tools:

```text
Page identity
One-line purpose
Primary action row
Compact summary/status
Main list/table
Details panel
```

Do not show full dashboard proof cards on every page.

---

# Part 4 — Sidebar cohesion

Keep this structure:

```text
Main
- Home
- Cleaner
- Archive
- Activity

System
- Startup
- Uninstaller
- Restore
- Settings

Tools
- Explorer Context Menus
- Registry Snapshot
- Cleanroom Rewind
- Cleanroom Receipt
- Proof Pack
- Custody Check
- Schedule Cleanup
```

## Requirements

```text
[ ] Explorer Context Menus remains inside Tools
[ ] Tools is findable, not buried
[ ] Active page is obvious
[ ] Section headers feel intentional
[ ] Rows are not cramped
[ ] No duplicate navigation elsewhere
```

The sidebar should feel like a product rail, not a tkinter list.

---

# Part 5 — More menu / command hierarchy

## Current issue

More menu has been darkened, but it must remain product-quality and grouped.

## Required structure

More menu should be grouped:

```text
Receipts
- Latest Receipt
- Receipt Viewer
- Proof Pack

Custody
- Verify Custody
- Open Archive Folder
- Custody Check

Tools
- Explorer Context Menus
- Registry Snapshot
- Cleanroom Rewind
- Schedule Cleanup

Diagnostics
- Local Logs
- App Diagnostics
```

Rename any “Telemetry” wording to:

```text
Diagnostics
Local Logs
```

Cleanroom is local-only. Do not make it sound like it phones home.

---

# Part 6 — Unified table/list interaction contract

Every major table must follow the same contract:

```text
single click = select + update details
double click = safe inspect/open details
right click = dark action popover
arrow keys = move selection + update details
Enter = safe default action
Delete key = only if guarded and confirmed
```

Apply to:

```text
Cleaner candidates
Archive custody
Activity ledger
Startup Manager
Uninstaller
Restore
```

## Empty/read-only states

Do not show dead dashes.

Use explicit empty states:

```text
Select a candidate to inspect why Cleanroom flagged it.
Select a startup entry to review its command and available actions.
Select a ledger row to view proof details.
No candidates found. Run Scan to refresh.
```

---

# Part 7 — Cleaner page

## Current issue

Cleaner is improved, but candidate details must always bind correctly.

## Required Cleaner layout

```text
Cleaner
Scan folders, then preview receipt before cleanup.

[Scan Now] [Preview Receipt] [Archive & Clean]

Status chips:
Candidates
Checked
Reclaimable
Archive target
Reason groups

Candidate list
Candidate details
```

## Candidate details must show

When a row is selected:

```text
Name
Full path
Reason
Size
Archive destination
Receipt status
Why it matters
Actions:
- Open location
- Copy path
- Exclude
- Preview receipt
```

No selected row should leave the details panel blank or dash-only.

---

# Part 8 — Archive Custody page

## Current issue

Archive is functional but still dense. Delete flow must be unmistakable.

## Required Archive organization

Separate actions visually:

```text
Review & restore
- Restore Selected
- Open Archive Folder
- Refresh

Select
- Select All Safe
- Select Visible
- Clear Selection

Delete from archive
- Delete Eligible
- Delete Older Than
```

Danger/destructive delete actions must be visually separated.

## Delete modal must show buckets

Before deleting:

```text
Selected: 4,787
Eligible to delete now: 3
Will be skipped: 4,784
Eligible size: 9.60MB
Why skipped:
- keep in custody
- not old enough
- not in archive
- missing proof
```

Button must say:

```text
Delete 3 eligible items
```

not “Delete selected” if most selected items will be skipped.

After delete:

```text
Deleted: 3
Skipped: 4,784
Receipt: <path>
[Open Receipt] [Close]
```

---

# Part 9 — Activity / Proof Ledger

## Current issue

Activity still risks feeling like a log viewer.

## Required Activity framing

```text
Proof Ledger
Every action has a receipt.

Summary:
- Custody trust
- Actions logged
- Restorable now
- Bytes in custody
- Bytes pruned

Ledger list
Proof details panel
```

## Verify Custody

No native path-dump warnings.

Use styled summary:

```text
Custody check failed

736 / 5,529 archived items are present on disk.
4,793 items are missing from archive.
This usually means files were pruned, moved, or deleted outside Cleanroom.

[Open full report] [Copy summary] [OK]
```

Full report opens in a Cleanroom styled scrollable report modal.

---

# Part 10 — Startup Manager

## Current issue

Startup Manager still feels too dead/technical unless interaction is obvious.

## Required Startup table columns

Prefer human-readable columns:

```text
Name
Type
Source
Status / Note
```

Move long command/path into details panel.

## Required right-click actions

```text
Enable selected
Disable selected
Copy command
Open file location
Open registry key / Task Scheduler source when available
Search online
Show details
```

Unavailable actions must be disabled or show a clear reason.

Double-click must not enable/disable. It should safely show details or open location only when clearly safe.

---

# Part 11 — Uninstaller

## Current issue

Uninstaller still feels like a raw table with buttons.

## Required framing

```text
Uninstaller
Remove apps safely. Prefer official uninstallers.

Primary:
[Uninstall]

Secondary:
[Force Remove]
[Scan Leftovers]

Program list
Program details card
```

Details card should show:

```text
What it is
What it does
Do you need it?
Official uninstaller guidance
Risk note
```

Do not make the raw table the whole experience.

---

# Part 12 — Settings / Control Room

Settings is much improved. Keep left section rail.

Sections:

```text
General
Scan folders
Archive custody
Explorer integration
Receipts
Advanced
```

## Requirements

```text
[ ] No bottom tabs
[ ] Larger spacing
[ ] Clear switch rows
[ ] Better dropdown sizing
[ ] Stable footer actions
[ ] No blank cards
[ ] No tiny raw Tk feeling where avoidable
```

Footer should only contain persistent actions:

```text
Save Settings
Discard Changes
Open Data Folder / Open Config if appropriate
```

---

# Part 13 — Dialogs/modals

All app dialogs must share Cleanroom style.

Required styled surfaces:

```text
More menu
Explorer Context Menu Editor
Receipt Viewer
Verify Custody
Full report viewer
Archive delete confirmation
Delete result
Diagnostics / Local Logs
```

No native white menus or native path-dump messageboxes.

Receipt Viewer should be product-grade:

```text
Receipt
Prune Archive · 2026-06-13 16:50:54

Items pruned: 3
Bytes pruned: 9.60MB
Original live files touched: No

[Copy Receipt] [Open Receipt File] [Open Receipt Folder] [Close]

Tabs:
Summary
Raw
```

---

# Part 14 — Terminal/output polish

Terminal should not show avoidable noise.

Fix/suppress:

```text
CTkImage warnings
old traceback noise
debug prints
unexpected terminal spam
```

Manual gate must show:

```text
No TclError
No traceback
No repeated CTkImage warning spam
```

---

# Part 15 — Runtime/performance rules

Do not regress existing fixes:

```text
No full scan on startup unless Scan on startup is ON
No Not Responding on tab switches
Heavy tables load in background/chunks
Archive selected count starts at 0
Delete confirmation summarizes, not path dumps
Single-instance guard works
Tray cleanup works
One tray icon max
```

---

# Part 16 — Gates

Run:

```powershell
python -m pytest
python scripts/ui_merge_gates.py --include-150
python scripts/verify_release_surface.py --tag v1.0.4
```

Expected:

```text
209 passed
UI merge gates passed at 920x580 and 150% scaling
Release surface verify passed for v1.0.4
```

---

# Part 17 — Manual acceptance checklist

Run:

```powershell
git pull
python startup_manager_gui.py
```

Verify:

```text
[ ] Fresh launch fast
[ ] No auto full-scan
[ ] Home feels like finished product dashboard
[ ] Work pages do not duplicate full Home dashboard chrome
[ ] Sidebar Main/System/Tools hierarchy is clean
[ ] Explorer Context Menus is inside Tools
[ ] More menu is styled and grouped
[ ] Tray menu is useful and not cheap/default
[ ] Desktop/taskbar/tray/titlebar icon looks premium
[ ] Cleaner row click updates Candidate Details every time
[ ] Archive delete modal shows selected / eligible / skipped
[ ] Activity Verify Custody uses summary + report viewer
[ ] Startup rows have right-click + safe double-click/details behavior
[ ] Uninstaller details feel like product guidance
[ ] Settings left rail feels natural
[ ] Receipt Viewer is styled and useful
[ ] No native white menus/dialogs remain in normal flows
[ ] No Not Responding
[ ] No TclError / traceback
[ ] No CTkImage warning spam
[ ] No duplicate tray icons after repeated launches
[ ] 920x580 usable
[ ] 150% scaling usable
[ ] PR #21 Explorer shell context menus still work
```

Decision:

```text
PASS -> squash merge PR #22
FAIL -> fix only failed visual/runtime item(s), push, re-gate
```

---

## Stop condition

After pushing the final update to PR #22:

```text
Stop.
Do not merge.
Do not tag.
Do not start v1.0.5.
Do not prep release.
```

PR #22 remains on manual hold until explicitly approved.
