# UE DataTable Editor

A standalone single-file web app for editing the **Aziel Arts Ecological Biome** DataTable CSV exports outside Unreal Engine, then re-importing them with exact format fidelity.

**▶ Live: https://markleyboyer.github.io/ue-datatable-editor/**

No install, no build step. Open the link in any modern browser, click **📂 Open CSV**, and edit local files on your machine.

## Purpose

The Aziel Arts Ecological Biome system uses Unreal Engine DataTables to define species placement rules and ecosystem compositions. This tool lets you edit those CSVs in a spreadsheet-like interface with bulk multi-cell editing, scale-factor operations, live charts, a grid-based modal editor for the nested MeshVariants field, and a live spatial preview of dispersion patterns — then save them back in a format UE can re-import without modification.

## Files

| File | Description |
|------|-------------|
| `ue-datatable-editor.html` | The editor (the actual app) |
| `index.html` | Tiny redirect → `ue-datatable-editor.html` for the GitHub Pages root |
| `DT_PlatteEcosystems.csv` | Example Ecosystem DataTable for trying out the editor |
| `chop_thumbnails.py` | Utility: chop a UE content-browser screenshot into named PNGs |
| `chop_all_species.py` | Utility: batch-run chop_thumbnails for all species folders |

The editor opens any UE DataTable CSV from your local disk — you don't need any of the example files in the repo to use it.

See [HOW-TO-USE.md](HOW-TO-USE.md) for step-by-step instructions.

---

## How to Use

1. Open the [hosted editor](https://markleyboyer.github.io/ue-datatable-editor/) — or `ue-datatable-editor.html` locally in any browser
2. Click **📂 Open CSV** and pick a DataTable CSV from your disk
3. Edit values in the grid
4. Click **💾 Save CSV** — saves back over the original file (Chrome/Edge) or to your Downloads folder (other browsers)

### Browser support

The editor works everywhere, but the file-handling experience differs:

| Browser | Open CSV | Save CSV |
|---------|----------|----------|
| Chrome / Edge / Opera (desktop) | Native picker (File System Access API) | **Saves back to the original file in place** |
| Firefox / Safari / mobile | Standard file input | Downloads to your Downloads folder |

GitHub Pages serves over HTTPS, which is what the in-place save path needs — running the page from `file://` may disable that path in some browsers (notably Brave). Use the hosted URL or serve the folder over `http://localhost` if you hit that.

### Thumbnail Support

Click **Thumbnails Folder** and select the `SpeciesScreenShots/Thumbnails/` folder. All PNG files are preloaded into memory. Thumbnails then appear in the Mesh Variants modal as a small preview column; hovering over any thumbnail shows a large 400×400 popup.

---

## Grid Interaction

### Cell Selection
- **Click** — select a single cell, deselect all others
- **Shift+click** — extend selection to a range within the same column
- **Ctrl+click** — toggle individual cells on/off (non-contiguous selection)
- **Esc** — clear selection

### Bulk Editing (Selection Bar)
When one or more cells are selected in the same column, a bar appears above the grid:
- Type a new value and press **Enter** or click **Apply** to write it to all selected cells
- **Float auto-format**: typing a whole number (e.g. `50`) into a float field auto-expands to `50.000000`
- **Range fields** (Slope, Aspect, Wetness, MicroTopo): the bar shows separate **Min** and **Max** inputs serialized as UE Vector2D format `(X=0.000000,Y=1.000000)`

### Scale Factor
Next to the Apply button is a **× Scale** input and button:
- Select cells in a single column, enter a numeric factor (e.g. `0.5`), and click **× Scale** (or press Enter)
- Each cell's current value is multiplied independently by the factor
- Float fields remain serialized to 6 decimal places after scaling

### Randomize ±%
Next to the × Scale control is a **% / 🎲 Randomize** input and button:
- Select cells in a single numeric column, enter a percentage (default `20`), and click **🎲 Randomize** (or press Enter)
- Each cell is multiplied independently by a random factor in `[1 − N%, 1 + N%]`, then rounded to a "nice" whole number whose trailing digits are only zeros or a single 5 (e.g. 150, 500, 1250, 2500)
- The rounding step is chosen from `{5, 10, 50, 100, 500, 1000, …}` based on the value's magnitude, so small numbers still vary and big numbers keep clean trailing zeros
- Useful for adding natural variation across StemsPerHectare, EcosystemDensity, SpatialNoiseSize, etc.

### MeshVariants Column
Clicking a cell in the **Mesh Variants** column opens a modal grid editor. Each variant is a row with the same multi-cell selection, bulk-edit, and scale-factor tools. Columns:

| Column | Description |
|--------|-------------|
| (thumbnail) | Mesh preview image, if thumbnails folder is loaded |
| Mesh Asset Path | Full UE asset path to the static mesh |
| Age Class | Seedling / Sapling / Mature / Dead |
| Age Wt | AgeClassWeight |
| Scale Min / Max | ScaleRange X and Y |
| Align | AlignToSurface (0–1) |
| Z Offset | ZPositionOffset |
| ✕ | Remove this variant row |

Click **+ Add Variant** to append a new row. Click **✓ Save Variants** to write back to the main table.

---

## Sidebar Charts

Charts update live as you edit data.

### Species Table
| Chart | Content |
|-------|---------|
| **Species Distribution** | Horizontal bar chart of Stems per Hectare per species |
| **Age Class Distribution** | Stacked horizontal bar chart of age class weights (Seedling / Sapling / Mature / Dead). White bold labels inside each segment show the number of mesh variants assigned to that age class. |
| **Dispersion Pattern** | Live spatial preview of the species' point distribution — see below |

### Ecosystem Table
| Chart | Content |
|-------|---------|
| **Ecosystem Density** | Bar chart of density per ecosystem, colored by the ecosystem's own color value |
| **Spatial Noise Strength** | Bar chart of spatial noise strength per ecosystem |

---

## Dispersion Pattern Visualizer

When a species table is loaded and a row is selected, the **Dispersion Pattern** panel appears in the sidebar with a live canvas preview of how that species will be spatially distributed in Unreal Engine.

### What it reads

| Field | Effect on the preview |
|-------|----------------------|
| `DispersionType` | `Random` / `Poisson` → uniform-random; `Clumping` → Thomas process (cluster centers + Gaussian offspring); `Uniform` → jittered hex-ish grid |
| `TargetRIndex` | Clark-Evans nearest-neighbor index target. R<1 = clumped, R=1 = random, R≈2.149 = perfect hex packing |
| `DispersionScale` | Cluster radius (in **meters**) for Clumping; jitter magnitude for Uniform |
| `DispersionWarpStrength` | Smooth sinusoidal displacement applied to the whole point set |
| `DispersionSeed` | Seeds a deterministic RNG, so the same inputs always produce the same pattern |
| `StemsPerHectare` | Multiplied by the visible area (from the scale slider) to give the actual point count rendered |

### Real-world scale

A slider above the canvas sets the edge length of the visible area, from **5 m to 5 km** (default 100 m). Everything in the preview is in real meters:

- The total point count = `StemsPerHectare × area_in_hectares` — so the same species draws ~50 dots at 50 m, ~200 at 100 m, and densifies further as you zoom out
- Cluster sigma is in real meters, so a 4 m clump genuinely covers 4% of a 100 m grid and 0.4% of a 1 km grid
- Each dot is drawn at the size of a tree canopy (~1.5 m radius), clamped to a legible pixel range
- A **scale bar** in the bottom-left and a **house icon** (10 m × 8 m footprint) in the bottom-right give human-scale references that update with the slider
- For very large grids the rendered count is capped at 3,000 points per pattern, with a `(of 20,000)` annotation in the info readout

### Multi-row overlay

Selecting cells across multiple rows (Ctrl+click or Shift+click) draws each row's pattern as a colored layer on the same canvas, so you can compare distributions side-by-side. Opacity steps down as more rows are added (1 row = full opacity, 7+ rows ≈ 42%). The legend below the canvas shows each row's name, dispersion type, and stems/ha in its layer color.

### Computed Clark-Evans R

For a single selected row, the info readout shows both `R_target` (what you set) and `R_actual` (the Clark-Evans index of the actually-rendered point set), which is a useful sanity check that the generator is matching your intent.

---

## Supported Table Types

The editor auto-detects the table type from column headers on load:

| Type | Detected by | Key columns |
|------|-------------|-------------|
| **Species** | `MeshVariants` column present | StemsPerHectare, DispersionType, TargetRIndex, DispersionScale, DispersionWarpStrength, DispersionSeed, SlopeRange, AspectRange, WetnessRange, MicroTopoRange, age weights, MeshVariants |
| **Ecosystem** | `SpeciesList` column present | EcosystemVisible, EcosystemDensity, EcosystemColor, SpeciesList, noise/seed params |
| **Generic** | fallback | All columns editable as plain text |

---

## UE Format Details

Unreal Engine DataTable CSVs have specific format requirements that the editor preserves on save:

### CSV Structure
- First column header is `---` (the row key column); all other headers are field names
- The row key column is **not** quoted; all other values are double-quoted
- Line endings are `\r\n` (CRLF)

### Field Formats
| Type | Example |
|------|---------|
| Float | `1.000000` (always 6 decimal places) |
| Bool | `True` or `False` |
| Vector2D | `(X=0.000000,Y=1.000000)` |
| LinearColor | `(R=0.043735,G=0.412543,B=0.162029,A=1.000000)` |
| Asset reference | `/Script/Engine.DataTable'/Game/MBData/...'` |
| MeshVariants | `((Mesh="path",Age Class=Mature,AgeClassWeight=1.000000,ScaleRange=(X=0.800000,Y=1.200000),AlignToSurface=0.500000,ZPositionOffset=0.000000),(...))` |

### MeshVariants Parsing Strategy
MeshVariants is a nested struct array serialized as a flat string. The parser tracks parenthesis depth to split entries at `)(` boundaries (rather than naive comma-splitting, which would break on nested `ScaleRange=(X=...,Y=...)`). Within each entry a key=value scanner handles quoted strings, nested paren values, and plain values. `ScaleRange` is flattened into `_scaleX` / `_scaleY` fields internally for the modal UI, then re-serialized on save.

---

## Thumbnail Utility Scripts

`chop_thumbnails.py` uses PIL/numpy to chop Unreal Engine content browser screenshots into individually named PNGs. It auto-detects card boundaries by column/row variance analysis and trims the label strip from each card by brightness scan.

`chop_all_species.py` is a batch runner for all species (Ash, Beech, DeadTrees, Oaks, Spruce), with hardcoded name lists that include `None` entries to skip non-mesh assets (e.g. `InterchangeSceneImportAsset` entries in the Spruce screenshot).

**Requirements:** Python 3 with `Pillow` and `numpy`
```
pip install Pillow numpy
python chop_all_species.py
```

After running, copy or move all output PNGs into `SpeciesScreenShots/Thumbnails/` (flat folder, no subfolders), then load that folder in the editor.

---

## Libraries Used

| Library | Version | Role |
|---------|---------|------|
| [AG Grid Community](https://www.ag-grid.com/) | 31.3.2 | Spreadsheet grid |
| [Papa Parse](https://www.papaparse.com/) | 5.4.1 | CSV parsing |
| [Chart.js](https://www.chartjs.org/) | 4.4.3 | Sidebar charts |
| [chartjs-plugin-datalabels](https://chartjs-plugin-datalabels.netlify.app/) | 2.2.0 | Variant count labels inside chart bars |

All loaded from jsDelivr CDN — no build step, no server, no install.

---

## Key Implementation Notes

### Cell Highlighting
AG Grid Community does not support multi-cell range selection (that is an Enterprise feature). Cell selection is implemented manually using a `Set<"rowId||field">`. Highlights are applied by injecting a `<style id="sel-hl-css">` element into `<head>` containing CSS attribute-selector rules — this approach is immune to AG Grid's DOM re-renders.

### Scale Factor
The scale operation pre-computes all new values from current row data before applying any writes, then sets `node.data[field]` directly and calls `api.refreshCells()`. This bypasses `onCellValueChanged` entirely, preventing the normal broadcast-to-selection behavior from overwriting other cells with the first cell's result.

### CSV Serialization
Papa Parse is used only for parsing. Serialization is done manually to match UE's exact quoting format: `origHeaders.join(',')` for the header line (no quotes); first column unquoted then `'"' + value + '"'` for all remaining columns.

### Browser Requirements
The editor uses the File System Access API (`showOpenFilePicker`, `showSaveFilePicker`, `showDirectoryPicker`) when available — that gives the in-place save experience in Chrome 86+ / Edge 86+ / Opera. If the API is missing (Firefox, Safari, mobile browsers, or sandboxed iframes such as the GitHub Pages preview), it falls back to:
- A hidden `<input type="file">` for opening
- A blob download for saving

Other Chromium browsers (Brave, Arc, Vivaldi) ship the same API but may block it on `file://` origins as part of their privacy hardening — Brave is a notable example. Workarounds: use the [hosted Pages URL](https://markleyboyer.github.io/ue-datatable-editor/), open the page in Chrome/Edge directly, or serve the folder over `http://localhost` (e.g. `python -m http.server 8000`).

---

## Credits

Built collaboratively with the **Claude** coding agent inside **Anthropic Antigravity**.
