# UE DataTable Editor

A standalone single-file web app for editing Unreal Engine DataTable CSV exports outside the engine, then re-importing them with exact format fidelity.

## Purpose

Unreal Engine can export DataTables as CSV files. This tool lets you edit those CSVs in a spreadsheet-like interface with bulk multi-cell editing, visual charts, and a structured modal editor for complex nested fields — then save them back in a format UE can re-import without modification.

## Files

| File | Description |
|------|-------------|
| `ue-datatable-editor.html` | The editor — open this in Chrome or Edge |
| `DT_NewReal01.csv` | Species DataTable (mesh placement rules per species) |
| `DT_PlatteEcosystems.csv` | Ecosystem DataTable (biome compositions and spatial parameters) |

---

## How to Use

1. Open `ue-datatable-editor.html` in **Chrome or Edge** (requires the File System Access API — Firefox is not supported)
2. Click **Open CSV** and select one of the DataTable CSV files
3. Edit data in the grid
4. Click **Save CSV** to write changes back to the original file

### Thumbnail Support

Click **Thumbnails Folder** to point the editor at a directory of mesh preview images (PNG/JPG). Files should be named to match the mesh asset name (the last segment of the UE asset path, before the dot). Thumbnails appear in the Mesh Variants modal.

---

## Grid Interaction

### Cell Selection
- **Click** — select a single cell, deselect all others
- **Shift+click** — extend selection to a range within the same column
- **Ctrl+click** — toggle individual cells on/off (allows non-contiguous selection)
- **Esc** — clear selection

### Bulk Editing (Selection Bar)
When one or more cells are selected in the same column, a bar appears above the grid:
- Type a new value and press **Enter** or click **Apply** to write it to all selected cells
- **Float auto-format**: if you type a whole number (e.g. `50`) into a field that stores 6-decimal floats, it is automatically expanded to `50.000000`
- **Range fields** (Slope, Aspect, Wetness, MicroTopo): the bar shows separate **Min** and **Max** number inputs instead of a single text field; values are serialized as UE Vector2D format `(X=0.000000,Y=1.000000)`

### MeshVariants Column
Clicking a cell in the **Mesh Variants** column opens a modal editor with one structured row per mesh variant. Each variant exposes:
- Mesh asset path
- Age Class (Seedling / Sapling / Mature / Dead)
- Age Class Weight
- Scale Min / Scale Max
- Align to Surface
- Z Position Offset

---

## Sidebar Charts

Charts update live as you edit data.

### Species Table
| Chart | Content |
|-------|---------|
| **Species Distribution** | Horizontal bar chart of Stems per Hectare per species |
| **Age Class Distribution** | Stacked horizontal bar chart of age class weights (Seedling / Sapling / Mature / Dead). Each bar segment shows the **number of mesh variants** assigned to that age class as a white bold label inside the segment. |

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
| **Species** | `MeshVariants` column present | SpeciesWeight, StemsPerHectare, SlopeRange, AspectRange, WetnessRange, MicroTopoRange, age weights, MeshVariants |
| **Ecosystem** | `SpeciesList` column present | EcosystemVisible, EcosystemDensity, EcosystemColor, SpeciesList, noise/seed params |
| **Generic** | fallback | All columns editable as plain text |

---

## UE Format Details

Unreal Engine DataTable CSVs have several format requirements that the editor preserves on save:

### CSV Structure
- First column header is `---` (the row key column); all other headers are field names
- All values are quoted
- Line endings are `\r\n` (CRLF)
- Papa Parse handles the doubled-quote escaping UE uses inside nested struct strings

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
MeshVariants is a nested struct array serialized as a flat string. The parser tracks parenthesis depth to split entries at `)(` boundaries (rather than naive comma-splitting, which would break on nested `ScaleRange=(X=...,Y=...)`). Within each entry, a key=value scanner handles:
- Quoted string values (`Mesh="..."`)
- Nested paren values (`ScaleRange=(...)`)
- Plain values (`Age Class=Mature`)

Keys with spaces (`Age Class`) are supported. `ScaleRange` is flattened into `_scaleX` / `_scaleY` fields internally for the modal UI, then re-serialized on save.

---

## Libraries Used

| Library | Version | Role |
|---------|---------|------|
| [AG Grid Community](https://www.ag-grid.com/) | 31.3.2 | Spreadsheet grid |
| [Papa Parse](https://www.papaparse.com/) | 5.4.1 | CSV parse / serialize |
| [Chart.js](https://www.chartjs.org/) | 4.4.3 | Sidebar charts |
| [chartjs-plugin-datalabels](https://chartjs-plugin-datalabels.netlify.app/) | 2.2.0 | Variant count labels inside chart bars |

All loaded from jsDelivr CDN — no build step, no server, no install.

---

## Key Implementation Notes

### Cell Highlighting
AG Grid Community does not support multi-cell range selection (that is an Enterprise feature). Cell selection is implemented manually using a `Set<"rowId||field">`. Highlights are applied by injecting a `<style id="sel-hl-css">` element into `<head>` containing CSS attribute-selector rules:

```css
#grid .ag-row[row-id="RowKey"] .ag-cell[col-id="FieldName"] {
  background-color: #1a3d78 !important;
  ...
}
```

This approach is immune to AG Grid's DOM re-renders (which would wipe any classes added directly to cell elements).

### Shift-click Range Extension
Shift+click range selection is restricted to the same column as the anchor cell. This mirrors typical spreadsheet behavior and avoids ambiguity when columns have different data types.

### Live Chart Updates
Charts are destroyed and recreated on every edit (`updateCharts()` is called from `onCellValueChanged` and after `applySelEdit`). Chart.js canvas reuse without destroy/recreate produces stale data warnings.
