# UE DataTable Editor

A standalone single-file web app for editing the **Aziel Arts Ecological Biome** DataTable CSV exports outside Unreal Engine, then re-importing them with exact format fidelity.

## Purpose

The Aziel Arts Ecological Biome system uses Unreal Engine DataTables to define species placement rules and ecosystem compositions. This tool lets you edit those CSVs in a spreadsheet-like interface with bulk multi-cell editing, scale-factor operations, visual charts, and a grid-based modal editor for the complex nested MeshVariants field — then save them back in a format UE can re-import without modification.

## Files

| File | Description |
|------|-------------|
| `ue-datatable-editor.html` | The editor — open this in Chrome or Edge |
| `DT_NewReal01.csv` | Species DataTable (mesh placement rules per species) |
| `DT_PlatteEcosystems.csv` | Ecosystem DataTable (biome compositions and spatial parameters) |
| `chop_thumbnails.py` | Utility: chop a UE content-browser screenshot into named PNGs |
| `chop_all_species.py` | Utility: batch-run chop_thumbnails for all species folders |
| `SpeciesScreenShots/Thumbnails/` | Flat folder of all species mesh PNGs (load this in the editor) |

See [HOW-TO-USE.md](HOW-TO-USE.md) for step-by-step instructions.

---

## How to Use

1. Open `ue-datatable-editor.html` in **Chrome or Edge** (requires the File System Access API — Firefox is not supported)
2. Click **Open CSV** and select one of the DataTable CSV files
3. Edit data in the grid
4. Click **Save CSV** — a Save As dialog will appear; choose a file name and location

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

### Ecosystem Table
| Chart | Content |
|-------|---------|
| **Ecosystem Density** | Bar chart of density per ecosystem, colored by the ecosystem's own color value |
| **Spatial Noise Strength** | Bar chart of spatial noise strength per ecosystem |

---

## Supported Table Types

The editor auto-detects the table type from column headers on load:

| Type | Detected by | Key columns |
|------|-------------|-------------|
| **Species** | `MeshVariants` column present | StemsPerHectare, SlopeRange, AspectRange, WetnessRange, MicroTopoRange, age weights, MeshVariants |
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
Requires Chrome 86+ or Edge 86+ for the File System Access API (`showOpenFilePicker`, `showSaveFilePicker`, `showDirectoryPicker`). Falls back to a standard browser download if the API is unavailable.
