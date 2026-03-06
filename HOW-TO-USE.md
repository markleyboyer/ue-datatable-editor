# How to Use — UE DataTable Editor

Step-by-step guide to editing Unreal Engine DataTable CSV files with `ue-datatable-editor.html`.

---

## Requirements

- **Browser:** Chrome or Edge (version 86 or later). Firefox is not supported — it lacks the File System Access API needed for the open/save dialogs.
- **Internet connection:** The editor loads AG Grid, Papa Parse, and Chart.js from CDN on first open.
- **Python 3 + Pillow + numpy** (optional): only needed if you want to generate thumbnail images from UE content browser screenshots.

---

## Opening the Editor

Double-click `ue-datatable-editor.html` or drag it into a Chrome/Edge window. No installation is required.

The toolbar at the top contains all primary controls. A status message on the right side of the toolbar shows feedback after each action.

---

## Loading a CSV File

1. Click **📂 Open CSV** in the toolbar.
2. A file picker opens — navigate to and select your DataTable CSV file (e.g. `DT_NewReal01.csv` or `DT_PlatteEcosystems.csv`).
3. The table type badge (top center) updates to show **Species** or **Ecosystem** based on the file's columns. The grid populates with one row per DataTable row and one column per field.

> The editor auto-detects whether the file is a Species table (contains a `MeshVariants` column) or an Ecosystem table (contains a `SpeciesList` column). Generic CSV files load with all columns editable as plain text.

---

## Editing Values

### Direct cell edit
Double-click any cell to edit it inline. Press **Enter** or click another cell to confirm. Press **Escape** to cancel.

Numeric fields that store 6-decimal floats (e.g. StemsPerHectare, AgeClassWeight) will automatically expand a whole number you type (`50`) to `50.000000` when you confirm the edit.

### Bulk edit across multiple rows
Use cell selection to edit the same field in several rows at once:

| Action | Result |
|--------|--------|
| **Click** a cell | Select that cell; deselect all others |
| **Shift+click** a cell | Extend selection from the current anchor to the clicked cell (same column only) |
| **Ctrl+click** a cell | Add or remove that cell from the selection without changing other selected cells |
| **Esc** | Clear the entire selection |

When at least one cell is selected, the **Selection Bar** appears between the toolbar and the grid showing:
- Which field and how many cells are selected
- A text/number input for the new value
- An **Apply ↵** button (or press **Enter**) to write the new value to all selected cells

For **Range fields** (SlopeRange, AspectRange, WetnessRange, MicroTopoRange), the Selection Bar shows separate **Min** and **Max** inputs instead. Values are stored in UE's Vector2D format `(X=min,Y=max)` automatically.

### Scaling values by a factor
To multiply selected cells by a number rather than replacing them:

1. Select cells in a single column (same as bulk edit above).
2. In the **× factor** input to the right of the Apply button, type a multiplier — for example `0.5` to halve all values, or `2` to double them.
3. Click **× Scale** or press **Enter** while the factor input is focused.

Each cell's current value is multiplied independently — cells with different values will produce different results. Float fields remain formatted to 6 decimal places.

> Example: selecting three cells with values 200, 300, 400 and applying factor 0.5 produces 100, 150, 200.

### Adding a row
Click **+ Add Row** in the toolbar to append a new row at the bottom of the table with default values. Edit the row key (Name field) and other fields as needed.

---

## Mesh Variants Editor (Species Tables Only)

The **Mesh Variants** column in a Species table holds the list of static meshes and their parameters for each species. Each cell shows a summary like `▣ 4 variants`.

**To edit variants:**
1. Click the Mesh Variants cell for any species row.
2. A modal window opens showing each variant as a row in its own grid.
3. Edit values the same way as the main grid — direct cell edit, multi-cell selection, bulk apply, and scale factor all work identically.
4. To add a new variant, click **+ Add Variant** at the bottom of the modal.
5. To remove a variant, click the **✕** button in the rightmost column of that variant row.
6. When finished, click **✓ Save Variants**. This writes the updated variants back to the main table row (the main table is not saved to disk at this point — use Save CSV separately).
7. Click **✕ Close** or press **Esc** to close the modal without saving changes.

### Mesh Variants fields

| Column | Field name | Description |
|--------|-----------|-------------|
| (thumbnail) | — | Mesh preview image (requires thumbnails folder to be loaded) |
| Mesh Asset Path | Mesh | Full UE content path, e.g. `/Game/Meshes/SM_Ash_Tree_01a.SM_Ash_Tree_01a` |
| Age Class | Age Class | Seedling / Sapling / Mature / Dead |
| Age Wt | AgeClassWeight | Relative spawn weight for this age class (float) |
| Scale Min | _scaleX | Minimum scale multiplier |
| Scale Max | _scaleY | Maximum scale multiplier |
| Align | AlignToSurface | 0 = vertical, 1 = align to surface normal |
| Z Offset | ZPositionOffset | Vertical offset in world units |

---

## Thumbnail Previews

Thumbnails show inside the Mesh Variants modal — a small image column on the left, and a 400×400 hover popup when you move the mouse over any thumbnail.

**To load thumbnails:**
1. Click **🖼 Thumbnails Folder** in the toolbar.
2. Select the `SpeciesScreenShots/Thumbnails/` folder (or any folder containing PNG/JPG files).
3. All images in the folder are preloaded. The status bar shows how many were loaded.
4. Open any Mesh Variants modal — the thumbnail column will now show images for recognized mesh names.

**How thumbnail matching works:** The editor extracts the last segment of the UE asset path before the dot (e.g. `SM_Ash_Tree_NN_01a` from `/Game/.../SM_Ash_Tree_NN_01a.SM_Ash_Tree_NN_01a`) and looks for a PNG file with that exact name in the loaded folder.

**Generating thumbnails from UE content browser screenshots:**

If you have screenshots of the UE content browser showing mesh thumbnails with names visible, the included Python scripts can chop them into individual named PNGs automatically.

1. Place screenshots in `SpeciesScreenShots/` — one per species, named after the species (e.g. `Ash.png`).
2. Open `chop_all_species.py` and verify the name lists match the assets shown in each screenshot. Use `None` for any slots that should be skipped.
3. Run `python chop_all_species.py` from the project folder.
4. Move all output PNGs into `SpeciesScreenShots/Thumbnails/` (flat folder — no subfolders).
5. Load the folder in the editor as described above.

---

## Saving the File

Click **💾 Save CSV** at any time.

A **Save As** dialog appears every time — you can overwrite the original file or save to a new name. The editor preserves the exact CSV format that Unreal Engine expects:
- The `Name` row-key column is not quoted
- All other field values are double-quoted
- Floats always have exactly 6 decimal places
- Line endings are CRLF (`\r\n`)
- Nested struct values (MeshVariants, Vector2D, LinearColor) use UE's serialization syntax

If the browser does not support the Save As dialog (unlikely in Chrome/Edge), the file is downloaded automatically to your Downloads folder.

---

## Sidebar Charts

The right-hand sidebar shows live charts that update as you edit.

### Species table charts

**Species Distribution** — horizontal bar chart of Stems per Hectare for each species. Longer bars = higher density.

**Age Class Distribution** — stacked horizontal bar showing the four age class weights (Seedling / Sapling / Mature / Dead) for each species. The white number inside each bar segment is the count of mesh variants assigned to that age class for that species.

### Ecosystem table charts

**Ecosystem Density** — bar chart of EcosystemDensity per ecosystem, colored by that ecosystem's EcosystemColor.

**Spatial Noise Strength** — bar chart of SpatialNoiseStrength per ecosystem.

---

## Workflow Example — Adjusting Species Density

**Goal:** Reduce all species Stems per Hectare by 20%.

1. Open `DT_NewReal01.csv`.
2. Click the **StemsPerHectare** cell for the first species.
3. Shift+click the **StemsPerHectare** cell for the last species to select the entire column.
4. In the **× factor** input, type `0.8`.
5. Click **× Scale**. All values are multiplied by 0.8 individually.
6. Verify the updated values look correct in the grid and in the Species Distribution chart.
7. Click **💾 Save CSV** and save over the original file.

---

## Workflow Example — Adding a Mesh Variant

**Goal:** Add a new Mature tree mesh to the Beech species.

1. Open `DT_NewReal01.csv`.
2. Find the **Beech** row and click its **Mesh Variants** cell.
3. In the modal, click **+ Add Variant**.
4. Double-click the **Mesh Asset Path** cell in the new row and enter the full UE path to your mesh.
5. Set **Age Class** to `Mature`.
6. Set **Age Wt**, **Scale Min**, **Scale Max**, **Align**, and **Z Offset** as needed.
7. Click **✓ Save Variants**.
8. Click **💾 Save CSV**.

---

## Workflow Example — Editing Ecosystem Spatial Noise

**Goal:** Set SpatialNoiseSize to the same value for three ecosystems at once.

1. Open `DT_PlatteEcosystems.csv`.
2. Click the **SpatialNoiseSize** cell for the first ecosystem.
3. Ctrl+click the same column for two other ecosystems to add them to the selection.
4. In the Selection Bar, type the new value and press **Enter**.
5. All three cells update. The Spatial Noise Strength chart reflects the change.
6. Click **💾 Save CSV**.

---

## Troubleshooting

**The Open/Save buttons don't work.**
Make sure you are using Chrome or Edge version 86 or later. Firefox does not support the File System Access API.

**The table loaded but all columns show as plain text.**
The file may not be a recognized Species or Ecosystem table. Check that the CSV has either a `MeshVariants` column or a `SpeciesList` column.

**Thumbnails aren't showing in the modal.**
- Verify the Thumbnails folder was selected (status bar should say "Thumbnails: N loaded").
- Check that the PNG file name exactly matches the last segment of the UE asset path in the Mesh column (case-sensitive on some platforms).
- Make sure the Mesh column is not blank for that variant row.

**Save produced a download instead of a Save As dialog.**
This is the fallback for browsers where `showSaveFilePicker` is blocked (e.g. some security policies). The file is complete and correct — find it in your Downloads folder.

**Values all became the same after applying a scale factor.**
Make sure you are using the latest version of the file. Earlier versions had a bug where AG Grid's cell-change broadcast overwrote subsequent scaled values with the first result. The current version bypasses the event system for scale operations entirely.
