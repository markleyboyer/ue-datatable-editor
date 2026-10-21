# Eco Table Editor: Unreal bridge plugin

An editor-only Unreal Engine plugin that lets the **UE DataTable Editor** web app open, edit and save **Aziel Ecosystems** species and ecosystem DataTables *live inside a running Unreal editor*, without exporting or re-importing CSVs, and regenerate the Aziel Ecosystem actors afterwards.

It's a small Python HTTP server (`eco_table_bridge.py`) that starts with the editor, serves the web app on **http://127.0.0.1:8765/**, and exposes a JSON API the app uses when it detects the bridge ("Unreal mode").

Tested with Unreal Engine **5.8** and **Aziel Ecosystems v06.05**.

## What you get in Unreal mode

When the page is opened from the bridge (or the hosted page can reach it), extra toolbar buttons appear:

| Button | What it does |
|---|---|
| 🎮 **Open from Unreal** | Lists every species and ecosystem DataTable in the project (`/Game` and `/AzielEcosystems`) and opens the ones you tick. *Use Content Browser selection* ticks the tables you've selected in the editor. |
| ↻ **Reload** | Re-reads the shown tables from Unreal (asks before discarding unsaved edits). |
| ⟳ **Save + Regenerate** | Writes the changed tables into the DataTable assets, then rebuilds and regenerates every `BP_Aziel_Ecosystem` actor in the open level. |
| ●/○ column, **All on / All off / Sel on / Sel off** | Switch rows on and off without losing their settings. Ecosystem rows flip `EcosystemVisible`. Species rows park `StemsPerHectare` at 0 and remember the real value (stored by the bridge), and switching back on restores it exactly. |

Saves are conflict-checked: if a table was changed in Unreal after you opened it, the app asks before overwriting.

Mesh thumbnails in the MeshVariants sub-grid are rendered by Unreal itself (see `/api/thumb` below).

## Install

1. Copy the `EcoTableEditor` folder into your project's `Plugins/` folder:
   ```
   <YourProject>/Plugins/EcoTableEditor/EcoTableEditor.uplugin
   <YourProject>/Plugins/EcoTableEditor/Content/Python/init_unreal.py
   <YourProject>/Plugins/EcoTableEditor/Content/Python/eco_table_bridge.py
   ```
2. Make sure these engine plugins are enabled (the `.uplugin` declares them): **Python Editor Script Plugin**, **Editor Scripting Utilities**, **Web Browser** (only needed for the in-editor widget below).
3. Tell the bridge where the web app is. It serves the first of these that exists:
   1. the file in the environment variable **`ECO_EDITOR_HTML`**;
   2. `C:\Users\mail\projects\EcosystemEDTEditor\ue-datatable-editor.html` (the author's working copy: edit this line in `eco_table_bridge.py` to point at your clone of this repo);
   3. `Plugins/EcoTableEditor/Resources/ue-datatable-editor.html` (copy the editor file there for a self-contained install).
4. Restart the editor. The Output Log should show:
   ```
   [EcoTableBridge] Serving http://127.0.0.1:8765/ (unreal mode)
   ```
5. Open **http://127.0.0.1:8765/** in Chrome or Edge. The status bar reads *Connected to Unreal (YourProject)*.

`init_unreal.py` starts the bridge automatically. Unreal runs any `Content/Python/init_unreal.py` at startup, and a failure is logged as a warning, never blocking the editor.

### Optional: dock it inside Unreal

Create an **Editor Utility Widget** (e.g. `EUW_EcoTableEditor`) with a **Web Browser** widget set to *Fill* and *Initial URL* `http://127.0.0.1:8765/`. Run it to get the editor as a dockable panel.

### Reloading after updating the bridge

Restart the editor, or in the Output Log switch the input box from **Cmd** to **Python** and run:
```python
import importlib, eco_table_bridge as b; b.stop(); importlib.reload(b); b.start()
```
Changes to `ue-datatable-editor.html` only need a browser refresh: the page is read from disk on every request.

## HTTP API

All endpoints are on `127.0.0.1:8765`. Requests from other origins are refused (allowed: `http://127.0.0.1:8765`, `http://localhost:8765`, `https://markleyboyer.github.io`, `null`), so only the local editor page and the hosted GitHub Pages copy can talk to your editor.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/` | | the web app |
| GET | `/api/ping` | | `{mode, project, engine, ok}` |
| GET | `/api/tables` | `?struct=species\|ecosystem\|all` | `{tables: [{path, name, type}]}` |
| GET | `/api/table` | `?path=/Game/.../SDT_X` | `{path, csv}` (Unreal's own CSV export) |
| POST | `/api/table` | `{path, csv, baseCsv?, force?}` | `{path, csv}` after writing; **409** `{error, csv}` if the table changed since `baseCsv` |
| POST | `/api/regenerate` | `{}` | `{regenerated: [{actor, event, generated, errors}]}` |
| GET | `/api/selection` | | `{paths}` of DataTables selected in the Content Browser |
| GET / POST | `/api/hidden` | POST `{hidden: {table: {row: stems}}}` | the remembered stems of switched-off species (`Saved/EcoTableEditor/hidden_species.json`) |
| GET | `/api/thumb` | `?mesh=<mesh path>[&refresh=1]` | PNG thumbnail, cached in `Saved/EcoThumbs/` |

Notes:
- Tables are read and written with `DataTableFunctionLibrary.export_data_table_to_csv_string` / `fill_data_table_from_csv_string`, so the CSV shape is exactly what Unreal produces.
- Unreal API calls are marshalled onto the editor's game thread through a Slate post-tick callback. HTTP requests themselves are handled on a background thread.
- **Regenerate** re-assigns each Aziel actor's `EcosystemList` to itself (re-running its construction script, which rebuilds the plant lists from the tables), runs `pcg.RuntimeGeneration.Enable 1`, then calls `generate(True)` on each activated PCG component. Aziel's own *ForceUpdate* event can't be called from Python.
- **Thumbnails** are rendered by calling the editor's built-in Model Context Protocol server (`http://127.0.0.1:8000/mcp`, tool `EditorToolset.EditorAppToolset.CaptureAssetImage`). This needs the UE 5.8 *Model Context Protocol* plugin with its server running. Without it, thumbnails simply don't appear.

## Testing without Unreal (mock mode)

The bridge can serve a folder of DataTable CSVs as if they were Unreal assets:

```bash
python -I eco_table_bridge.py --mock <folder of CSVs> --port 8766 --html <path to ue-datatable-editor.html>
```

Then open `http://127.0.0.1:8766/`. Saves write back into the CSV files, and the on/off memory goes to `<folder>/EcoTableEditor/hidden_species.json`.

## Files

| File | Purpose |
|---|---|
| `EcoTableEditor.uplugin` | Plugin descriptor (editor-only, enabled by default, depends on Python / Editor Scripting / Web Browser) |
| `Content/Python/init_unreal.py` | Starts the bridge when the editor launches |
| `Content/Python/eco_table_bridge.py` | The HTTP server, Unreal backend, mock backend, thumbnail renderer and on/off store |
