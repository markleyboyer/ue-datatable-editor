# Project context for Claude

Single-file web app (`ue-datatable-editor.html`) for editing Unreal Engine DataTable CSV exports — Aziel Arts Ecological Biome species and ecosystem tables — with exact format fidelity on save. No build step; all deps come from jsDelivr CDN. See [README.md](README.md) for the user-facing overview and [HOW-TO-USE.md](HOW-TO-USE.md) for workflow guides.

## Live deployment

- Hosted on GitHub Pages: **https://markleyboyer.github.io/ue-datatable-editor/**
- Source repo: `https://github.com/markleyboyer/ue-datatable-editor` (single branch `main`, built from root)
- `index.html` is a tiny `meta refresh` redirect to `ue-datatable-editor.html` so the Pages root lands on the app. Don't edit it; edit the editor file.
- Pages config managed via `gh api repos/markleyboyer/ue-datatable-editor/pages` — HTTPS is enforced, which is needed for the File System Access API's in-place save path.

## Major architectural pieces

All in one HTML file; the comment headers (`// ═══ TITLE ═══`) demarcate sections:

- **State** — `gridApi`, `selectedCells` (Set of `"rowId||field"`), `tableType` (`'species' | 'ecosystem' | 'generic'`), modal state, `dispCurrentRowIds`
- **UE format helpers** — float/Vec2/LinearColor parse + serialize. `FLOAT_FIELDS` set drives the 6-decimal `1.000000` formatting. `RANGE_FIELDS` set drives the Min/Max selection-bar UI.
- **Cell selection** — manual selection (AG Grid Community lacks range selection) using a `Set` of `"rowId||field"` keys; highlights are applied via an injected `<style id="sel-hl-css">` whose CSS attribute selectors target AG Grid's `row-id` / `col-id` attributes. This is **immune to AG Grid re-renders** that would otherwise wipe per-cell classes.
- **Bulk-edit ops (Apply / × Scale / 🎲 Randomize)** — direct-mutate `node.data[field]` then `api.refreshCells()`. Bypasses `setDataValue` / `onCellValueChanged` to avoid the broadcast-to-selection logic stomping later writes with the first cell's result.
- **MeshVariants modal** — separate AG Grid instance, parses/serializes the nested struct array using a parenthesis-depth scanner (naive comma-split breaks on nested `ScaleRange=(X=...,Y=...)`).
- **Charts** — Chart.js. Age-class chart has an inline `afterDatasetsDraw` plugin that draws variant counts directly onto the canvas (more reliable than `chartjs-plugin-datalabels` for per-dataset overrides).
- **Dispersion Pattern Visualizer** — see next section.

## Dispersion Pattern Visualizer (current focus)

Live canvas preview in the sidebar that shows the spatial pattern a species will produce in UE. Reads `DispersionType`, `TargetRIndex`, `DispersionScale`, `DispersionWarpStrength`, `DispersionSeed`, `StemsPerHectare`. Key design decisions:

- **Point count is physical**: `N = StemsPerHectare × area_ha`, where area is computed from the `dispGridSizeM` slider (5 m … 5 km). So zooming the scale slider genuinely densifies/sparsifies the pattern instead of just relabeling axes. Capped at **3,000 points per pattern** for render perf, with `(of 20,000)` style annotation in the info readout when sub-sampled.
- **Cluster sigma is in real meters**, not unit-square fractions: `sigmaM = scale × 5 × (1.2 − R)`, then divided by `gridSizeM` to convert to canvas-uv. A 4 m clump correctly looks bigger at 50 m grids than at 1 km grids.
- **Cluster count is per hectare**: `clustersPerHa = 4 + 25 × R`, capped so each cluster keeps ≥ 4 offspring (otherwise patterns at high N look random).
- **Dot radius = ~1.5 m tree canopy** in real meters, clamped to 0.7–7 px so it stays visible at extreme zooms.
- **Multi-row overlay**: selection across multiple rows draws each pattern in a distinct color from `PATTERN_COLORS` (12 colors, indexed by selection order). Opacity steps down with row count: 1=1.0, 2-3=0.72, 4-6=0.55, 7+=0.42.
- **House icon + scale bar** drawn as overlay references (10 m × 8 m footprint, "nice" 1/2/5/10/… meter scale bar). Both auto-hide when they'd be too small or too large.
- **Seeded RNG** is `mulberry32`; same inputs → identical patterns (good for reproducibility and visual stability while editing other fields).
- **R<sub>actual</sub>** computed via `clarkEvansR(pts)` — pairwise nearest-neighbor scan, fine up to a few thousand points.

`DispersionWarpStrength` is a new column added with this work — it's in `FLOAT_FIELDS` and the species `buildColDefs`. The `+ Add Row` defaults set it to `2.000000`.

## Browser support / fallback

The editor uses `showOpenFilePicker` / `showSaveFilePicker` when available. **A hidden `<input type="file">` fallback was added for the open path** — the GitHub Pages preview iframe doesn't expose those APIs, and Firefox/Safari/mobile don't have them at all. The save path already had a blob-download fallback. Don't remove these; they're load-bearing for the hosted experience.

## User conventions / preferences

- **Commits are minimal-scope.** Don't bulk-stage with `git add -A`; stage specific files. The user keeps a lot of working CSVs in the folder (`DT_NewReal*.csv`, `EDT_Flowers*.csv`, etc.) that should generally **not** go in the repo. Ask before staging anything beyond the obvious editor + docs changes.
- **Confirm before pushing or before any irreversible action.** The user reads commit messages and pushes carefully.
- **Multi-line commit messages via HEREDOC** (`git commit -m "$(cat <<'EOF' ... EOF\n)"`) — preserves formatting on Windows.
- **Antigravity environment**: the user runs Claude Code inside Anthropic Antigravity with the Claude-Preview MCP plugin and Claude-in-Chrome tools available. Edits to the HTML file appear live in a preview panel — when an Edit/Write hook says the file is visible in the preview panel, mention that in the response.
- **Windows + PowerShell**: prefer PowerShell for shell ops (`$env:VAR`, backtick line continuation, `Rename-Item`). Bash works too via the Bash tool but PowerShell is the native shell.

## Environment quirks

- A stale `GITHUB_TOKEN` env var was set system-wide on the user's machine pointing at an invalid token. `gh` keyring auth (set up via `gh auth login`) takes precedence in their interactive shell, but **subprocess shells started by tool calls may still see the bad token**. Prefix `gh` invocations with `$env:GITHUB_TOKEN=$null;` in PowerShell as a safety net. The user was advised to remove it from `sysdm.cpl` but may not have yet.
- Project location: `C:\Users\mail\projects\EcosystemEDTEditor` (moved out of Google Drive on 2026-05-10 to avoid Drive's file-handle and streaming-placeholder quirks). The git remote and the GitHub Pages URL are independent of local path, so a future move/rename is safe — just end the Claude Code session first, since cwd is locked at session start.

## Open threads

These came up in conversation but aren't built yet:

- **"Load CSVs from the GitHub repo"** — could add a dropdown of files in the repo, fetched via raw GitHub URLs, as an alternative to local `📂 Open CSV`. Read-only, easy.
- **"Save edited CSVs back to the repo"** — would need GitHub Contents API + a user-supplied PAT/OAuth token. ~100-200 LOC, no backend needed. User indicated this is desirable but not yet committed to building.
- **Working CSV cleanup**: as of last session, the working tree had ~16 untracked draft CSVs (`DT_NewReal01n.csv`, `DT_NewReal02-mawi.csv`, etc.) and a `SpeciesScreenShots/` directory. The user planned to move them out of the project folder manually before the next commit; once they do, expect a commit that removes the currently-tracked `DT_PlatteEcosystems.csv` as well (they OK'd this).

## Files NOT in repo (intentionally)

- `__pycache__/`, `*.pyc` — gitignored
- `.claude/` — local Claude Code session state
- The various `DT_NewReal*.csv` working drafts — held back per user preference
